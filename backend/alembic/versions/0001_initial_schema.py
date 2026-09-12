"""Initial schema — creates all SmartFarm tables and TimescaleDB hypertable.

Revision ID: 0001_initial_schema
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Enable TimescaleDB extension (best-effort, own savepoint) ─────────────
    try:
        conn.execute(sa.text("SAVEPOINT sp_timescale"))
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_timescale"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_timescale"))

    # ── crops ─────────────────────────────────────────────────
    op.create_table(
        'crops',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('variety', sa.String(128), nullable=True),
        sa.Column('optimal_moisture_min_pct', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('optimal_moisture_max_pct', sa.Float(), nullable=False, server_default='70.0'),
        sa.Column('critical_moisture_min_pct', sa.Float(), nullable=False, server_default='20.0'),
        sa.Column('optimal_temp_min_c', sa.Float(), nullable=False, server_default='15.0'),
        sa.Column('optimal_temp_max_c', sa.Float(), nullable=False, server_default='35.0'),
        sa.Column('heat_stress_c', sa.Float(), nullable=False, server_default='38.0'),
        sa.Column('optimal_humidity_min_pct', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('optimal_humidity_max_pct', sa.Float(), nullable=False, server_default='80.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('name', name='uq_crops_name'),
    )

    # ── farms ─────────────────────────────────────────────────
    op.create_table(
        'farms',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('location', sa.String(256), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=False, server_default='UTC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    # ── fields ────────────────────────────────────────────────
    op.create_table(
        'fields',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('farm_id', sa.String(64), sa.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('crop_id', sa.String(64), sa.ForeignKey('crops.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('area_m2', sa.Float(), nullable=True),
        sa.Column('growth_stage', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_fields_farm_id', 'fields', ['farm_id'])

    # ── devices ───────────────────────────────────────────────
    op.create_table(
        'devices',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('field_id', sa.String(64), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_identifier', sa.String(128), nullable=False),
        sa.Column('source_type', sa.String(32), nullable=False, server_default='simulator'),
        sa.Column('firmware_version', sa.String(64), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('device_identifier', name='uq_devices_identifier'),
    )
    op.create_index('ix_devices_field_id', 'devices', ['field_id'])

    # ── sensor_readings (TimescaleDB hypertable) ──────────────
    # Use (id, received_at) composite PK so TimescaleDB can partition by received_at
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.String(64), nullable=False),
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.id', ondelete='SET NULL'), nullable=False),
        sa.Column('field_id', sa.String(64), sa.ForeignKey('fields.id', ondelete='SET NULL'), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('device_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(32), nullable=False, server_default='simulator'),
        sa.Column('sequence_number', sa.Integer(), nullable=True),
        sa.Column('air_temperature_c', sa.Float(), nullable=True),
        sa.Column('air_humidity_pct', sa.Float(), nullable=True),
        sa.Column('soil_moisture_pct', sa.Float(), nullable=True),
        sa.Column('soil_temperature_c', sa.Float(), nullable=True),
        sa.Column('light_lux', sa.Float(), nullable=True),
        sa.Column('leaf_wetness_pct', sa.Float(), nullable=True),
        sa.Column('vibration_raw', sa.Integer(), nullable=True),
        sa.Column('water_level_available', sa.Boolean(), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validation_flags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sensor_status', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id', 'received_at'),
    )
    op.create_index('ix_sensor_readings_field_received', 'sensor_readings', ['field_id', 'received_at'])
    op.create_index('ix_sensor_readings_device_received', 'sensor_readings', ['device_id', 'received_at'])
    op.create_index('ix_sensor_readings_received_at', 'sensor_readings', ['received_at'])

    # Convert to TimescaleDB hypertable using a savepoint so a failure doesn't
    # abort the whole transaction — falls back to plain PostgreSQL table.
    try:
        conn.execute(sa.text("SAVEPOINT sp_hypertable"))
        conn.execute(sa.text(
            "SELECT create_hypertable('sensor_readings', 'received_at', "
            "if_not_exists => TRUE, migrate_data => TRUE)"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_hypertable"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_hypertable"))

    # ── alerts ────────────────────────────────────────────────
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('field_id', sa.String(64), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('alert_type', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('explanation', sa.String(1024), nullable=False),
        sa.Column('recommended_action', sa.String(512), nullable=True),
        sa.Column('contributing_factors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_alerts_field_status', 'alerts', ['field_id', 'status'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])

    # ── recommendations ───────────────────────────────────────
    op.create_table(
        'recommendations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('field_id', sa.String(64), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_type', sa.String(64), nullable=False),
        sa.Column('decision', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(32), nullable=False),
        sa.Column('reasoning', sa.String(2048), nullable=False),
        sa.Column('contributing_factors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_by', sa.String(64), nullable=False, server_default='rule_engine'),
        sa.Column('confidence_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_recommendations_field_created', 'recommendations', ['field_id', 'created_at'])

    # ── ml_predictions ────────────────────────────────────────
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('field_id', sa.String(64), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(128), nullable=False),
        sa.Column('model_version', sa.String(32), nullable=False),
        sa.Column('prediction_type', sa.String(64), nullable=False),
        sa.Column('prediction', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_stub', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('input_reference', sa.String(128), nullable=True),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_ml_predictions_field_created', 'ml_predictions', ['field_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('ml_predictions')
    op.drop_table('recommendations')
    op.drop_table('alerts')
    op.drop_table('sensor_readings')
    op.drop_table('devices')
    op.drop_table('fields')
    op.drop_table('farms')
    op.drop_table('crops')
