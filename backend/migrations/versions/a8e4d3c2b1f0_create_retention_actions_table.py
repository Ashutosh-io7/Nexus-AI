"""create retention actions table

Revision ID: a8e4d3c2b1f0
Revises: f9bf4859f869
Create Date: 2026-10-17 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8e4d3c2b1f0'
down_revision: Union[str, Sequence[str], None] = 'f9bf4859f869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'retention_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='proposed'),
        sa.Column('churn_probability', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=16), nullable=False),
        sa.Column('risk_drivers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('cohort_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=False),
        sa.Column('action_strategy', sa.Text(), nullable=False),
        sa.Column('policy_citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('email_subject', sa.String(length=255), nullable=False),
        sa.Column('email_body', sa.Text(), nullable=False),
        sa.Column('csm_notes', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_retention_actions_customer_id'), 'retention_actions', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_retention_actions_customer_id'), table_name='retention_actions')
    op.drop_table('retention_actions')