"""create churn_predictions table

Revision ID: e5b2c7d91a3f
Revises: d8f1e2a3b4c5
Create Date: 2026-10-11 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5b2c7d91a3f'
down_revision: Union[str, Sequence[str], None] = 'd8f1e2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'churn_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False),
        sa.Column('churn_probability', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=16), nullable=False),
        sa.Column('in_training_data', sa.Boolean(), nullable=False),
        sa.Column('predicted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'model_version', name='uq_churn_predictions_customer_model')
    )


def downgrade() -> None:
    op.drop_table('churn_predictions')