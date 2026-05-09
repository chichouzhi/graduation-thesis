"""Recommendation service: top-N in-memory scoring, no LLM.

只读：``Topic`` 上 ``tech_keywords`` + ``portrait_json`` 画像字段与学生 ``student_profile``
做 Jaccard/解释性打分并取 Top-N；不调大模型、不做在线重推理写库（符合
``architecture.spec`` R-REC-LLM）。
"""

from __future__ import annotations

from typing import Any

from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.topic.model import Topic, TopicStatus
from app.topic.model import contract_portrait_from_json


def _norm_terms(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    out: set[str] = set()
    for x in values:
        text = str(x).strip().lower()
        if text:
            out.add(text)
    return out


def _norm_terms_from_value(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return _norm_terms(value)
    if isinstance(value, str):
        parts = [
            part.strip()
            for part in value.replace("，", ",").replace("；", ",").replace("、", ",").split(",")
        ]
        return {part.lower() for part in parts if part}
    return _norm_terms([value])


class RecommendService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _profile_buckets(profile: Any) -> tuple[set[str], set[str], set[str], set[str]]:
        """Returns ``(skills, keywords, interests, union)`` — all lowercased tokens."""
        if not isinstance(profile, dict):
            return (set(), set(), set(), set())
        skills = _norm_terms_from_value(profile.get("skills"))
        keywords = _norm_terms_from_value(profile.get("keywords"))
        interests = _norm_terms_from_value(profile.get("interests"))
        union = skills | keywords | interests
        goal_terms = _norm_terms_from_value(profile.get("goal"))
        union |= goal_terms
        return (skills, keywords, interests, union)

    @staticmethod
    def _topic_term_set(row: Topic) -> set[str]:
        """课题侧只读词集：手工 ``tech_keywords`` ∪ 持久化画像 ``portrait_json.keywords``。"""
        terms = _norm_terms(row.tech_keywords)
        pj = row.portrait_json
        if isinstance(pj, dict):
            portrait = contract_portrait_from_json(pj) or {}
            terms |= _norm_terms_from_value(portrait.get("keywords"))
        return terms

    @staticmethod
    def _topic_capabilities(row: Topic) -> list[str]:
        pj = row.portrait_json
        if not isinstance(pj, dict):
            return []
        portrait = contract_portrait_from_json(pj) or {}
        return [str(item).strip() for item in portrait.get("required_capabilities", []) if str(item).strip()]

    @staticmethod
    def _capacity_status(row: Topic) -> str:
        remaining = max(int(row.capacity) - int(row.selected_count), 0)
        if remaining <= 0:
            return "full"
        if remaining <= 1:
            return "nearly_full"
        return "available"

    @staticmethod
    def _difficulty_fit_label(difficulty_label: str | None, weekly_hours: int) -> str | None:
        if difficulty_label is None:
            return None
        if difficulty_label == "basic":
            return "匹配"
        if difficulty_label == "intermediate":
            return "匹配" if weekly_hours >= 6 else "偏紧"
        if difficulty_label == "advanced":
            return "匹配" if weekly_hours >= 8 else "偏紧"
        return None

    @staticmethod
    def _capability_matches(capability: str, profile_text: str) -> bool:
        signals = {
            "前端实现与交互设计": ["react", "前端", "ui", "界面", "交互", "页面"],
            "后端接口与数据建模": ["flask", "python", "后端", "接口", "数据库", "api"],
            "模型调用与语义分析": ["llm", "大模型", "ai", "推荐", "画像", "关键词", "prompt", "语义"],
            "文档处理与内容理解": ["pdf", "文档", "解析", "摘要", "分块"],
            "异步任务编排与状态流转": ["异步", "队列", "任务", "worker", "状态"],
            "学术写作与实验整理": ["论文", "学术", "文献", "实验", "答辩"],
        }
        return any(signal in profile_text for signal in signals.get(capability, []))

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
        profile_goal = ""
        weekly_hours = 0
        if isinstance(user.student_profile, dict):
            profile_goal = str(user.student_profile.get("goal", "") or "").strip()
            weekly_raw = user.student_profile.get("weekly_hours", user.student_profile.get("weeklyHours", 0))
            try:
                weekly_hours = int(weekly_raw or 0)
            except (TypeError, ValueError):
                weekly_hours = 0
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
                capabilities = self._topic_capabilities(row)
                portrait = contract_portrait_from_json(row.portrait_json) if isinstance(row.portrait_json, dict) else None
                profile_text = " ".join(sorted(profile_union))
                matched_capabilities = [
                    capability for capability in capabilities if self._capability_matches(capability, profile_text)
                ]
                capacity_status = self._capacity_status(row)
                difficulty_label = None if portrait is None else str(portrait.get("difficulty_label") or "").strip() or None
                item["explain"] = {
                    "matched_skills": sorted(topic_terms & skills_s),
                    "matched_keywords": sorted(topic_terms & profile_non_skill),
                    "matched_capabilities": matched_capabilities,
                    "difficulty_fit": self._difficulty_fit_label(difficulty_label, weekly_hours),
                    "capacity_status": capacity_status,
                    "warnings": (
                        ["题目容量已满"]
                        if capacity_status == "full"
                        else (["与当前输入的兴趣和技能重合较少"] if not matched else [])
                    ),
                    "reasons": (
                        [f"jaccard={score:.4f} over {len(matched)} shared term(s)"]
                        if matched
                        else ["no overlapping terms between profile and topic keywords/portrait"]
                    ),
                }
                if profile_goal:
                    item["explain"]["reasons"].append(f"student goal: {profile_goal}")
            scored.append(item)
        scored.sort(key=lambda x: (x["score"], x["topic_id"]), reverse=True)
        return {"items": scored[:n], "top_n": n}
