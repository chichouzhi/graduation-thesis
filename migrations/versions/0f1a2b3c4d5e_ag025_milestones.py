"""ag025_milestones

Revision ID: 0f1a2b3c4d5e
Revises: fa1b2c3d4e5f
Create Date: 2026-04-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0f1a2b3c4d5e"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    # AG-025：``milestones``（与 ``app.taskboard.model.Milestone``、AG-019 一致）。
    op.create_table(
        "milestones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.String(length=4096), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'todo'"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('todo', 'doing', 'done')",
            name="ck_milestones_status",
        ),
    )
    op.create_index(
        op.f("ix_milestones_student_id"),
        "milestones",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_milestones_student_sort",
        "milestones",
        ["student_id", "sort_order"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_milestones_student_sort", table_name="milestones")
    op.drop_index(op.f("ix_milestones_student_id"), table_name="milestones")
    op.drop_table("milestones")
