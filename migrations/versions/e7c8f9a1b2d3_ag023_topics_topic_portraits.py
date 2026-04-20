"""ag023_topics_topic_portraits

Revision ID: e7c8f9a1b2d3
Revises: ce7d22a91bf4
Create Date: 2026-04-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7c8f9a1b2d3"
down_revision = "ce7d22a91bf4"
branch_labels = None
depends_on = None


def upgrade():
    # AG-023：``topics`` + 画像等价列 ``portrait_json``（与 ``app.topic.model.Topic``、AG-016 一致；无独立 ``topic_portraits`` 表）。
    op.create_table(
        "topics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("requirements", sa.Text(), nullable=False, server_default=""),
        sa.Column("tech_keywords", sa.JSON(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "selected_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("teacher_id", sa.String(length=36), nullable=False),
        sa.Column("term_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("portrait_json", sa.JSON(), nullable=True),
        sa.Column("llm_keyword_job_id", sa.String(length=36), nullable=True),
        sa.Column("llm_keyword_job_status", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_teacher_id"), "topics", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_topics_term_id"), "topics", ["term_id"], unique=False)
    op.create_index(
        "ix_topics_term_status",
        "topics",
        ["term_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_topics_teacher_term",
        "topics",
        ["teacher_id", "term_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_topics_teacher_term", table_name="topics")
    op.drop_index("ix_topics_term_status", table_name="topics")
    op.drop_index(op.f("ix_topics_term_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_teacher_id"), table_name="topics")
    op.drop_table("topics")
