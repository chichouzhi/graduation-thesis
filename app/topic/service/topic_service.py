"""Topic service: CRUD, portrait sync, review flow, and keyword queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.adapter import nlp as nlp_mod
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db, get_policy_gateway
from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.task import queue as queue_mod
from app.terms.model import Term
from app.topic.model import Topic, TopicKeywordJobStatus, TopicStatus


class TopicService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _require_non_empty(name: str, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{name} must be non-empty")
        return text

    @staticmethod
    def _now_iso_z() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _normalize_keywords(values: Any) -> list[str]:
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValueError("tech_keywords must be a list")
        out: list[str] = []
        for item in values:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out

    def _require_teacher_or_admin(self, user_id: str) -> tuple[str, UserRole]:
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            raise ValueError("user not found")
        if user.role not in {UserRole.teacher, UserRole.admin}:
            raise PermissionError("only teacher/admin can mutate topics")
        return uid, user.role

    def _build_text_snapshot(self, *, title: str, summary: str, requirements: str, tech_keywords: list[str]) -> str:
        lines = [title, summary, requirements]
        if tech_keywords:
            lines.append("关键词: " + ", ".join(tech_keywords))
        return "\n".join(lines).strip()

    def _sync_portrait(self, *, title: str, summary: str, requirements: str, tech_keywords: list[str]) -> dict[str, Any]:
        text = "\n".join([title, summary, requirements]).strip()
        tokens = nlp_mod.tokenize(text)
        merged: list[str] = []
        for kw in [*tech_keywords, *tokens]:
            norm = kw.strip()
            if norm and norm not in merged:
                merged.append(norm)
        return {"keywords": merged, "extracted_at": self._now_iso_z()}

    def list_topics(
        self,
        *,
        status: str | None = None,
        teacher_id: str | None = None,
        term_id: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        query = Topic.query
        if status is not None:
            query = query.filter_by(status=TopicStatus(str(status).strip()))
        if teacher_id is not None:
            query = query.filter_by(teacher_id=str(teacher_id).strip())
        if term_id is not None:
            query = query.filter_by(term_id=str(term_id).strip())
        if q:
            like = f"%{str(q).strip()}%"
            query = query.filter(Topic.title.ilike(like) | Topic.summary.ilike(like) | Topic.requirements.ilike(like))
        query = query.order_by(Topic.updated_at.desc(), Topic.id.desc())
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [x.to_topic() for x in rows], "page": page, "page_size": page_size, "total": total}

    def create_topic_as_teacher(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        uid, role = self._require_teacher_or_admin(user_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        title = self._require_non_empty("title", payload.get("title", ""))
        summary = self._require_non_empty("summary", payload.get("summary", ""))
        requirements = self._require_non_empty("requirements", payload.get("requirements", ""))
        term_id = self._require_non_empty("term_id", payload.get("term_id", ""))
        if db.session.get(Term, term_id) is None:
            raise ValueError("term not found")
        capacity = int(payload.get("capacity", 0))
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        tech_keywords = self._normalize_keywords(payload.get("tech_keywords"))
        portrait = self._sync_portrait(title=title, summary=summary, requirements=requirements, tech_keywords=tech_keywords)
        text_snapshot = self._build_text_snapshot(
            title=title, summary=summary, requirements=requirements, tech_keywords=tech_keywords
        )
        keyword_job_id = str(uuid.uuid4())
        row = Topic(
            title=title,
            summary=summary,
            requirements=requirements,
            tech_keywords=tech_keywords,
            capacity=capacity,
            selected_count=0,
            teacher_id=uid,
            term_id=term_id,
            status=TopicStatus.draft,
            portrait_json=portrait,
            llm_keyword_job_id=keyword_job_id,
            llm_keyword_job_status=TopicKeywordJobStatus.pending,
        )
        policy_gateway = get_policy_gateway()
        policy_gateway.assert_can_enqueue(queue=queue_mod.KEYWORD_JOBS, user_id=uid, term_id=term_id, role=role.value)
        db.session.add(row)
        db.session.commit()
        try:
            queue_mod.enqueue_keyword_jobs(
                {
                    "keyword_job_id": keyword_job_id,
                    "topic_id": row.id,
                    "term_id": term_id,
                    "text_snapshot": text_snapshot,
                    "requested_by_user_id": uid,
                }
            )
        except Exception as exc:
            row.llm_keyword_job_status = TopicKeywordJobStatus.failed
            db.session.commit()
            raise PolicyDenied("keyword_jobs queue is unavailable", code=ErrorCode.QUEUE_UNAVAILABLE) from exc
        return row.to_topic()

    def update_topic_as_teacher(self, user_id: str, topic_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        uid, role = self._require_teacher_or_admin(user_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        row = Topic.query.filter_by(id=str(topic_id).strip()).one_or_none()
        if row is None:
            return None
        if role != UserRole.admin and row.teacher_id != uid:
            raise PermissionError("teacher can only update own topics")
        if row.status not in {TopicStatus.draft, TopicStatus.rejected}:
            raise ValueError("only draft/rejected topic can be updated")
        changed_text = False
        if "title" in payload:
            row.title = self._require_non_empty("title", payload["title"])
            changed_text = True
        if "summary" in payload:
            row.summary = self._require_non_empty("summary", payload["summary"])
            changed_text = True
        if "requirements" in payload:
            row.requirements = self._require_non_empty("requirements", payload["requirements"])
            changed_text = True
        if "capacity" in payload:
            cap = int(payload["capacity"])
            if cap < 1:
                raise ValueError("capacity must be >= 1")
            row.capacity = cap
        if "tech_keywords" in payload:
            row.tech_keywords = self._normalize_keywords(payload["tech_keywords"])
            changed_text = True
        if changed_text:
            row.portrait_json = self._sync_portrait(
                title=row.title,
                summary=row.summary,
                requirements=row.requirements,
                tech_keywords=(row.tech_keywords or []),
            )
            row.llm_keyword_job_id = str(uuid.uuid4())
            row.llm_keyword_job_status = TopicKeywordJobStatus.pending

        policy_gateway = get_policy_gateway()
        policy_gateway.assert_can_enqueue(queue=queue_mod.KEYWORD_JOBS, user_id=uid, term_id=row.term_id, role=role.value)
        db.session.commit()
        if changed_text:
            try:
                queue_mod.enqueue_keyword_jobs(
                    {
                        "keyword_job_id": row.llm_keyword_job_id,
                        "topic_id": row.id,
                        "term_id": row.term_id,
                        "text_snapshot": self._build_text_snapshot(
                            title=row.title,
                            summary=row.summary,
                            requirements=row.requirements,
                            tech_keywords=(row.tech_keywords or []),
                        ),
                        "requested_by_user_id": uid,
                    }
                )
            except Exception as exc:
                row.llm_keyword_job_status = TopicKeywordJobStatus.failed
                db.session.commit()
                raise PolicyDenied("keyword_jobs queue is unavailable", code=ErrorCode.QUEUE_UNAVAILABLE) from exc
        return row.to_topic()

    def delete_or_withdraw_topic_as_teacher(self, user_id: str, topic_id: str) -> bool:
        uid, role = self._require_teacher_or_admin(user_id)
        row = Topic.query.filter_by(id=str(topic_id).strip()).one_or_none()
        if row is None:
            return False
        if role != UserRole.admin and row.teacher_id != uid:
            raise PermissionError("teacher can only delete own topics")
        if row.status not in {TopicStatus.draft, TopicStatus.rejected}:
            raise ValueError("only draft/rejected topic can be withdrawn")
        row.status = TopicStatus.closed
        db.session.commit()
        return True

    def submit_topic_for_review(self, user_id: str, topic_id: str) -> dict[str, Any] | None:
        uid, role = self._require_teacher_or_admin(user_id)
        row = Topic.query.filter_by(id=str(topic_id).strip()).one_or_none()
        if row is None:
            return None
        if role != UserRole.admin and row.teacher_id != uid:
            raise PermissionError("teacher can only submit own topics")
        if row.status not in {TopicStatus.draft, TopicStatus.rejected}:
            raise ValueError("only draft/rejected topic can be submitted")
        row.status = TopicStatus.pending_review
        db.session.commit()
        return row.to_topic()

    def review_topic_as_admin(self, user_id: str, topic_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            raise ValueError("user not found")
        if user.role != UserRole.admin:
            raise PermissionError("only admin can review topics")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        row = Topic.query.filter_by(id=str(topic_id).strip()).one_or_none()
        if row is None:
            return None
        if row.status != TopicStatus.pending_review:
            raise ValueError("only pending_review topic can be reviewed")
        action = self._require_non_empty("action", payload.get("action", ""))
        if action == "approve":
            row.status = TopicStatus.published
        elif action == "reject":
            row.status = TopicStatus.rejected
        else:
            raise ValueError("action must be approve or reject")
        db.session.commit()
        return row.to_topic()
