"""oh

Revision ID: 708a36b2a79e
Revises: f7311ab62250
Create Date: 2024-09-26 14:16:52.125968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '708a36b2a79e'
down_revision: Union[str, None] = 'f7311ab62250'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transactions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('amount', sa.DECIMAL(), nullable=False),
    sa.Column('robux_amount', sa.DECIMAL(), nullable=False),
    sa.Column('game_id', sa.BIGINT(), nullable=False),
    sa.Column('gamepass_id', sa.BIGINT(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('roblox_username', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions'))
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    # ### end Alembic commands ###
