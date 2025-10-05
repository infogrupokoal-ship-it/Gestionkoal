"""Initial migration

Revision ID: b768121f1c6e
Revises: f643ad082b32
Create Date: 2025-10-05 20:15:11.806643

"""
from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b768121f1c6e'
down_revision = 'f643ad082b32'
branch_labels = None
depends_on = None


def upgrade():
    sql = Path("schema.sql").read_text(encoding="utf-8")
    for statement in [s.strip() for s in sql.split(";") if s.strip()]:
        op.execute(statement)


def downgrade():
    pass
