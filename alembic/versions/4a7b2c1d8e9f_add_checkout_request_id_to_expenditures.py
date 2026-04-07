"""Add checkout_request_id to expenditures

Revision ID: 4a7b2c1d8e9f
Revises: 311c4aa95e74
Create Date: 2026-04-07 20:15:00.000000

The Expenditure ORM model has had checkout_request_id since the M-Pesa
finance integration was added, but no forward migration ever created it.
The d4df720dd8fe migration's downgrade() incorrectly referenced dropping
it, confirming the column was always intended to exist.
"""
from alembic import op
import sqlalchemy as sa


revision = '4a7b2c1d8e9f'
down_revision = '311c4aa95e74'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'expenditures',
        sa.Column('checkout_request_id', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('expenditures', 'checkout_request_id')
