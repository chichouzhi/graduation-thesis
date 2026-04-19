"""pytest 架构元测：注册表完整性、spec §9 索引、可机判落点文档（与 import-linter / check_rules 去重）。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "architecture.spec.md"

# scripts/ 下的 registry（无 pip 包）
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from arch_rules_registry import RULES, all_rule_ids, ArchRule  # noqa: E402


SECTION9_ROW = re.compile(r"^\|\s*(R-[A-Z0-9-]+|M-[A-Z0-9-]+|W2-DUP)\s*\|", re.MULTILINE)
# §1.1 表内 W 编号（未全部出现在 §9）
EXTRA_REGISTRY_IDS = frozenset({"W1", "W3", "W3b", "W4", "W5", "W6"})


def test_spec_section9_ids_are_registered() -> None:
    text = SPEC.read_text(encoding="utf-8")
    found = set(SECTION9_ROW.findall(text))
    reg = all_rule_ids()
    missing = found - reg
    assert not missing, f"§9 索引表中的规则未写入 arch_rules_registry: {sorted(missing)}"


def test_registry_ids_are_documented_or_extra() -> None:
    text = SPEC.read_text(encoding="utf-8")
    section9 = set(SECTION9_ROW.findall(text))
    # 出现在正文标题中的 R-/M- 规则
    heading_ids = set(re.findall(r"^###\s+(R-[A-Z0-9-]+|M-[A-Z0-9-]+|W2-DUP)\s", text, re.MULTILINE))
    allowed = section9 | heading_ids | EXTRA_REGISTRY_IDS
    unknown = sorted(all_rule_ids() - allowed)
    assert not unknown, (
        "registry 中存在 spec 未出现的规则 id（若有意新增请同步 architecture.spec §9 索引）: "
        + ", ".join(unknown)
    )


@pytest.mark.parametrize("rule", RULES)
def test_manual_rules_have_notes(rule: ArchRule) -> None:
    """无法自动检测（manual / pytest_other 为主）的规则须有 note，避免空白映射。"""
    if "manual" in rule.engines or not rule.autodetect:
        assert rule.note.strip(), f"{rule.id} 缺少 note（应说明检测方式或缺口）"


def test_r_chat_job_order_artifact() -> None:
    """R-CHAT-JOB-ORDER：三选一真源（与 check_rules 一致，pytest 侧作快速回归）。"""
    ep = ROOT / "execution_plan.md"
    doc = ROOT / "docs" / "arch" / "chat_job_order.md"
    cfg = ROOT / "app" / "config.py"
    ok = doc.is_file()
    if cfg.is_file():
        if re.search(r"^CHAT_JOB_ORDER\s*=", cfg.read_text(encoding="utf-8", errors="replace"), re.M):
            ok = True
    if ep.is_file() and re.search(
        r"^###\s+Chat\s+同会话多 job 顺序（真源）",
        ep.read_text(encoding="utf-8", errors="replace"),
        re.M,
    ):
        ok = True
    assert ok, "R-CHAT-JOB-ORDER：须存在 chat_job_order.md 或 CHAT_JOB_ORDER= 或 execution_plan 真源小节"


def test_multi_engine_scripts_executable() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_rules.py"), "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
