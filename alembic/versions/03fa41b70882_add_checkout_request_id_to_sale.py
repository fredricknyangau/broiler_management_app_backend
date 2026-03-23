"""add checkout_request_id to sale

Revision ID: 03fa41b70882
Revises: f2fe9e107929
Create Date: 2026-03-23 14:51:27.902621

"""
from alembic import op
import sqlalchemy as sa


revision = '03fa41b70882'
down_revision = 'f2fe9e107929'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('sales', sa.Column('checkout_request_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_sales_checkout_request_id'), 'sales', ['checkout_request_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_sales_checkout_request_id'), table_name='sales')
    op.drop_column('sales', 'checkout_request_id')
