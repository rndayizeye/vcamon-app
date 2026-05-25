"""add symptom capture metadata

Revision ID: 6b2a2836b7f8
Revises: e3f9427a3fbf
Create Date: 2026-05-22 20:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6b2a2836b7f8"
down_revision: Union[str, Sequence[str], None] = "e3f9427a3fbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


symptom_date_kind_enum = sa.Enum(
    "ONSET_REPORTED",
    "OBSERVED_DURING_EXAM",
    name="symptom_date_kind_enum",
)
symptom_duration_source_enum = sa.Enum(
    "REPORTED",
    "ASSUMED_MAX",
    "UNKNOWN",
    name="symptom_duration_source_enum",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        symptom_date_kind_enum.create(bind, checkfirst=True)
        symptom_duration_source_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.add_column(
            sa.Column("date_kind", symptom_date_kind_enum, nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "duration_source",
                symptom_duration_source_enum,
                nullable=True,
            )
        )

    op.execute(
        "UPDATE symptom_entries SET date_kind = 'ONSET_REPORTED' WHERE date_kind IS NULL"
    )
    op.execute(
        """
        UPDATE symptom_entries
        SET duration_source = CASE
            WHEN duration_days IS NOT NULL THEN 'REPORTED'
            ELSE 'UNKNOWN'
        END
        WHERE duration_source IS NULL
        """
    )

    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.alter_column(
            "date_kind",
            existing_type=symptom_date_kind_enum,
            nullable=False,
        )
        batch_op.alter_column(
            "duration_source",
            existing_type=symptom_duration_source_enum,
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("symptom_entries") as batch_op:
        batch_op.drop_column("duration_source")
        batch_op.drop_column("date_kind")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="symptom_duration_source_enum").drop(bind, checkfirst=True)
        postgresql.ENUM(name="symptom_date_kind_enum").drop(bind, checkfirst=True)
