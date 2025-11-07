"""Add unique index on whatsapp_message_logs.whatsapp_message_id

Revision ID: a1b2c3d4e5f6
Revises: 6037a22f1fa2
Create Date: 2025-10-26 03:30:00.000000

"""
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6037a22f1fa2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    tables = set(insp.get_table_names())
    if 'whatsapp_message_logs' in tables:
        existing = {idx.get('name') for idx in insp.get_indexes('whatsapp_message_logs')}
        if 'uq_whatsapp_message_logs_message_id' not in existing:
            op.create_index(
                'uq_whatsapp_message_logs_message_id',
                'whatsapp_message_logs',
                ['whatsapp_message_id'],
                unique=True,
            )


def downgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    tables = set(insp.get_table_names())
    if 'whatsapp_message_logs' in tables:
        existing = {idx.get('name') for idx in insp.get_indexes('whatsapp_message_logs')}
        if 'uq_whatsapp_message_logs_message_id' in existing:
            op.drop_index('uq_whatsapp_message_logs_message_id', table_name='whatsapp_message_logs')

