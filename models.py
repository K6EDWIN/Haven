from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy() 

class Interaction(db.Model):
    __tablename__ = 'chatbot_interactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    user_input = db.Column(db.String(500), nullable=False)
    ai_response = db.Column(db.String(500), nullable=False)
    sentiment = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    event = db.Column(db.String(200), nullable=False)
    log_level = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(200), nullable=False)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    counselor_name = db.Column(db.String(100), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)


class ApiRequestMetric(db.Model):
    """Operational measurements only; never store request or response content."""
    __tablename__ = 'api_request_metrics'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(36), nullable=False, index=True)
    endpoint = db.Column(db.String(80), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    duration_ms = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(100), nullable=True)
    error_category = db.Column(db.String(30), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class HavenUser(db.Model):
    __tablename__ = 'haven_users'
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='active')
    pin_hash = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('haven_users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SavedConversation(db.Model):
    __tablename__ = 'saved_conversations'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('haven_users.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False, default='Safe Space conversation')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    messages = db.relationship('SavedMessage', cascade='all, delete-orphan', order_by='SavedMessage.position')


class SavedMessage(db.Model):
    __tablename__ = 'saved_messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('saved_conversations.id'), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)


class DiaryEntry(db.Model):
    __tablename__ = 'diary_entries'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('haven_users.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False, default='')
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AdminAuditLog(db.Model):
    __tablename__ = 'admin_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.String(36), nullable=False, index=True)
    action = db.Column(db.String(80), nullable=False)
    target_id = db.Column(db.String(36), nullable=True)
    outcome = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
