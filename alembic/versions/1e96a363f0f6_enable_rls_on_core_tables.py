"""enable_rls_on_core_tables

Revision ID: 1e96a363f0f6
Revises: fe04bcc53389
Create Date: 2026-03-27 15:59:22.665928

"""
from alembic import op
import sqlalchemy as sa


revision = '1e96a363f0f6'
down_revision = 'fe04bcc53389'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable RLS on core tables
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE farms ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE farm_members ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE flocks ENABLE ROW LEVEL SECURITY;")

    # --- Users policies ---
    # Users can see and update only their own row
    op.execute("""
        CREATE POLICY user_self_access ON users
        USING (id = current_setting('app.current_user_id', TRUE)::uuid)
        WITH CHECK (id = current_setting('app.current_user_id', TRUE)::uuid);
    """)

    # --- Farms policies ---
    # A user can see a farm if they own it (farmer_id) or are a member
    op.execute("""
        CREATE POLICY farm_access ON farms
        USING (
            farmer_id = current_setting('app.current_user_id', TRUE)::uuid
            OR id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
        );
    """)

    # --- Farm Members policies ---
    # A user can see farm members for farms they belong to
    op.execute("""
        CREATE POLICY farm_member_access ON farm_members
        USING (
            user_id = current_setting('app.current_user_id', TRUE)::uuid
            OR farm_id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
        );
    """)

    # --- Flocks policies ---
    # A user can see flocks they own or flocks belonging to their farms
    op.execute("""
        CREATE POLICY flock_access ON flocks
        USING (
            farmer_id = current_setting('app.current_user_id', TRUE)::uuid
            OR farm_id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
        );
    """)


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS flock_access ON flocks;")
    op.execute("DROP POLICY IF EXISTS farm_member_access ON farm_members;")
    op.execute("DROP POLICY IF EXISTS farm_access ON farms;")
    op.execute("DROP POLICY IF EXISTS user_self_access ON users;")

    # Disable RLS
    op.execute("ALTER TABLE flocks DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE farm_members DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE farms DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
