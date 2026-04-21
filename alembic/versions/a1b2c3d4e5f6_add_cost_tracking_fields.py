"""add_cost_tracking_fields

Revision ID: a1b2c3d4e5f6
Revises: f01c93fc1c84
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f01c93fc1c84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cost_ksh to vaccination_events
    op.add_column(
        'vaccination_events',
        sa.Column('cost_ksh', sa.DECIMAL(precision=10, scale=2), nullable=True)
    )

    # Add auto-linking fields to expenditures
    op.add_column(
        'expenditures',
        sa.Column(
            'related_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='ID of the source event (e.g. FeedEvent ID)'
        )
    )
    op.add_column(
        'expenditures',
        sa.Column(
            'related_type',
            sa.String(length=50),
            nullable=True,
            comment='Type of source event: feed, vaccination, flock_placement'
        )
    )
    op.create_index('ix_expenditures_related_id', 'expenditures', ['related_id'])
    op.create_index('ix_expenditures_related_type', 'expenditures', ['related_type'])


def downgrade() -> None:
    op.drop_index('ix_expenditures_related_type', table_name='expenditures')
    op.drop_index('ix_expenditures_related_id', table_name='expenditures')
    op.drop_column('expenditures', 'related_type')
    op.drop_column('expenditures', 'related_id')
    op.drop_column('vaccination_events', 'cost_ksh')
