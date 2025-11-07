"""Initial migration

Revision ID: b768121f1c6e
Revises: f643ad082b32
Create Date: 2025-10-05 20:15:11.806643

"""


# revision identifiers, used by Alembic.
revision = 'b768121f1c6e'
down_revision = 'f643ad082b32'
branch_labels = None
depends_on = None


def upgrade():
    # This migration is redundant and caused errors.
    # The initial schema is created by f643ad082b32.
    # Leaving this empty to resolve the conflict.
    pass


def downgrade():
    pass
