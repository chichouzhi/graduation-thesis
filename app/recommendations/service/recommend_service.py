"""Recommendation service: top-N in-memory scoring, no LLM."""

from __future__ import annotations

from typing import Any

from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.topic.model import Topic, TopicStatus


class RecommendService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _extract_profile_terms(profile: Any) -> set[str]:
        if not isinstance(profile, dict):
            return set()
        out: set[str] = set()
        for key in ("skills", "keywords", "interests"):
            val = profile.get(key)
            if isinstance(val, list):
                for x in val:
                    text = str(x).strip().lower()
                    if text:
                        out.add(text)
        return out

    def recommend_topics_for_student(
        self, user_id: str, *, term_id: str, top_n: int = 10, explain: bool = False
    ) -> dict[str, Any]:
        uid = str(user_id).strip()
        if not uid:
            raise ValueError("user_id must be non-empty")
        tid = str(term_id).strip()
        if not tid:
            raise ValueError("term_id must be non-empty")
        n = int(top_n)
        if n < 1:
            raise ValueError("top_n must be >= 1")
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return {"items": [], "top_n": n}
        if user.role != UserRole.student:
            raise PermissionError("ROLE_FORBIDDEN")

        profile_terms = self._extract_profile_terms(user.student_profile)
        rows = (
            Topic.query.filter_by(term_id=tid, status=TopicStatus.published)
            .order_by(Topic.created_at.desc(), Topic.id.desc())
            .all()
        )
        scored: list[dict[str, Any]] = []
        for row in rows:
            kws = [str(x).strip().lower() for x in (row.tech_keywords or []) if str(x).strip()]
            matched = sorted(set(kws).intersection(profile_terms))
            score = float(len(matched))
            item: dict[str, Any] = {"topic_id": row.id, "title": row.title, "score": score}
            if explain:
                item["explain"] = {
                    "matched_skills": matched,
                    "matched_keywords": matched,
                    "reasons": ([f"matched {len(matched)} profile keywords"] if matched else ["no explicit keyword match"]),
                }
            scored.append(item)
        scored.sort(key=lambda x: (x["score"], x["topic_id"]), reverse=True)
        return {"items": scored[:n], "top_n": n}
