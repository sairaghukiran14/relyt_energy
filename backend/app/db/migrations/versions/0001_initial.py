"""create actual_generation and wind_forecast

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actual_generation",
        sa.Column("start_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("generation_mw", sa.Float(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "wind_forecast",
        sa.Column("start_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("publish_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("generation_mw", sa.Float(), nullable=False),
        sa.Column("horizon_h", sa.Float(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wind_forecast_publish_time", "wind_forecast", ["publish_time"])


def downgrade() -> None:
    op.drop_index("ix_wind_forecast_publish_time", table_name="wind_forecast")
    op.drop_table("wind_forecast")
    op.drop_table("actual_generation")
