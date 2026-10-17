"""create users table and seed initial demo user

Revision ID: b9f5e4d3c2a1
Revises: a8e4d3c2b1f0
Create Date: 2026-10-17 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt

# revision identifiers, used by Alembic.
revision: str = 'b9f5e4d3c2a1'
down_revision: Union[str, Sequence[str], None] = 'a8e4d3c2b1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    users_table = op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=120), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='csm'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Seed initial demo user: csm@nexus.ai / Password123!
    hashed_pwd = bcrypt.hashpw(b"Password123!", bcrypt.gensalt()).decode("utf-8")
    op.bulk_insert(
        users_table,
        [
            {
                "email": "csm@nexus.ai",
                "hashed_password": hashed_pwd,
                "full_name": "Alex Vance (Lead CSM)",
                "role": "manager",
                "is_active": True,
            }
        ]
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')