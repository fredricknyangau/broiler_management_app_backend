"""add_performance_indexes

Revision ID: 311c4aa95e74
Revises: d4df720dd8fe
Create Date: 2026-04-05 17:26:45.720901

"""
from alembic import op
import sqlalchemy as sa


revision = '311c4aa95e74'
down_revision = 'd4df720dd8fe'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Finance Tables - Composite (Farmer + Date DESC)
    op.create_index('ix_sales_farmer_id_date', 'sales', ['farmer_id', sa.text('date DESC')])
    op.create_index('ix_expenditures_farmer_id_date', 'expenditures', ['farmer_id', sa.text('date DESC')])
    
    # 2. Event Tables - Composite (Flock + Date DESC)
    op.create_index('ix_mortality_flock_id_date', 'mortality_events', ['flock_id', sa.text('event_date DESC')])
    op.create_index('ix_feed_flock_id_date', 'feed_consumption_events', ['flock_id', sa.text('event_date DESC')])
    op.create_index('ix_weight_flock_id_date', 'weight_measurement_events', ['flock_id', sa.text('event_date DESC')])
    op.create_index('ix_vaccination_flock_id_date', 'vaccination_events', ['flock_id', sa.text('event_date DESC')])

def downgrade() -> None:
    op.drop_index('ix_vaccination_flock_id_date', table_name='vaccination_events')
    op.drop_index('ix_weight_flock_id_date', table_name='weight_measurement_events')
    op.drop_index('ix_feed_flock_id_date', table_name='feed_consumption_events')
    op.drop_index('ix_mortality_flock_id_date', table_name='mortality_events')
    op.drop_index('ix_expenditures_farmer_id_date', table_name='expenditures')
    op.drop_index('ix_sales_farmer_id_date', table_name='sales')
