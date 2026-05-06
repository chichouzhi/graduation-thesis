"""ag027_document_artifacts_and_progress

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-30 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b3c4d5e6f7a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("document_tasks") as batch:
        batch.add_column(sa.Column("current_stage", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("progress_json", sa.JSON(), nullable=True))

    op.create_table(
        "document_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_task_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_task_id"], ["document_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_artifacts_document_task_id"),
        "document_artifacts",
        ["document_task_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_document_artifacts_document_task_id"), table_name="document_artifacts")
    op.drop_table("document_artifacts")
    with op.batch_alter_table("document_tasks") as batch:
        batch.drop_column("progress_json")
        batch.drop_column("current_stage")
