"""add workflow state to chat sessions

Revision ID: 834c8ce72301
Revises: b0864f103f3f
Create Date: 2026-07-05 22:29:52.643156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '834c8ce72301'
down_revision: Union[str, Sequence[str], None] = 'b0864f103f3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("workflow_state", sa.JSON(), nullable=True))
    pass


def downgrade() -> None:
    op.drop_column("chat_sessions", "workflow_state")
    pass
