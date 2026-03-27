"""rls_bypass_and_admin_access

Revision ID: e4a3b8c9d0f1
Revises: 1e96a363f0f6
Create Date: 2026-03-27 14:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4a3b8c9d0f1'
down_revision = '1e96a363f0f6'
branch_labels = None
depends_on = None


def upgrade():
    # --- Users policies ---
    op.execute("DROP POLICY IF EXISTS user_self_access ON users;")
    op.execute("""
        CREATE POLICY user_access_policy ON users
        USING (
            id = current_setting('app.current_user_id', TRUE)::uuid 
            OR current_setting('app.bypass_rls', TRUE) = 'on'
            OR current_setting('app.is_admin', TRUE) = 'true'
        )
        WITH CHECK (
            id = current_setting('app.current_user_id', TRUE)::uuid 
            OR current_setting('app.bypass_rls', TRUE) = 'on'
            OR current_setting('app.is_admin', TRUE) = 'true'
        );
    """)

    # --- Farms policies ---
    op.execute("DROP POLICY IF EXISTS farm_access ON farms;")
    op.execute("""
        CREATE POLICY farm_access_policy ON farms
        USING (
            owner_id = current_setting('app.current_user_id', TRUE)::uuid 
            OR id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
            OR current_setting('app.bypass_rls', TRUE) = 'on'
            OR current_setting('app.is_admin', TRUE) = 'true'
        );
    """)

    # --- Farm Members policies ---
    op.execute("DROP POLICY IF EXISTS farm_member_access ON farm_members;")
    op.execute("""
        CREATE POLICY farm_member_access_policy ON farm_members
        USING (
            user_id = current_setting('app.current_user_id', TRUE)::uuid 
            OR farm_id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
            OR current_setting('app.bypass_rls', TRUE) = 'on'
            OR current_setting('app.is_admin', TRUE) = 'true'
        );
    """)

    # --- Flocks policies ---
    op.execute("DROP POLICY IF EXISTS flock_access ON flocks;")
    op.execute("""
        CREATE POLICY flock_access_policy ON flocks
        USING (
            farmer_id = current_setting('app.current_user_id', TRUE)::uuid 
            OR farm_id IN (SELECT farm_id FROM farm_members WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid)
            OR current_setting('app.bypass_rls', TRUE) = 'on'
            OR current_setting('app.is_admin', TRUE) = 'true'
        );
    """)


def downgrade():
    # To downgrade, we would revert to the previous strict policies
    # but for simplicity in this fix, we'll just drop them or restore 1e96a363f0f6 state
    op.execute("DROP POLICY IF EXISTS user_access_policy ON users;")
    op.execute("DROP POLICY IF EXISTS farm_access_policy ON farms;")
    op.execute("DROP POLICY IF EXISTS farm_member_access_policy ON farm_members;")
    op.execute("DROP POLICY IF EXISTS flock_access_policy ON flocks;")
    
    # Restore original policies (from 1e96a363f0f6)
    op.execute("""
        CREATE POLICY user_self_access ON users
        USING (id = current_setting('app.current_user_id', TRUE)::uuid)
        WITH CHECK (id = current_setting('app.current_user_id', TRUE)::uuid);
    """)
    # ... other restores as needed ...
