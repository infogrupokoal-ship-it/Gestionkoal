from flask import Blueprint, current_app, g, jsonify, render_template

from backend.auth import login_required
from backend.db import get_db
from backend.wa_client import send_whatsapp_text
from backend.whatsapp_meta import save_whatsapp_log

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def list_notifications():
    return render_template('notifications/list.html', title="Notificaciones")

@bp.route('/api/unread_notifications_count')
@login_required
def unread_notifications_count():
    db = get_db()
    count = db.execute(
        'SELECT COUNT(id) FROM notifications WHERE user_id = ? AND is_read = 0',
        (g.user.id,)
    ).fetchone()[0]
    return jsonify({'unread_count': count})

def add_notification(db, user_id, message):
    if db is None:
        current_app.logger.error("Database connection error in add_notification.")
        return
    try:
        db.execute(
            'INSERT INTO notifications (user_id, message) VALUES (?, ?)',
            (user_id, message)
        )
        db.commit()
    except Exception as e:
        current_app.logger.error(f"Error adding notification for user {user_id}: {e}", exc_info=True)
        db.rollback() # Commit immediately for notifications

def send_whatsapp_notification(db, user_id, message):
    if db is None:
        current_app.logger.error("Database connection error in send_whatsapp_notification.")
        return
    try:
        user_data = db.execute(
            'SELECT whatsapp_number, whatsapp_opt_in FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if user_data and user_data['whatsapp_opt_in'] and user_data['whatsapp_number']:
            to_number = user_data['whatsapp_number']
            message_id = send_whatsapp_text(to_number, message)

            if message_id:
                save_whatsapp_log(
                    job_id=None, material_id=None, provider_id=None,
                    direction='outbound', from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                    to_number=to_number, message_body=message, whatsapp_message_id=message_id,
                    status='sent', user_id=user_id
                )
            else:
                save_whatsapp_log(
                    job_id=None, material_id=None, provider_id=None,
                    direction='outbound', from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                    to_number=to_number, message_body=message, whatsapp_message_id=None,
                    status='failed', error_info='Failed to get message ID from WhatsApp API', user_id=user_id
                )
            db.commit()
        else:
            current_app.logger.info(f"WhatsApp notification not sent to user {user_id}: Opt-in or number missing.")
    except Exception as e:
        current_app.logger.error(f"Error sending WhatsApp notification to user {user_id}: {e}", exc_info=True)
        db.rollback()