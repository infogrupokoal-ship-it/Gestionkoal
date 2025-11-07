"""Set composite primary key on user_roles

Revision ID: b4f0c1d2e3f4
Revises: a1b2c3d4e5f6
Create Date: 2025-10-26 18:40:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision = "b4f0c1d2e3f4"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _has_column(insp: Inspector, table: str, column: str) -> bool:
    return any(col["name"] == column for col in insp.get_columns(table))


def upgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    if "user_roles" not in insp.get_table_names():
        return
    if not _has_column(insp, "user_roles", "id"):
        return

    temp = op.create_table(
        "user_roles__tmp",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )

    old = sa.Table("user_roles", sa.MetaData(), autoload_with=bind)
    insert_stmt = sa.insert(temp).from_select(
        ["user_id", "role_id"],
        sa.select(old.c.user_id, old.c.role_id).distinct(),
    )
    op.execute(insert_stmt)

    op.drop_table("user_roles")
    op.rename_table("user_roles__tmp", "user_roles")


def downgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    if "user_roles" not in insp.get_table_names():
        return
    if _has_column(insp, "user_roles", "id"):
        return

    temp = op.create_table(
        "user_roles__tmp",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "role_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )

    current = sa.Table("user_roles", sa.MetaData(), autoload_with=bind)
    insert_stmt = sa.insert(temp).from_select(
        ["user_id", "role_id"],
        sa.select(current.c.user_id, current.c.role_id).distinct(),
    )
    op.execute(insert_stmt)

    op.drop_table("user_roles")
    op.rename_table("user_roles__tmp", "user_roles")
