from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import create_app
from app.chat.model import (
    Conversation,
    ConversationContextType,
    Message,
    MessageAsyncTaskStatus,
    MessageRole,
)
from app.extensions import db
from app.identity.model import User
from app.terms.model import Term
from app.topic.model import Topic


TASKBOARD_TOPIC_ID = "ee4c4719-26ea-4f38-a3e6-2e2d26482fff"
DEMO_CONVERSATION_ID = "conv-demo-taskboard-consult"


QA_PAIRS = [
    (
        "我准备做“毕业设计过程任务看板与进度预警平台”，这个选题适合作为毕业设计吗？",
        "这个选题适合作为毕业设计。它的应用场景明确，围绕毕业设计过程中的任务拆解、阶段跟踪、教师反馈和进度预警展开，能够形成比较完整的业务闭环。相比单纯的增删改查系统，它可以展示状态流转、风险判断和师生协同过程，答辩时也容易说明系统价值。建议把重点放在“任务看板 + 进度预警 + 教师查看反馈”三条主线上，先保证流程稳定，再补充统计和提醒细节。",
    ),
    (
        "这个题目的主要功能模块应该怎么设计？",
        "可以拆成四个模块。第一是任务看板模块，用于展示开题、中期检查、论文撰写、答辩准备等阶段任务；第二是进度填报模块，学生可以更新任务状态、完成说明和相关材料；第三是预警规则模块，根据截止时间、完成状态和延期情况生成风险提示；第四是教师管理模块，教师可以查看学生进度、筛选异常任务并给出反馈。这样设计后，系统从任务创建、执行、跟踪到干预都有对应页面，演示链路比较完整。",
    ),
    (
        "答辩时我应该重点讲哪些创新点？",
        "答辩时可以重点讲三点。第一，把毕业设计过程从静态记录变成动态跟踪，教师和学生都能看到阶段任务状态；第二，通过截止时间和完成状态形成进度预警，帮助教师提前发现风险；第三，系统还能与 AI 对话、文档分析、选题推荐等功能衔接，形成从选题到过程管理的完整辅助平台。这样讲会比只介绍页面功能更有层次，也能体现系统对毕业设计管理流程的实际价值。",
    ),
]


def seed_demo_chat() -> None:
    student = User.query.filter_by(username="api-login-user").one()
    term = db.session.get(Term, "term-2026-spring")
    topic = db.session.get(Topic, TASKBOARD_TOPIC_ID)
    context_ref_id = topic.id if topic is not None else None

    Conversation.query.filter_by(user_id=student.id).delete(synchronize_session=False)
    db.session.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    conversation = Conversation(
        id=DEMO_CONVERSATION_ID,
        user_id=student.id,
        term_id=term.id,
        title="演示：毕业设计过程任务看板咨询",
        context_type=ConversationContextType.topic,
        context_ref_id=context_ref_id,
        created_at=now,
        updated_at=now + timedelta(minutes=len(QA_PAIRS) * 2),
    )
    db.session.add(conversation)

    for index, (question, answer) in enumerate(QA_PAIRS):
        created_at = now + timedelta(minutes=index * 2)
        db.session.add(
            Message(
                id=f"msg-demo-u{index + 1}",
                conversation_id=conversation.id,
                role=MessageRole.user,
                content=question,
                delivery_status=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
        db.session.add(
            Message(
                id=f"msg-demo-a{index + 1}",
                conversation_id=conversation.id,
                role=MessageRole.assistant,
                content=answer,
                delivery_status=MessageAsyncTaskStatus.done,
                created_at=created_at + timedelta(seconds=30),
                updated_at=created_at + timedelta(seconds=30),
            )
        )


def main() -> None:
    app = create_app()
    with app.app_context():
        seed_demo_chat()
        db.session.commit()
        print({"conversation": DEMO_CONVERSATION_ID, "messages": len(QA_PAIRS) * 2})


if __name__ == "__main__":
    main()
