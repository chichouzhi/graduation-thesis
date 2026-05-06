"""ag026_chat_job_runtime_metadata

Revision ID: 1a2b3c4d5e6f
Revises: 0f1a2b3c4d5e
Create Date: 2026-04-26 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "0f1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chat_jobs") as batch:
        batch.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("finished_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("provider_request_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("model_name", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("usage_json", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("chat_jobs") as batch:
        batch.drop_column("usage_json")
        batch.drop_column("model_name")
        batch.drop_column("provider_request_id")
        batch.drop_column("finished_at")
        batch.drop_column("started_at")
