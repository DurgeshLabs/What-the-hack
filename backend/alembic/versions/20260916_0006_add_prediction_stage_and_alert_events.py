"""Add predictions.predicted_stage and index alert_events.

predicted_attack_type answers "what kind of traffic"; the world model also predicts a
coarse kill-chain stage, which previously had nowhere to live and was overloaded onto
predicted_attack_type with values outside the feature-schema contract enum.

Revision ID: 20260916_0006
Revises: 20260902_0005
Create Date: 2026-09-16
"""

import sqlalchemy as sa
from alembic import op

revision = "20260916_0006"
down_revision = "20260902_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("predicted_stage", sa.String(length=40), nullable=True))
    # Alert timelines are always read newest-first for one alert.
    op.create_index("ix_alert_events_alert_created", "alert_events", ["alert_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_alert_created", table_name="alert_events")
    op.drop_column("predictions", "predicted_stage")
