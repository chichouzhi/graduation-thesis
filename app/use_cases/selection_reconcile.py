"""志愿对账编排：``assignments`` 真源与 ``topics.selected_count`` 一致（Worker 路径；无 LLM）。

与 ``contract.yaml`` → ``ReconcileJobPayload``、``ADR-reconcile-jobs-and-w4.md`` 一致。
使用 Core ``text()`` 查询，避免 ``use_cases`` 导入 ORM 模型（import-linter 对 ``app.extensions`` 传递依赖）。

由 ``task/reconcile_jobs.run`` 绑定 ``db.session`` 后调用 :func:`reconcile_assignments`；单测直接传入 ``session``。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

Scope = Literal["by_term", "full_table"]


class ReconcileSummary(TypedDict):
    """对账结果摘要（便于 worker 打日志）。"""

    scope: str
    topics_scanned: int
    topics_updated: int


def _parse_payload(payload: Mapping[str, Any]) -> tuple[str, Scope, str | None]:
    rid = payload.get("reconcile_job_id")
    if rid is None:
        raise ValueError("reconcile_job_id is required")
    scope_raw = payload.get("scope")
    if scope_raw not in ("by_term", "full_table"):
        raise ValueError('scope must be "by_term" or "full_table"')
    scope: Scope = scope_raw
    term_id: str | None = payload.get("term_id")
    if scope == "by_term":
        tid = (term_id or "").strip() if term_id is not None else ""
        if not tid:
            raise ValueError("term_id is required when scope is by_term")
        term_id = tid
    else:
        term_id = None
    return str(rid), scope, term_id


def _active_assignment_count(session: Session, *, topic_id: str, term_id: str) -> int:
    row = session.execute(
        text(
            "SELECT COUNT(*) FROM assignments "
            "WHERE topic_id = :topic_id AND term_id = :term_id AND status = :status"
        ),
        {
            "topic_id": topic_id,
            "term_id": term_id,
            "status": "active",
        },
    ).one()
    return int(row[0])


def reconcile_assignments(
    payload: Mapping[str, Any],
    *,
    session: Session,
) -> ReconcileSummary:
    """将 ``topics.selected_count`` 与 **active** ``assignments`` 行数对齐（按课题 + 学期）。"""
    _reconcile_job_id, scope, term_id = _parse_payload(payload)

    if scope == "by_term":
        rows = session.execute(
            text("SELECT id, term_id, selected_count FROM topics WHERE term_id = :tid"),
            {"tid": term_id},
        ).fetchall()
    else:
        rows = session.execute(text("SELECT id, term_id, selected_count FROM topics")).fetchall()

    updated = 0
    for topic_id, topic_term_id, selected_count in rows:
        actual = _active_assignment_count(session, topic_id=topic_id, term_id=topic_term_id)
        if int(selected_count) != actual:
            session.execute(
                text("UPDATE topics SET selected_count = :cnt WHERE id = :id"),
                {"cnt": actual, "id": topic_id},
            )
            updated += 1

    session.commit()

    return ReconcileSummary(
        scope=scope,
        topics_scanned=len(rows),
        topics_updated=updated,
    )
