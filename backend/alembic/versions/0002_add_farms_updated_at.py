"""Add missing updated_at column to farms table.

The initial migration omitted farms.updated_at even though the ORM model
declares it, causing every MQTT telemetry ingestion to fail with:
  asyncpg.UndefinedColumnError: column farms.updated_at does not exist

Revision ID: 0002_add_farms_updated_at
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0002_add_farms_updated_at'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the missing updated_at column to farms, defaulting to created_at
    # for existing rows so the NOT NULL constraint is satisfied immediately.
    op.add_column(
        'farms',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('farms', 'updated_at')
