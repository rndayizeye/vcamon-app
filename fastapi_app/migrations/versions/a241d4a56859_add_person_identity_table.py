"""add person identity table

Revision ID: a241d4a56859
Revises: d4e5f6a7b8c9
Create Date: 2026-06-01 15:21:25.248950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a241d4a56859'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('cases', sa.Column('person_id', sa.Integer(), nullable=True))
    op.add_column('partners', sa.Column('person_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('partners', 'person_id')
    op.drop_column('cases', 'person_id')
    op.drop_table('persons')
