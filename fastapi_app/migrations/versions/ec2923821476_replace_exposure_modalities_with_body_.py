"""replace_exposure_modalities_with_body_parts

Revision ID: ec2923821476
Revises: 6b2a2836b7f8
Create Date: 2026-05-25 18:39:04.281228

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec2923821476"
down_revision: Union[str, Sequence[str], None] = "6b2a2836b7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "case_partner_relationships",
        sa.Column("op_body_parts", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "case_partner_relationships",
        sa.Column("partner_body_parts", sa.String(length=200), nullable=True),
    )
    op.drop_column("case_partner_relationships", "exposure_modalities")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "case_partner_relationships",
        sa.Column("exposure_modalities", sa.VARCHAR(length=200), nullable=True),
    )
    op.drop_column("case_partner_relationships", "partner_body_parts")
    op.drop_column("case_partner_relationships", "op_body_parts")
