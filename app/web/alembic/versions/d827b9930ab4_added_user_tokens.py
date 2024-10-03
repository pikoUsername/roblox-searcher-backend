"""added user tokens

Revision ID: d827b9930ab4
Revises: 708a36b2a79e
Create Date: 2024-10-02 19:04:30.182985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd827b9930ab4'
down_revision: Union[str, None] = '708a36b2a79e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_tokens',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('roblox_name', sa.String(length=255), nullable=True),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_tokens'))
    )
    op.create_index(op.f('ix_user_tokens_id'), 'user_tokens', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_tokens_id'), table_name='user_tokens')
    op.drop_table('user_tokens')
    # ### end Alembic commands ###