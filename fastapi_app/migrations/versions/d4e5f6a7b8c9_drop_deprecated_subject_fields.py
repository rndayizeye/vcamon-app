"""Drop deprecated legacy lab/symptom/lesion columns from subjects

Revision ID: d4e5f6a7b8c9
Revises: b1c2d3e4f5a6
Create Date: 2026-05-30

These columns (lab_1/2/3, lesion_type, symptom, lab_1_date/2_date/3_date)
were the original single-row storage for labs and symptoms on Case/Partner.
They were deprecated when LabResultEntry and SymptomEntry were introduced.
New writes always set them to None; the Subject migration (b1c2d3e4f5a6)
moved them here from cases/partners. This migration removes them entirely.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEPRECATED_COLS = [
    "lab_1",
    "lab_2",
    "lab_3",
    "lesion_type",
    "symptom",
    "lab_1_date",
    "lab_2_date",
    "lab_3_date",
]


def upgrade() -> None:
    with op.batch_alter_table("subjects") as batch_op:
        for col in _DEPRECATED_COLS:
            batch_op.drop_column(col)


def downgrade() -> None:
    with op.batch_alter_table("subjects") as batch_op:
        batch_op.add_column(sa.Column("lab_3_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("lab_2_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("lab_1_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("symptom", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("lesion_type", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("lab_3", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("lab_2", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("lab_1", sa.String(50), nullable=True))
