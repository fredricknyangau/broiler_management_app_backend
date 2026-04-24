"""fix_missing_columns

Revision ID: 60cf8fa5d065
Revises: 59cf8fa5d064
Create Date: 2026-04-24 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60cf8fa5d065'
down_revision = '59cf8fa5d064'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use raw SQL to add columns IF they don't exist
    # This prevents errors if they already exist locally but are missing on Neon
    op.execute("""
        DO $$ 
        BEGIN 
            -- Check for related_id in expenditures
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='expenditures' AND column_name='related_id') THEN
                ALTER TABLE expenditures ADD COLUMN related_id UUID;
                CREATE INDEX ix_expenditures_related_id ON expenditures (related_id);
                COMMENT ON COLUMN expenditures.related_id IS 'ID of the source event (e.g. FeedEvent ID)';
            END IF;

            -- Check for related_type in expenditures
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='expenditures' AND column_name='related_type') THEN
                ALTER TABLE expenditures ADD COLUMN related_type VARCHAR(50);
                CREATE INDEX ix_expenditures_related_type ON expenditures (related_type);
                COMMENT ON COLUMN expenditures.related_type IS 'Type of source event: feed, vaccination, flock_placement';
            END IF;

            -- Check for cost_ksh in vaccination_events
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vaccination_events' AND column_name='cost_ksh') THEN
                ALTER TABLE vaccination_events ADD COLUMN cost_ksh DECIMAL(10,2);
            END IF;
        END $$;
    """)

def downgrade() -> None:
    # No-op to avoid dropping data accidentally in case of manual rollbacks
    pass
