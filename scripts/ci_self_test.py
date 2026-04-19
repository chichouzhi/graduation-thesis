"""CI 自检：临时注入违规/失败，逐项跑 pytest / lint-imports / check_rules / score，验证门禁是否生效。

用法（仓库根）:
  python scripts/ci_self_test.py

依赖: 已安装 pytest、import-linter（lint-imports 在 PATH）、PyYAML（check_rules 子步骤）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parents[1]

ToolName = Literal["pytest", "lint-imports", "check_rules", "score"]


@dataclass
class ToolResult:
    name: ToolName
    returncode: int | None
    skipped: bool
    note: str = ""


@dataclass
class ScenarioResult:
    id: str
    description: str
    tools: dict[ToolName, ToolResult] = field(default_factory=dict)
    ok: bool = True
    messages: list[str] = field(default_factory=list)


def _which_lint_imports() -> list[str] | None:
    exe = shutil.which("lint-imports")
    if exe:
        return [exe, "--config", ".importlinter"]
    return None


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> tuple[int | None, str]:
    """返回 (returncode, combined_output)；启动失败时 returncode 为 None。"""
    full_env = os.environ.copy()
    full_env.setdefault("PYTHONUTF8", "1")
    full_env.pop("ARCH_SCORE", None)
    if env is not None:
        full_env.update(env)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except OSError as exc:
        return None, str(exc)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _run_all_tools(env_extra: dict[str, str] | None = None) -> dict[ToolName, ToolResult]:
    results: dict[ToolName, ToolResult] = {}

    # pytest（与 CI 接近：strict-markers；全量略慢但覆盖 policy / spy）
    code, out = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--strict-markers",
            "--tb=no",
        ],
        cwd=REPO,
        env=env_extra,
    )
    results["pytest"] = ToolResult("pytest", code, code is None, out[-400:] if out else "")

    li = _which_lint_imports()
    if li:
        code, out = _run(li, cwd=REPO, env=env_extra)
        results["lint-imports"] = ToolResult(
            "lint-imports", code, code is None, (out or "")[-400:]
        )
    else:
        results["lint-imports"] = ToolResult(
            "lint-imports",
            None,
            True,
            "lint-imports executable not found (pip install import-linter)",
        )

    code, out = _run([sys.executable, "scripts/check_rules.py"], cwd=REPO, env=env_extra)
    results["check_rules"] = ToolResult("check_rules", code, code is None, (out or "")[-400:])

    code, out = _run([sys.executable, "scripts/score.py"], cwd=REPO, env=env_extra)
    results["score"] = ToolResult("score", code, code is None, (out or "")[-200:])

    return results


def _expect(
    tools: dict[ToolName, ToolResult],
    want_fail: dict[ToolName, bool],
    *,
    scenario_id: str,
) -> Iterator[str]:
    """want_fail[tool]=True 表示期望该工具非 0（应检出注入）。"""
    for name, should_fail in want_fail.items():
        tr = tools[name]
        if tr.skipped:
            if should_fail:
                yield (
                    f"[{scenario_id}] {name}: SKIPPED but expected failure — "
                    f"cannot verify ({tr.note})"
                )
            continue
        assert tr.returncode is not None
        failed = tr.returncode != 0
        if failed != should_fail:
            yield (
                f"[{scenario_id}] {name}: 期望 exit {'!=' if should_fail else '=='} 0, "
                f"实际 rc={tr.returncode}"
            )


def _sanity() -> tuple[list[str], list[str]]:
    """返回 (fatal_errors, lint_warnings)。"""
    fatal: list[str] = []
    lint_warn: list[str] = []
    tools = _run_all_tools()
    for name, tr in tools.items():
        if tr.skipped:
            if name == "lint-imports":
                lint_warn.append(f"sanity: {name} skipped — {tr.note}")
            else:
                fatal.append(f"sanity: {name} skipped — {tr.note}")
            continue
        if tr.returncode != 0:
            fatal.append(f"sanity: {name} failed rc={tr.returncode} (clean tree should pass)")
    return fatal, lint_warn


def _scenario_api_adapter_llm(
    inject_path: Path,
) -> tuple[Callable[[], None], Callable[[], None], dict[ToolName, bool], str]:
    """在 API 包内加入对 adapter.llm 的 import（违反 R-API-ADAPTER）。"""

    def prepare() -> None:
        inject_path.parent.mkdir(parents=True, exist_ok=True)
        inject_path.write_text(
            textwrap.dedent(
                '''\
                """CI self-test: forbidden API → adapter.llm import."""
                from app.adapter.llm import complete  # noqa: F401
                '''
            ),
            encoding="utf-8",
        )

    def cleanup() -> None:
        inject_path.unlink(missing_ok=True)

    want = {
        "pytest": False,
        "lint-imports": True,
        "check_rules": False,
        "score": False,
    }
    return prepare, cleanup, want, "API 层 import app.adapter.llm（R-API-ADAPTER）"


def _scenario_pytest_fail(
    target: Path,
) -> tuple[Callable[[], None], Callable[[], None], dict[ToolName, bool], str]:
    original = target.read_text(encoding="utf-8")

    def prepare() -> None:
        target.write_text(
            original
            + "\n\n\ndef test_ci_selftest_injected_failure() -> None:\n"
            '    assert False, "ci_selftest injected pytest failure"\n',
            encoding="utf-8",
        )

    def cleanup() -> None:
        target.write_text(original, encoding="utf-8")

    want = {
        "pytest": True,
        "lint-imports": False,
        "check_rules": False,
        "score": False,
    }
    return prepare, cleanup, want, "pytest 断言失败"


def _scenario_policy_file_contains_skip(
    target: Path,
) -> tuple[Callable[[], None], Callable[[], None], dict[ToolName, bool], str]:
    """在 policy deny 源文件中留下 pytest.skip( 文本，触发 check_policy_deny_tests 静态扫描。"""
    original = target.read_text(encoding="utf-8")
    inject = textwrap.dedent(
        '''

        import pytest  # ci_selftest_inject

        def _ci_selftest_skip_probe() -> None:
            if False:
                pytest.skip("ci_selftest injected skip token")
        '''
    )

    def prepare() -> None:
        target.write_text(original + inject, encoding="utf-8")

    def cleanup() -> None:
        target.write_text(original, encoding="utf-8")

    want = {
        "pytest": False,
        "lint-imports": False,
        "check_rules": True,
        "score": False,
    }
    return prepare, cleanup, want, "policy 测文件中出现 pytest.skip(（违反 check_policy_deny_tests 门禁）"


def _scenario_score_low() -> tuple[Callable[[], None], Callable[[], None], dict[ToolName, bool], str]:
    def prepare() -> None:
        return

    def cleanup() -> None:
        return

    want = {
        "pytest": False,
        "lint-imports": False,
        "check_rules": False,
        "score": True,
    }
    return prepare, cleanup, want, "ARCH_SCORE=55（<80）"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    os.environ.pop("ARCH_SCORE", None)
    os.chdir(REPO)
    print("== CI self-test: sanity (clean tree) ==")
    bad, lint_warn = _sanity()
    for w in lint_warn:
        print("WARN:", w)
    if bad:
        for line in bad:
            print("FATAL:", line, file=sys.stderr)
        return 2

    scenarios: list[tuple[str, str, Callable[[], None], Callable[[], None], dict[ToolName, bool], dict[str, str] | None]] = []

    if _which_lint_imports():
        inj_api = REPO / "app" / "chat" / "api" / "_ci_selftest_bad_import.py"
        p, c, w, desc = _scenario_api_adapter_llm(inj_api)
        scenarios.append(("api_adapter_llm", desc, p, c, w, None))
    else:
        print(
            "WARN: skip scenario api_adapter_llm (lint-imports not on PATH). "
            "Install: pip install import-linter"
        )

    arch_test = REPO / "tests" / "test_architecture.py"
    p, c, w, desc = _scenario_pytest_fail(arch_test)
    scenarios.append(("pytest_fail", desc, p, c, w, None))

    pol = REPO / "tests" / "arch" / "test_policy_deny_chat.py"
    p, c, w, desc = _scenario_policy_file_contains_skip(pol)
    scenarios.append(("policy_pytest_skip_grep", desc, p, c, w, None))

    p, c, w, desc = _scenario_score_low()
    scenarios.append(("score_below_80", desc, p, c, w, {"ARCH_SCORE": "55"}))

    scenario_results: list[ScenarioResult] = []
    tool_effectiveness: dict[ToolName, list[str]] = {
        "pytest": [],
        "lint-imports": [],
        "check_rules": [],
        "score": [],
    }
    tool_miss: dict[ToolName, list[str]] = {k: [] for k in tool_effectiveness}

    for sid, desc, prepare, cleanup, want, env_extra in scenarios:
        print(f"\n== Scenario: {sid} — {desc} ==")
        sr = ScenarioResult(id=sid, description=desc)
        try:
            prepare()
            tools = _run_all_tools(env_extra)
            sr.tools = tools
            for msg in _expect(tools, want, scenario_id=sid):
                sr.messages.append(msg)
                sr.ok = False
            for name, should_fail in want.items():
                tr = tools[name]
                if tr.skipped:
                    continue
                assert tr.returncode is not None
                detected = tr.returncode != 0
                if should_fail and detected:
                    tool_effectiveness[name].append(sid)
                if should_fail and not detected:
                    tool_miss[name].append(sid)
                if not should_fail and detected:
                    sr.messages.append(f"[{sid}] {name}: 未注入时期望通过，但 rc={tr.returncode}")
                    sr.ok = False
        finally:
            cleanup()
        scenario_results.append(sr)
        status = "OK" if sr.ok else "FAIL"
        print(f"   result: {status}")
        for m in sr.messages:
            print("  ", m, file=sys.stderr)

    # 汇总：哪些检测在至少一个场景下有效 / 哪些应检出却未检出
    print("\n" + "=" * 60)
    print("[SUMMARY] which gates caught injected faults (effective)")
    print("=" * 60)
    for name in ("pytest", "lint-imports", "check_rules", "score"):
        eff = tool_effectiveness[name]
        miss = tool_miss[name]
        if eff:
            print(f"- {name}: EFFECTIVE in scenarios: {', '.join(eff)}")
        else:
            print(f"- {name}: not triggered by this inject set (see RISK below)")
        if miss:
            print(f"  RISK: expected FAIL but got PASS: scenarios {', '.join(miss)}")

    print("\n[EXPECTED GAPS] not required to fail for these injects:")
    print(
        "  - API->adapter.llm: pytest and check_rules do not scan api imports; "
        "import-linter is primary (scenario skipped if lint-imports missing)."
    )
    print("  - pytest assert fail: lint-imports / check_rules / score unrelated.")
    print(
        "  - pytest.skip( in policy sources: pytest may still exit 0; "
        "check_policy_deny_tests static grep is the gate."
    )
    print("  - low ARCH_SCORE: only score.py gate.")

    if any(not s.ok for s in scenario_results):
        print("\nOVERALL: FAIL (see stderr lines above)", file=sys.stderr)
        return 1
    print("\nOVERALL: OK (all expected failures observed; other tools stayed green)")

    print("\n--- 中文摘要 ---")
    eff_names: list[str] = []
    if tool_effectiveness["pytest"]:
        eff_names.append("pytest")
    if tool_effectiveness["lint-imports"]:
        eff_names.append("import-linter")
    if tool_effectiveness["check_rules"]:
        eff_names.append("check_rules")
    if tool_effectiveness["score"]:
        eff_names.append("score")
    print("有效检测:", "、".join(eff_names) if eff_names else "（本次无 lint 场景时可能仅部分）")
    risk: list[str] = []
    if not _which_lint_imports():
        risk.append("import-linter 未安装: 未验证 API->adapter 违规")
    if tool_miss["lint-imports"]:
        risk.append("import-linter 应对以下场景失败但未失败: " + ",".join(tool_miss["lint-imports"]))
    for t in ("pytest", "check_rules", "score"):
        if tool_miss[t]:
            risk.append(f"{t} 应对场景失败但未失败: " + ",".join(tool_miss[t]))
    print("未生效或风险:", "；".join(risk) if risk else "无（在已安装 lint-imports 且跑全场景时）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
