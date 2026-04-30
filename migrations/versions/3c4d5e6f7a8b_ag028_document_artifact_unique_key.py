"""ag028_document_artifact_unique_key

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-04-30 23:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c4d5e6f7a8b"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def _artifact_key(artifact_type: str, stage: str, chunk_index: int | None) -> str:
    chunk_text = "" if chunk_index is None else str(int(chunk_index))
    return f"{artifact_type}\x1f{stage}\x1f{chunk_text}"


def upgrade():
    with op.batch_alter_table("document_artifacts") as batch:
        batch.add_column(sa.Column("artifact_key", sa.String(length=160), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id, document_task_id, artifact_type, stage, chunk_index
            FROM document_artifacts
            ORDER BY updated_at DESC, created_at DESC, id DESC
            """
        )
    ).mappings()

    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = _artifact_key(str(row["artifact_type"]), str(row["stage"]), row["chunk_index"])
        identity = (str(row["document_task_id"]), key)
        if identity in seen:
            conn.execute(
                sa.text("DELETE FROM document_artifacts WHERE id = :id"),
                {"id": row["id"]},
            )
            continue
        conn.execute(
            sa.text("UPDATE document_artifacts SET artifact_key = :artifact_key WHERE id = :id"),
            {"artifact_key": key, "id": row["id"]},
        )
        seen.add(identity)

    with op.batch_alter_table("document_artifacts") as batch:
        batch.alter_column("artifact_key", existing_type=sa.String(length=160), nullable=False)
        batch.create_unique_constraint(
            "uq_document_artifacts_task_artifact_key",
            ["document_task_id", "artifact_key"],
        )


def downgrade():
    with op.batch_alter_table("document_artifacts") as batch:
        batch.drop_constraint("uq_document_artifacts_task_artifact_key", type_="unique")
        batch.drop_column("artifact_key")
