"""architecture.spec.md §9 与 §1.1 规则 → 多引擎映射（单一真源）。

engines:
  - import_linter  : 由 .importlinter + lint-imports 执行（本模块不重复实现 rg）
  - static         : scripts/check_rules.py（纯 Python / 子进程调用既有 ci 脚本）
  - pytest_arch    : tests/test_architecture.py（仓库元数据、注册表完整性）
  - pytest_other   : tests/arch/** 等集成/间谍测（本表仅索引，不在 test_architecture 内重复断言）
  - manual         : 无法自动检测；CI 不因此失败

duplicate_policy:
  - 凡标记 import_linter 的边，check_rules 不再做等价的 api/**/*.py rg，避免与 linter 冲突。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Engine = Literal["import_linter", "static", "pytest_arch", "pytest_other", "manual"]


@dataclass(frozen=True)
class ArchRule:
    id: str
    engines: tuple[Engine, ...]
    autodetect: bool
    note: str = ""


# 顺序与 architecture.spec.md 建议一致，便于审阅
RULES: tuple[ArchRule, ...] = (
    # §2 禁止
    ArchRule(
        "R-API-ADAPTER",
        ("import_linter", "static"),
        True,
        ".importlinter forbidden_api_adapter + scripts/ci/check_api_packages_in_linter.py；动态 import 见 manual",
    ),
    ArchRule("R-API-LLM", ("pytest_other", "manual"), False, "PROC_API 语义；§5.1 集成测 + 动态 import 无法静态保证"),
    ArchRule("R-API-UC", ("import_linter",), True, "§4 forbidden_api_use_cases"),
    ArchRule("R-API-TASK", ("import_linter",), True, "§4 forbidden_api_task"),
    ArchRule(
        "R-API-MODEL",
        ("static",),
        True,
        "rg-guard-api-model；非 import-linter 能力（spec §4 说明）",
    ),
    ArchRule("R-APP-EXAMPLES", ("static",), True, "scripts/ci/rg_guard_app_examples.py"),
    ArchRule("R-SYNC-LLM", ("pytest_other", "manual"), False, "§5.1 时序+无 LLM HTTP；与 R-API-LLM 叠加"),
    ArchRule("R-TASK-BIZ", ("static",), True, "rg-guard-jobs-biz"),
    ArchRule(
        "R-UC-SKIP",
        ("import_linter", "pytest_other"),
        True,
        "linter: forbidden_task_adapter（直连 adapter 禁止；allow_indirect_imports）；rg 兜底 task 内 adapter import",
    ),
    ArchRule("R-NO-QUEUE", ("static", "pytest_other", "manual"), True, "部署清单可机判部分 static；broker 行为集成测"),
    ArchRule("R-UC-ONLY", ("static",), True, "llm_entrypoints 脚本 + rg-guard-svc-uc-signals"),
    ArchRule("R-SVC-LLM", ("static",), True, "rg-guard-svc-llm（不做 service→整包 adapter 的 linter，以免与 R-SVC 口径漂移）"),
    ArchRule("R-REC-LLM", ("static",), True, "app/recommendations/** rg（API 已由 linter 覆盖）"),
    ArchRule("R-TASK-API", ("import_linter",), True, "§4 forbidden_task_api"),
    ArchRule(
        "R-UC-API",
        ("import_linter",),
        True,
        "linter: forbidden_use_cases_flask + forbidden_use_cases_api（避免与 rg 双检冲突）",
    ),
    ArchRule("R-QUEUE-CONSIST", ("pytest_other", "manual"), False, "集成 spy / 僵尸行；无可靠纯静态真值"),
    ArchRule("R-QUEUE-ISO", ("static",), True, "check_queue_contract_keys + 可选 enqueue 字面量（弱）"),
    ArchRule("R-CHAT-JOB-ORDER", ("pytest_arch", "static"), True, "三选一真源文件/配置"),
    ArchRule("R-POLICY-SVC", ("pytest_other", "static"), True, "policy deny 三测 + check_policy_deny_tests"),
    ArchRule("W2-DUP", ("static",), True, "与 R-UC-ONLY ② 同 rg，单点实现避免重复"),
    ArchRule("W3", ("static",), True, "SVC 禁止 import app.task.*_jobs（启发式）"),
    ArchRule("W3b", ("manual",), False, "默认关闭；启用须 ADR + 改 registry + linter"),
    ArchRule(
        "W4",
        ("static", "pytest_other"),
        True,
        "static: *_jobs 引用 UC + task 不得 import service；集成 M-CHAIN-WORKER",
    ),
    ArchRule(
        "W5",
        ("import_linter", "static", "pytest_other", "manual"),
        True,
        "linter: use_cases_over_adapter；static: app/use_cases 目录存在；Worker 栈与动态 import 见集成/ manual",
    ),
    ArchRule("W6", ("import_linter",), True, "forbidden_task_adapter：禁止 task 直连 adapter，经 UC 可达不判违规"),
    # §3 必须
    ArchRule("M-QUEUE-WORKER", ("static", "pytest_other", "manual"), True, "与 R-NO-QUEUE 检测表重叠；static 覆盖可脚本部分"),
    ArchRule("M-CHAIN-WORKER", ("static", "pytest_other"), True, "static 部分同 R-UC-SKIP jobs；集成 mock UC"),
    ArchRule("M-POLICY-ENQUEUE", ("pytest_other", "manual"), False, "commit/enqueue 顺序 spy"),
    ArchRule("M-ADAPTER-METER", ("pytest_other", "manual"), False, "§5 it-adapter-meter"),
    # §1.1 白名单边（可机判部分已由禁止边与层推导覆盖）
    ArchRule("W1", ("import_linter",), True, "由 R-API-* + domain layers 覆盖"),
    # §6 无 §9 ID：契约序列化与枚举分 schema（与 AsyncTaskStatus 对齐）
    ArchRule(
        "S6-STATUS-SCHEMAS",
        ("manual",),
        False,
        "architecture.spec §6：须 openapi-spec-validator（contract.yaml）+ 集成测区分 AsyncTaskStatus 与业务枚举；无单文件静态真值",
    ),
)


def rules_by_id() -> dict[str, ArchRule]:
    return {r.id: r for r in RULES}


def all_rule_ids() -> frozenset[str]:
    return frozenset(r.id for r in RULES)
