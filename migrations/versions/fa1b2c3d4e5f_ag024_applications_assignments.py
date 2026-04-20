"""ag024_applications_assignments

Revision ID: fa1b2c3d4e5f
Revises: e7c8f9a1b2d3
Create Date: 2026-04-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fa1b2c3d4e5f"
down_revision = "e7c8f9a1b2d3"
branch_labels = None
depends_on = None


def upgrade():
    # AG-024：``applications`` + ``assignments``（与 ``app.selection.model``、AG-017/AG-018 一致）。
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("term_id", sa.String(length=36), nullable=False),
        sa.Column("topic_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "term_id",
            "topic_id",
            name="uq_applications_student_term_topic",
        ),
        sa.UniqueConstraint(
            "student_id",
            "term_id",
            "priority",
            name="uq_applications_student_term_priority",
        ),
        sa.CheckConstraint("priority IN (1, 2)", name="ck_applications_priority"),
    )
    op.create_index(
        op.f("ix_applications_student_id"),
        "applications",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applications_term_id"),
        "applications",
        ["term_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applications_topic_id"),
        "applications",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_applications_term_student",
        "applications",
        ["term_id", "student_id"],
        unique=False,
    )
    op.create_index(
        "ix_applications_topic_status",
        "applications",
        ["topic_id", "status"],
        unique=False,
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("teacher_id", sa.String(length=36), nullable=False),
        sa.Column("topic_id", sa.String(length=36), nullable=False),
        sa.Column("term_id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assignments_student_id"),
        "assignments",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignments_teacher_id"),
        "assignments",
        ["teacher_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignments_topic_id"),
        "assignments",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignments_term_id"),
        "assignments",
        ["term_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignments_application_id"),
        "assignments",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignments_term_student",
        "assignments",
        ["term_id", "student_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignments_term_teacher",
        "assignments",
        ["term_id", "teacher_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_assignments_term_teacher", table_name="assignments")
    op.drop_index("ix_assignments_term_student", table_name="assignments")
    op.drop_index(op.f("ix_assignments_application_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_term_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_topic_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_teacher_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_student_id"), table_name="assignments")
    op.drop_table("assignments")

    op.drop_index("ix_applications_topic_status", table_name="applications")
    op.drop_index("ix_applications_term_student", table_name="applications")
    op.drop_index(op.f("ix_applications_topic_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_term_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_student_id"), table_name="applications")
    op.drop_table("applications")
