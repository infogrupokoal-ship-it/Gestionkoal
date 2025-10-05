# backend/models.py
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, email=None, active=True, whatsapp_verified=False, referral_code=None, referred_by_user_id=None, **_):
        self.id = str(id)
        self.username = username
        self.email = email
        self._active = bool(active)
        self.whatsapp_verified = bool(whatsapp_verified)
        self.referral_code = referral_code
        self.referred_by_user_id = referred_by_user_id

    @property
    def is_active(self):
        return self._active

    def has_permission(self, permission_code):
        # Basic implementation: admin has all permissions, others have none for now
        # In a real app, this would query a permissions table based on user.role
        if self.username == 'admin': # Assuming 'admin' is the admin user
            return True
        # For other roles, you'd check against a predefined set of permissions
        # For now, only admin has permissions
        return False
