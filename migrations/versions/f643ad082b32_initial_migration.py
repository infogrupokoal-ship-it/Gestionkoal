"""Initial migration

Revision ID: f643ad082b32
Revises: 7ca4e60aebf4
Create Date: 2025-10-05 19:14:26.427546

"""
from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = 'f643ad082b32'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path("schema.sql").read_text(encoding="utf-8")
    for statement in [s.strip() for s in sql.split(";") if s.strip()]:
        op.execute(statement)


def downgrade():
    pass
