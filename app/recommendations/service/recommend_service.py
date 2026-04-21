"""Recommendation service: top-N in-memory scoring, no LLM.

只读：``Topic`` 上 ``tech_keywords`` + ``portrait_json.keywords``（AG-016 画像列）
与学生 ``student_profile`` 的 skills/keywords/interests 做 **Jaccard** 打分并取 Top-N；
不调大模型、不做在线重推理写库（符合 ``architecture.spec`` R-REC-LLM）。
"""

from __future__ import annotations

from typing import Any

from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.topic.model import Topic, TopicStatus


def _norm_terms(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    out: set[str] = set()
    for x in values:
        text = str(x).strip().lower()
        if text:
            out.add(text)
    return out


class RecommendService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _profile_buckets(profile: Any) -> tuple[set[str], set[str], set[str], set[str]]:
        """Returns ``(skills, keywords, interests, union)`` — all lowercased tokens."""
        if not isinstance(profile, dict):
            return (set(), set(), set(), set())
        skills = _norm_terms(profile.get("skills"))
        keywords = _norm_terms(profile.get("keywords"))
        interests = _norm_terms(profile.get("interests"))
        union = skills | keywords | interests
        return (skills, keywords, interests, union)

    @staticmethod
    def _topic_term_set(row: Topic) -> set[str]:
        """课题侧只读词集：手工 ``tech_keywords`` ∪ 持久化画像 ``portrait_json.keywords``。"""
        terms = _norm_terms(row.tech_keywords)
        pj = row.portrait_json
        if isinstance(pj, dict):
            terms |= _norm_terms(pj.get("keywords"))
        return terms

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a and not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return float(inter) / float(union) if union else 0.0

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

        skills_s, keywords_s, interests_s, profile_union = self._profile_buckets(user.student_profile)
        rows = (
            Topic.query.filter_by(term_id=tid, status=TopicStatus.published)
            .order_by(Topic.created_at.desc(), Topic.id.desc())
            .all()
        )
        scored: list[dict[str, Any]] = []
        for row in rows:
            topic_terms = self._topic_term_set(row)
            score = self._jaccard(profile_union, topic_terms)
            matched = sorted(topic_terms & profile_union)
            item: dict[str, Any] = {"topic_id": row.id, "title": row.title, "score": score}
            if explain:
                profile_non_skill = keywords_s | interests_s
                item["explain"] = {
                    "matched_skills": sorted(topic_terms & skills_s),
                    "matched_keywords": sorted(topic_terms & profile_non_skill),
                    "reasons": (
                        [f"jaccard={score:.4f} over {len(matched)} shared term(s)"]
                        if matched
                        else ["no overlapping terms between profile and topic keywords/portrait"]
                    ),
                }
            scored.append(item)
        scored.sort(key=lambda x: (x["score"], x["topic_id"]), reverse=True)
        return {"items": scored[:n], "top_n": n}
