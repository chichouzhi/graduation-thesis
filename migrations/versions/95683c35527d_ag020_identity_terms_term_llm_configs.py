"""ag020_identity_terms_term_llm_configs

Revision ID: 95683c35527d
Revises: 
Create Date: 2026-04-20 11:27:19.471586

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95683c35527d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # AG-020：仅 identity（users）+ terms + term_llm_configs；与其它域迁移分_revision 交付。
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("student_profile", sa.JSON(), nullable=True),
        sa.Column("teacher_profile", sa.JSON(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "terms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("selection_start_at", sa.DateTime(), nullable=True),
        sa.Column("selection_end_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "term_llm_configs",
        sa.Column("term_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=256), nullable=True),
        sa.Column("daily_budget_tokens", sa.Integer(), nullable=True),
        sa.Column("per_user_daily_tokens", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("term_id"),
    )


def downgrade():
    op.drop_table("term_llm_configs")
    op.drop_table("terms")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
