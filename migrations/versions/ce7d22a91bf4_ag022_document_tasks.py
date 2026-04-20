"""ag022_document_tasks

Revision ID: ce7d22a91bf4
Revises: b2f9c8e1d430
Create Date: 2026-04-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ce7d22a91bf4"
down_revision = "b2f9c8e1d430"
branch_labels = None
depends_on = None


def upgrade():
    # AG-022：``document_tasks``（与 ``app.document.model.DocumentTask`` 对齐；依赖 AG-020 users/terms、AG-021 之前链）。
    op.create_table(
        "document_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("term_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column(
            "task_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'summary'"),
        ),
        sa.Column(
            "language",
            sa.String(length=8),
            nullable=False,
            server_default=sa.text("'zh'"),
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("last_completed_chunk", sa.Integer(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("result_storage_uri", sa.String(length=512), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_tasks_user_id"), "document_tasks", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_tasks_term_id"), "document_tasks", ["term_id"], unique=False
    )
    op.create_index(
        "ix_document_tasks_user_status_created",
        "document_tasks",
        ["user_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_tasks_status_created_at",
        "document_tasks",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_tasks_status_locked_at",
        "document_tasks",
        ["status", "locked_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_document_tasks_status_locked_at", table_name="document_tasks")
    op.drop_index("ix_document_tasks_status_created_at", table_name="document_tasks")
    op.drop_index("ix_document_tasks_user_status_created", table_name="document_tasks")
    op.drop_index(op.f("ix_document_tasks_term_id"), table_name="document_tasks")
    op.drop_index(op.f("ix_document_tasks_user_id"), table_name="document_tasks")
    op.drop_table("document_tasks")
