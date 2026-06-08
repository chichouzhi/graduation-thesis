"""Fixed topic portrait presets for stable demo scenarios."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


TASKBOARD_DEMO_TITLE = "毕业设计过程任务看板与进度预警平台"
TASKBOARD_DEMO_SUMMARY = "面向毕业设计过程管理，提供任务拆解、进度跟踪和风险提醒。"
TASKBOARD_DEMO_REQUIREMENTS = "支持教师发布阶段任务，学生更新进度，系统生成预警提示。"
TASKBOARD_DEMO_TECH_KEYWORDS = ["React", "Flask", "任务看板", "进度预警"]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fixed_taskboard_portrait(*, extracted_at: str | None = None) -> dict[str, Any]:
    return {
        "keywords": ["毕业设计管理", "任务看板", "进度预警", "阶段节点", "师生协同"],
        "difficulty_label": "intermediate",
        "difficulty_reason": "该题目以过程管理为主，核心难点在任务状态设计、进度规则建模和前后端联动。",
        "required_capabilities": [
            "React 页面开发",
            "Flask 接口设计",
            "数据库建模",
            "任务状态流转",
            "进度预警规则设计",
        ],
        "suitable_students": [
            "熟悉前后端联调并希望做过程管理系统的学生",
            "愿意围绕毕业设计流程设计状态规则和演示数据的学生",
        ],
        "risks": [
            "预警规则过粗会影响提示可信度。",
            "任务状态同步不及时会影响师生协同体验。",
            "演示数据不足时需要准备清晰的阶段节点样例。",
        ],
        "summary": "该课题适合围绕毕业设计过程管理展开，展示从任务拆解、进度跟踪到风险预警的完整闭环。",
        "extracted_at": extracted_at or utc_now_iso_z(),
    }


def fixed_portrait_for_text(text: str) -> dict[str, Any] | None:
    if TASKBOARD_DEMO_TITLE in str(text):
        return fixed_taskboard_portrait()
    return None
