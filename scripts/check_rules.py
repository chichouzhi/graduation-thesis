"""多引擎规则：执行 import-linter 之外的静态/脚本检查（与 .importlinter 去重）。

architecture.spec.md 中已由 import-linter 覆盖的 import 边（R-API-ADAPTER / UC / TASK，
R-TASK-API，R-UC-SKIP/W6）不在此重复 rg。

用法:
  python scripts/check_rules.py              # 运行全部静态规则
  python scripts/check_rules.py --list       # 打印规则 → 引擎映射（可读列表）
  python scripts/check_rules.py --markdown   # 打印 spec → 检测方式 Markdown 表
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

from arch_rules_registry import RULES, ArchRule

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app"
APP_TASK = APP / "task"


class RuleError(Exception):
    def __init__(self, rule_id: str, message: str) -> None:
        super().__init__(f"[{rule_id}] {message}")
        self.rule_id = rule_id
        self.msg = message


def _py_under_app(*, subdir: str) -> Iterator[Path]:
    """subdir 为路径片段之一，如 'api' 或 'service'。"""
    if not APP.is_dir():
        return
    for path in APP.rglob("*.py"):
        rel = path.relative_to(REPO)
        if subdir in rel.parts and "tests" not in rel.parts:
            yield path


def _py_under(path: Path, *, glob: str = "*.py") -> Iterator[Path]:
    if not path.is_dir():
        return
    for p in path.rglob(glob):
        if "tests" not in p.parts:
            yield p


def _run_script(rel: str, *, rule_id: str) -> None:
    script = REPO / rel
    if not script.is_file():
        raise RuleError(rule_id, f"missing script {rel}")
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        out = (proc.stdout or "") + (proc.stderr or "")
        raise RuleError(rule_id, f"{rel} failed:\n{out.strip()}")


def check_r_api_model() -> None:
    pat = re.compile(
        r"from\s+app\.\w+\.models\s+import|import\s+app\.\w+\.models|"
        r"from\s+app\.models\s+import|import\s+app\.models",
        re.M,
    )
    hits: list[str] = []
    for path in _py_under_app(subdir="api"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError("R-API-MODEL", "API 层疑似直连 ORM models:\n  " + "\n  ".join(hits))


def check_r_svc_llm() -> None:
    pat = re.compile(r"adapter\.llm|from\s+app\.adapter.*\bllm\b", re.M)
    hits: list[str] = []
    for path in _py_under_app(subdir="service"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError("R-SVC-LLM", "service 层疑似直连 adapter.llm:\n  " + "\n  ".join(hits))


def check_r_rec_llm() -> None:
    root = APP / "recommendations"
    if not root.is_dir():
        return
    pat = re.compile(
        r"adapter\.llm|from\s+app\.adapter.*\bllm\b|from\s+app\.adapter.*\bnlp\b|import\s+app\.adapter\b",
        re.M,
    )
    hits: list[str] = []
    for path in _py_under(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError("R-REC-LLM", "recommendations 域疑似调用 adapter llm/nlp:\n  " + "\n  ".join(hits))


def check_r_uc_only_signals() -> None:
    """R-UC-ONLY ② + W2-DUP（同一 rg，避免双份实现）。"""
    pat = re.compile(r"system_prompt|messages\s*=\s*\[|\"role\"\s*:\s*\"system\"|PROMPT_", re.M)
    hits: list[str] = []
    for path in _py_under_app(subdir="service"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pat.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError(
            "R-UC-ONLY",
            "service 层出现 UC 级编排信号（亦属 W2-DUP 代理）：\n  " + "\n  ".join(hits),
        )


def check_r_task_biz() -> None:
    if not APP_TASK.is_dir():
        return
    pats = [
        re.compile(r"PROMPT_|CHUNK_SIZE", re.M),
        re.compile(r"role\"\s*:\s*\"system\"|role'\s*:\s*'system'", re.M),
    ]
    hits: list[str] = []
    for path in APP_TASK.glob("*_jobs*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for p in pats:
            if p.search(text):
                hits.append(str(path.relative_to(REPO)))
                break
    if hits:
        raise RuleError("R-TASK-BIZ", "*_jobs 文件疑似含编排片段:\n  " + "\n  ".join(hits))


def check_w3_svc_enqueue_only_queue() -> None:
    """W3：禁止 SVC import app.task 下 *_jobs（queue 除外）。"""
    bad_import = re.compile(r"^\s*(?:from|import)\s+app\.task\.(?!queue\b)\w+", re.M)
    hits: list[str] = []
    for path in _py_under_app(subdir="service"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if bad_import.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError("W3", "service 层疑似直接 import app.task 非 queue 模块:\n  " + "\n  ".join(hits))


def check_task_not_import_service() -> None:
    """W4 消费路径：task 不得绕 UC 直接依赖各域 service。"""
    bad = re.compile(r"^\s*from\s+app\.\w+\.service\b|^\s*import\s+app\.\w+\.service\b", re.M)
    hits: list[str] = []
    for path in _py_under(APP_TASK):
        text = path.read_text(encoding="utf-8", errors="replace")
        if bad.search(text):
            hits.append(str(path.relative_to(REPO)))
    if hits:
        raise RuleError("W4", "app/task 疑似 import 域 service（应经 use_cases）:\n  " + "\n  ".join(hits))


def check_m_chain_jobs_reference_uc() -> None:
    """M-CHAIN-WORKER ② / W4：每个 *_jobs*.py 须出现 use_cases 或 app.use_cases。"""
    if not APP_TASK.is_dir():
        return
    need = re.compile(r"\buse_cases\b|app\.use_cases")
    missing: list[str] = []
    for path in APP_TASK.glob("*_jobs*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not need.search(text):
            missing.append(str(path.relative_to(REPO)))
    if missing:
        raise RuleError(
            "M-CHAIN-WORKER",
            "以下 *_jobs 文件未命中 use_cases / app.use_cases 引用:\n  " + "\n  ".join(missing),
        )


def check_r_chat_job_order() -> None:
    ep = REPO / "execution_plan.md"
    doc = REPO / "docs" / "arch" / "chat_job_order.md"
    cfg = APP / "config.py"
    ok = False
    if doc.is_file():
        ok = True
    if cfg.is_file() and re.search(r"^CHAT_JOB_ORDER\s*=", cfg.read_text(encoding="utf-8", errors="replace"), re.M):
        ok = True
    if ep.is_file() and re.search(
        r"^###\s+Chat\s+同会话多 job 顺序（真源）",
        ep.read_text(encoding="utf-8", errors="replace"),
        re.M,
    ):
        ok = True
    if not ok:
        raise RuleError(
            "R-CHAT-JOB-ORDER",
            "三选一真源均未命中：docs/arch/chat_job_order.md 或 app/config.py CHAT_JOB_ORDER= 或 "
            "execution_plan.md 小节「### Chat 同会话多 job 顺序（真源）」",
        )


def check_r_no_queue_manifest() -> None:
    """R-NO-QUEUE / M-QUEUE-WORKER：部署侧可机判子集（无 app/ 时不强制，避免空仓库误伤）。"""
    if not APP.is_dir():
        return
    candidates = [
        REPO / "docker-compose.yml",
        REPO / "compose.yaml",
        REPO / "docker-compose.yaml",
        REPO / "Procfile",
        REPO / "docs" / "deploy.md",
    ]
    texts: list[tuple[Path, str]] = []
    for p in candidates:
        if p.is_file():
            texts.append((p, p.read_text(encoding="utf-8", errors="replace")))
    if not texts:
        raise RuleError(
            "R-NO-QUEUE",
            "未找到 docker-compose.yml / compose.yaml / Procfile / docs/deploy.md 之一；"
            "spec 要求可机判部署清单",
        )
    worker_pat = re.compile(r"\bworker\b", re.I)
    broker_pat = re.compile(r"chat_jobs|document_jobs|\brq\b|celery|redis", re.I)
    for path, text in texts:
        if worker_pat.search(text) and broker_pat.search(text):
            return
    raise RuleError(
        "R-NO-QUEUE",
        "部署清单中未同时命中 worker 与 (chat_jobs|document_jobs|rq|celery|redis) 关键字",
    )


def check_enqueue_literals_weak() -> None:
    """R-QUEUE-ISO 弱校验：service 与 task/queue 中 enqueue(\"...\") 字面量 ⊆ contract 队列键。"""
    contract = REPO / "contract.yaml"
    if not contract.is_file():
        return
    try:
        import yaml  # type: ignore
    except ImportError:
        return
    data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    try:
        keys = set(data["x-task-contracts"]["queues"])
    except (KeyError, TypeError):
        return
    lit_pat = re.compile(r"enqueue\(\s*[\"']([a-zA-Z0-9_]+)[\"']")
    bad: list[str] = []
    files: set[Path] = set()
    qp = APP / "task" / "queue.py"
    if qp.is_file():
        files.add(qp)
    if APP.is_dir():
        for p in APP.rglob("*.py"):
            rel = p.relative_to(APP)
            if "service" in rel.parts and "tests" not in p.parts:
                files.add(p)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in lit_pat.finditer(text):
            k = m.group(1)
            if k not in keys:
                bad.append(f"{path.relative_to(REPO)}:{m.group(0)}")
    if bad:
        raise RuleError("R-QUEUE-ISO", "enqueue 字面量不在 contract 队列键内:\n  " + "\n  ".join(bad[:40]))


def run_static_checks() -> list[RuleError]:
    errors: list[RuleError] = []
    runners = [
        ("R-API-MODEL", check_r_api_model),
        ("R-SVC-LLM", check_r_svc_llm),
        ("R-REC-LLM", check_r_rec_llm),
        ("R-UC-ONLY", check_r_uc_only_signals),
        ("R-TASK-BIZ", check_r_task_biz),
        ("W3", check_w3_svc_enqueue_only_queue),
        ("W4", check_task_not_import_service),
        ("M-CHAIN-WORKER", check_m_chain_jobs_reference_uc),
        ("R-CHAT-JOB-ORDER", check_r_chat_job_order),
        ("R-NO-QUEUE", check_r_no_queue_manifest),
        ("R-QUEUE-ISO", check_enqueue_literals_weak),
    ]
    for rule_id, fn in runners:
        try:
            fn()
        except RuleError as e:
            errors.append(e)
        except OSError as e:
            errors.append(RuleError(rule_id, str(e)))
    return errors


def run_subprocess_suite() -> list[RuleError]:
    errors: list[RuleError] = []
    steps: list[tuple[str, str]] = [
        ("W5", "scripts/check_architecture.py"),
        ("R-QUEUE-ISO", "scripts/ci/check_queue_contract_keys.py"),
        ("R-UC-ONLY", "scripts/ci/check_llm_entrypoints_doc.py"),
        ("R-POLICY-SVC", "scripts/ci/check_policy_deny_tests.py"),
        ("R-APP-EXAMPLES", "scripts/ci/rg_guard_app_examples.py"),
        ("R-API-ADAPTER", "scripts/ci/check_api_packages_in_linter.py"),
    ]
    for rule_id, rel in steps:
        try:
            _run_script(rel, rule_id=rule_id)
        except RuleError as e:
            errors.append(RuleError(rule_id, e.msg))
    return errors


def print_rule_map() -> None:
    print("# architecture.spec → 引擎映射（真源：scripts/arch_rules_registry.py）\n")
    for r in RULES:
        eng = ", ".join(r.engines)
        ad = "可机判" if r.autodetect else "部分/不可机判"
        note = f" — {r.note}" if r.note else ""
        print(f"- **{r.id}** [{ad}]: {eng}{note}")


def print_rule_map_markdown() -> None:
    """供 CI/文档嵌入：spec 规则 ID -> engines + note（表头 ASCII，避免 Windows 控制台编码乱码）。"""
    lines = [
        "| spec_rule_id | autodetect_all | engines | note |",
        "|---|---:|---|---|",
    ]
    for r in RULES:
        engines = " + ".join(r.engines)
        auto = "yes" if r.autodetect else "no"
        note = (r.note or "").replace("|", "\\|")
        lines.append(f"| `{r.id}` | {auto} | {engines} | {note} |")
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="多引擎架构静态规则（与 import-linter 去重）")
    p.add_argument("--list", action="store_true", help="打印规则映射后退出")
    p.add_argument("--markdown", action="store_true", help="打印 Markdown 规则映射表后退出")
    args = p.parse_args(argv)
    if args.markdown:
        print_rule_map_markdown()
        return 0
    if args.list:
        print_rule_map()
        return 0

    failures: list[RuleError] = []
    failures.extend(run_subprocess_suite())
    failures.extend(run_static_checks())

    if failures:
        print("FAIL: architecture static rules", file=sys.stderr)
        for e in failures:
            print(f"  {e.rule_id}: {e}", file=sys.stderr)
        return 1
    print("OK: architecture static rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
