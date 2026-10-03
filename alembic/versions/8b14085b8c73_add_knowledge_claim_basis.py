"""add knowledge claim basis

Revision ID: 8b14085b8c73
Revises: b746cacea516
Create Date: 2026-10-03 08:44:39.622862

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b14085b8c73"
down_revision: str | Sequence[str] | None = "b746cacea516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("knowledge_claims") as batch_op:
        batch_op.add_column(
            sa.Column(
                "basis",
                sa.Enum("observation", "inference", name="claimbasis"),
                nullable=True,
            )
        )

    op.execute(
        sa.text("UPDATE knowledge_claims SET basis = 'observation' WHERE basis IS NULL")
    )

    with op.batch_alter_table("knowledge_claims") as batch_op:
        batch_op.alter_column(
            "basis",
            existing_type=sa.Enum(
                "observation",
                "inference",
                name="claimbasis",
            ),
            nullable=False,
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("knowledge_claims") as batch_op:
        batch_op.drop_column("basis")
    # ### end Alembic commands ###
