"""add_linked_case_id_to_partners

Revision ID: a1b2c3d4e5f6
Revises: ec2923821476
Create Date: 2026-05-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ec2923821476"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("partners") as batch_op:
        batch_op.add_column(
            sa.Column("linked_case_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_partners_linked_case_id",
            "cases",
            ["linked_case_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("partners") as batch_op:
        batch_op.drop_constraint("fk_partners_linked_case_id", type_="foreignkey")
        batch_op.drop_column("linked_case_id")
