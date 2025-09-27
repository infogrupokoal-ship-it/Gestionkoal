import functools
import os
from twilio.rest import Client

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from backend.auth import login_required
from backend.db import get_db
from flask import jsonify

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
    db.execute(
        'INSERT INTO notifications (user_id, message) VALUES (?, ?)',
        (user_id, message)
    )
    db.commit() # Commit immediately for notifications

def send_whatsapp_notification(db, user_id, message):
    from flask import current_app # Import current_app here to avoid circular imports
    import time

    # Fetch user's WhatsApp details
    user = db.execute(
        'SELECT whatsapp_number, whatsapp_opt_in FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    if user and user['whatsapp_opt_in'] and user['whatsapp_number']:
        whatsapp_number = user['whatsapp_number']
        
        # Twilio credentials from environment variables
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')

        if not all([account_sid, auth_token, twilio_whatsapp_number]):
            current_app.logger.warning("Twilio credentials not fully set. Cannot send WhatsApp message.",
                                       extra={'user_id': user_id, 'event': 'whatsapp_send_failed'})
            return None

        retries = 3
        for attempt in range(retries):
            try:
                client = Client(account_sid, auth_token)
                message_instance = client.messages.create(
                    from_=twilio_whatsapp_number,
                    body=message,
                    to=f'whatsapp:{whatsapp_number}'
                )
                current_app.logger.info(f"WhatsApp message sent. SID: {message_instance.sid}",
                                        extra={'user_id': user_id, 'event': 'whatsapp_sent', 'message_sid': message_instance.sid})
                return message_instance.sid
            except Exception as e:
                current_app.logger.error(f"Failed to send WhatsApp message (attempt {attempt + 1}/{retries}). Error: {e}",
                                         extra={'user_id': user_id, 'event': 'whatsapp_send_failed', 'error': str(e)})
                if attempt < retries - 1:
                    time.sleep(2 ** attempt) # Exponential backoff
        
        return None
