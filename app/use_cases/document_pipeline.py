"""文献多段 LLM 编排：分块计划与 ``DocumentJobPayload`` 幂等键（纯函数、无 IO）。

与 ``contract.yaml`` → ``DocumentJobPayload.stage`` / ``chunk_index``、
``execution_plan``（``document_task_id + chunk_index (+ stage)`` 幂等）及
``ADR-document-pdf-parse-to-document-jobs.md`` 一致；并行度上界见 ``Config.DOCUMENT_CHUNK_MAX_PARALLEL``。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from app.config import Config

# 与 ``contract.yaml`` → ``DocumentJobPayload.stage`` 枚举逐项对齐
class DocumentJobStage(str, Enum):
    EXTRACT = "extract"
    SUMMARIZE_CHUNK = "summarize_chunk"
    AGGREGATE = "aggregate"
    FINALIZE = "finalize"


# 分隔符：避免与 UUID/常见路径字符冲突
_IDEMPOTENCY_SEP: Final[str] = "\x1f"


@dataclass(frozen=True, slots=True)
class PlannedDocumentJob:
    """单条 ``document_jobs`` 队列消息的语义计划（不含 user_id 等运行时字段）。"""

    stage: DocumentJobStage
    chunk_index: int | None


@dataclass(frozen=True, slots=True)
class DocumentChunkingPlan:
    """解析后可分块文本的块数计划（``max_chunks >= 1``）。"""

    max_chunks: int


def assert_valid_stage_and_chunk(
    stage: DocumentJobStage | str,
    chunk_index: int | None,
) -> None:
    """``chunk_index`` 与 ``stage`` 的组合须满足契约：分块 LLM 子任务必填索引，控制面为 null。"""
    st = stage if isinstance(stage, DocumentJobStage) else DocumentJobStage(str(stage))
    if st == DocumentJobStage.SUMMARIZE_CHUNK:
        if chunk_index is None or int(chunk_index) < 0:
            raise ValueError("summarize_chunk requires chunk_index >= 0")
        return
    if chunk_index is not None:
        raise ValueError(f"{st.value} expects chunk_index null for control-plane jobs")


def format_document_job_idempotency_key(
    *,
    document_task_id: str,
    stage: DocumentJobStage | str,
    chunk_index: int | None,
) -> str:
    """幂等键字符串（``document_task_id`` + ``stage`` + ``chunk_index`` 规范化）。"""
    st = stage if isinstance(stage, DocumentJobStage) else DocumentJobStage(str(stage))
    assert_valid_stage_and_chunk(st, chunk_index)
    tid = (document_task_id or "").strip()
    if not tid:
        raise ValueError("document_task_id must be non-empty")
    ci = "" if chunk_index is None else str(int(chunk_index))
    return f"{tid}{_IDEMPOTENCY_SEP}{st.value}{_IDEMPOTENCY_SEP}{ci}"


def parse_document_job_idempotency_key(key: str) -> tuple[str, DocumentJobStage, int | None]:
    """解析 :func:`format_document_job_idempotency_key` 生成的键。"""
    parts = key.split(_IDEMPOTENCY_SEP)
    if len(parts) != 3:
        raise ValueError("invalid idempotency key shape")
    tid, st_raw, ci_raw = parts
    if not tid:
        raise ValueError("empty document_task_id in key")
    st = DocumentJobStage(st_raw)
    chunk: int | None = None if ci_raw == "" else int(ci_raw)
    assert_valid_stage_and_chunk(st, chunk)
    return tid, st, chunk


def expand_default_document_job_plan(plan: DocumentChunkingPlan) -> tuple[PlannedDocumentJob, ...]:
    """默认流水线：``extract`` → 每块 ``summarize_chunk`` → ``aggregate`` → ``finalize``。

    在 ``pdf_parse`` 已成功写出可分块中间态之后，由 worker 按序入队 ``document_jobs``
    （见 ADR）；返回顺序即推荐入队顺序。
    """
    n = int(plan.max_chunks)
    if n < 1:
        raise ValueError("max_chunks must be >= 1")

    out: list[PlannedDocumentJob] = [
        PlannedDocumentJob(stage=DocumentJobStage.EXTRACT, chunk_index=None),
    ]
    for i in range(n):
        out.append(
            PlannedDocumentJob(stage=DocumentJobStage.SUMMARIZE_CHUNK, chunk_index=i),
        )
    out.append(PlannedDocumentJob(stage=DocumentJobStage.AGGREGATE, chunk_index=None))
    out.append(PlannedDocumentJob(stage=DocumentJobStage.FINALIZE, chunk_index=None))
    return tuple(out)


def iter_planned_jobs(plan: DocumentChunkingPlan) -> Iterator[PlannedDocumentJob]:
    """同 :func:`expand_default_document_job_plan` 的惰性版本。"""
    yield from expand_default_document_job_plan(plan)


def planned_job_count(plan: DocumentChunkingPlan) -> int:
    """默认计划下队列消息条数：``1 + max_chunks + 2``。"""
    return 1 + int(plan.max_chunks) + 2


def validate_chunk_parallel_limit(limit: int) -> int:
    """校验并行度上界（``>= 1``）；用于显式入参或配置覆写。"""
    n = int(limit)
    if n < 1:
        raise ValueError("chunk parallel limit must be >= 1")
    return n


def resolve_document_chunk_max_parallel(*, override: int | None = None) -> int:
    """读取 ``summarize_chunk`` 并行度上界：``override`` 优先，否则 ``Config.DOCUMENT_CHUNK_MAX_PARALLEL``。"""
    if override is not None:
        return validate_chunk_parallel_limit(override)
    return validate_chunk_parallel_limit(int(Config.DOCUMENT_CHUNK_MAX_PARALLEL))


def chunk_summarize_waves(
    total_chunks: int,
    *,
    max_parallel: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    """将 ``0..total_chunks-1`` 划为若干波次，每波至多 ``max_parallel`` 个 chunk（同级 in-flight 上界）。

    Worker 可据此分批入队或限制并发：单波内 chunk 索引可并行，波次间顺序衔接
    （仍须满足 ``aggregate`` / ``finalize`` 在全部 ``summarize_chunk`` 完成之后由编排触发）。
    """
    cap = resolve_document_chunk_max_parallel(override=max_parallel)
    n = int(total_chunks)
    if n < 1:
        raise ValueError("total_chunks must be >= 1")
    waves: list[tuple[int, ...]] = []
    i = 0
    while i < n:
        end = min(i + cap, n)
        waves.append(tuple(range(i, end)))
        i = end
    return tuple(waves)


def run_document_job_stage(
    *,
    stage: DocumentJobStage | str,
    chunk_index: int | None,
    document_task_id: str,
    storage_path: str,
    term_id: str,
    user_id: str,
    max_chunks: int | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Execute one ``DocumentJobPayload`` stage and return writeback patch."""
    st = stage if isinstance(stage, DocumentJobStage) else DocumentJobStage(str(stage))
    assert_valid_stage_and_chunk(st, chunk_index)
    if not (document_task_id or "").strip():
        raise ValueError("document_task_id must be non-empty")
    if not (storage_path or "").strip():
        raise ValueError("storage_path must be non-empty")
    if not (term_id or "").strip():
        raise ValueError("term_id must be non-empty")
    if not (user_id or "").strip():
        raise ValueError("user_id must be non-empty")

    if st in (DocumentJobStage.EXTRACT, DocumentJobStage.AGGREGATE, DocumentJobStage.FINALIZE):
        patch: dict[str, Any] = {"status": "running"}
        if st == DocumentJobStage.FINALIZE:
            patch["status"] = "done"
        return patch

    # summarize_chunk: UC 统一触达 LLM，task 层不直接 import adapter
    from app.adapter import llm as llm_mod

    prompt = (
        f"Summarize chunk {chunk_index} for document_task_id={document_task_id}. "
        f"Use concise bullet points."
    )
    llm_resp = llm_mod.complete(
        [{"role": "user", "content": prompt}],
        term_id=term_id,
        user_id=user_id,
        request_id=request_id,
    )
    if isinstance(llm_resp, dict):
        summary_text = str(llm_resp.get("content", ""))
    else:
        summary_text = str(llm_resp)

    result_patch: dict[str, Any] = {
        "chunk_index": chunk_index,
        "summary": summary_text,
    }
    if max_chunks is not None:
        result_patch["max_chunks"] = int(max_chunks)
    return {
        "status": "running",
        "last_completed_chunk": chunk_index,
        "result_patch": result_patch,
    }
