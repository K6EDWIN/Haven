from flask import Flask, request, jsonify, render_template_string, render_template, g
from datetime import datetime, timedelta
from functools import wraps
import hmac
import hashlib
import math
import os
import re
import secrets
import sys
import time
import uuid
from app_logic import (
    analyze_sentiment, 
    check_in_initial, 
    extract_entities_conversational, 
    get_resources, 
    check_in, 
    schedule_appointment,
    get_safe_space_response
)
from models import (db, Interaction, ApiRequestMetric, HavenUser, UserSession,
                    SavedConversation, SavedMessage, DiaryEntry, AdminAuditLog, GoogleIdentity)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
_auth_failures = {}
_pin_failures = {}
_admin_bootstrap_checked = False

# --- DATABASE CONFIGURATION ---
database_url = os.environ.get('DATABASE_URL')
turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 240,
        'pool_size': 1,
        'max_overflow': 0,
    }
elif not turso_url:
    if os.environ.get('VERCEL') == '1' or os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError('Set DATABASE_URL to a production PostgreSQL connection string (Neon is supported).')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
else:
    if turso_url.startswith("libsql://"):
        turso_url = turso_url.replace("libsql://", "sqlite+libsql://")
    app.config['SQLALCHEMY_DATABASE_URI'] = f"{turso_url}?secure=true"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"auth_token": turso_token}
    }

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Haven Terminal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background-color: #0d1117; color: #00ff41; font-family: 'Courier New', Courier, monospace; margin: 0; padding: 20px; display: flex; flex-direction: column; height: 95vh; }
        h1 { margin: 0 0 10px 0; text-shadow: 0 0 5px #00ff41; border-bottom: 1px solid #00ff41; padding-bottom: 10px; }
        #terminal { flex-grow: 1; overflow-y: auto; white-space: pre-wrap; margin-bottom: 20px; padding: 10px; border: 1px solid #30363d; background: #000; border-radius: 5px; }
        .input-line { display: flex; align-items: center; }
        .prompt { color: #00ff41; margin-right: 10px; font-weight: bold; }
        input { background: transparent; border: none; color: #fff; font-family: inherit; font-size: 1.1em; flex-grow: 1; outline: none; }
        .bot-msg { color: #c9d1d9; margin: 5px 0; line-height: 1.4; }
        .user-msg { color: #00ff41; margin: 10px 0 5px 0; font-weight: bold; }
        .system-msg { color: #f0ad4e; font-style: italic; margin-top: 5px; }
        .error-msg { color: #ff6b6b; }
        a { color: #58a6ff; text-decoration: none; border-bottom: 1px dotted #58a6ff; }
        
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; }
    </style>
</head>
<body>
    <h1>Haven v2.0 [Online]</h1>
    <div id="terminal">
        <div class="system-msg">System initialized...</div>
        <div class="system-msg">Connecting to Haven Core... Connected.</div>
        <br>
        <div class="bot-msg">Welcome to Haven. I'm here to support you.</div>
        <div class="bot-msg">How can I help you right now?</div>
        <div class="bot-msg">-------------------------</div>
        <div class="bot-msg">[1] Safe Space (Chat)</div>
        <div class="bot-msg">[2] Insight Mode (Analyze Text)</div>
        <div class="bot-msg">[3] Daily Check-in (Log)</div>
        <div class="bot-msg">[4] Resources</div>
        <div class="bot-msg">[5] Schedule Appointment</div>
        <br>
    </div>
    <div class="input-line">
        <span class="prompt" id="prompt-text">menu ></span>
        <input type="text" id="user-input" autofocus autocomplete="off">
    </div>

    <script>
        const terminal = document.getElementById('terminal');
        const input = document.getElementById('user-input');
        const promptText = document.getElementById('prompt-text');
        
        let currentMode = 'menu';
        let appointmentStep = 0;
        let appointmentData = {};

        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                const text = input.value;
                if (!text) return;
                
                printToTerminal(text, 'user');
                input.value = '';
                processCommand(text);
            }
        });

        function printToTerminal(text, type) {
            const div = document.createElement('div');
            div.className = type === 'user' ? 'user-msg' : (type === 'system' ? 'system-msg' : 'bot-msg');
            
            // Format timestamps for system messages
            if(type === 'system') {
                div.innerText = `[System]: ${text}`;
            } else if(type === 'user') {
                div.innerText = `> ${text}`;
            } else {
                div.innerText = text; // Bot message
            }
            
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function processCommand(text) {
            const cmd = text.trim();
            const lowerCmd = cmd.toLowerCase();

            // --- GLOBAL COMMANDS ---
            // Allow returning to menu from ANY state
            if (lowerCmd === 'exit' || lowerCmd === 'menu' || lowerCmd === 'back') {
                resetToMenu();
                return;
            }

            // --- MENU LOGIC ---
            if (currentMode === 'menu') {
                if (cmd === '1') {
                    currentMode = 'safe_space';
                    promptText.innerText = 'safe-space >';
                    printToTerminal("Entering Safe Space. I'm listening—how are things going?", "bot");
                } else if (cmd === '2') {
                    currentMode = 'entities';
                    promptText.innerText = 'insight >';
                    printToTerminal("Insight Mode: Tell me about your situation, and I'll identify the key topics.", "bot");
                } else if (cmd === '3') {
                    currentMode = 'check_in';
                    promptText.innerText = 'check-in >';
                    printToTerminal("Daily Log: How are you feeling right now? (This will be saved).", "bot");
                } else if (cmd === '4') {
                    fetchResources();
                } else if (cmd === '5') {
                    startAppointment();
                } else {
                    // Chatbot fallback for menu: treat random text as a safe space entry or confusion
                    printToTerminal("Please select an option (1-5) or type 'exit'.", "system");
                }
                return;
            }

            // --- SAFE SPACE LOGIC ---
            if (currentMode === 'safe_space') {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                printToTerminal(data.response, 'bot');
            }

            // --- ENTITY/INSIGHT LOGIC ---
            else if (currentMode === 'entities') {
                const res = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                printToTerminal(data.entities, 'bot'); // Now returns a sentence
                printToTerminal("Anything else you want to analyze? (Or type 'menu')", "system");
            }

            // --- CHECK-IN LOGIC ---
            else if (currentMode === 'check_in') {
                const res = await fetch('/api/checkin', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text, user_id: 'web-user' })
                });
                const data = await res.json();
                printToTerminal(data.response, 'bot');
                // Auto-return to menu after logging to prevent confusion
                setTimeout(() => {
                    printToTerminal("Log saved. Returning to menu...", "system");
                    resetToMenu();
                }, 2000);
            }

            // --- APPOINTMENT LOGIC ---
            else if (currentMode === 'appointment') {
                handleAppointmentStep(text);
            }
        }

        function resetToMenu() {
            currentMode = 'menu';
            appointmentStep = 0;
            promptText.innerText = 'menu >';
            printToTerminal("-------------------------", "bot");
            printToTerminal("Main Menu: 1. Safe Space | 2. Insights | 3. Check-in | 4. Resources | 5. Appointment", "bot");
        }

        async function fetchResources() {
            printToTerminal("Fetching library...", "system");
            const res = await fetch('/api/resources');
            const data = await res.json();
            printToTerminal("Here are some helpful resources:", "bot");
            data.forEach(r => {
                const linkDiv = document.createElement('div');
                linkDiv.innerHTML = `• <a href="${r.link}" target="_blank">${r.name}</a>`;
                terminal.appendChild(linkDiv);
            });
            printToTerminal("Type 'menu' to return.", "system");
        }

        function startAppointment() {
            currentMode = 'appointment';
            appointmentStep = 1;
            appointmentData = {};
            promptText.innerText = 'scheduler >';
            printToTerminal("Appointment Scheduler. First, please enter your User ID:", "bot");
        }

        async function handleAppointmentStep(text) {
            if (appointmentStep === 1) {
                appointmentData.user_id = text;
                appointmentStep = 2;
                printToTerminal(`Okay, ID: ${text}. Which counselor would you like to see?`, "bot");
            } else if (appointmentStep === 2) {
                appointmentData.counselor = text;
                appointmentStep = 3;
                printToTerminal(`Checking ${text}'s availability... Enter preferred time (YYYY-MM-DD HH:MM):`, "bot");
            } else if (appointmentStep === 3) {
                appointmentData.time = text;
                printToTerminal("Booking slot...", "system");
                
                const res = await fetch('/api/appointment', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(appointmentData)
                });
                const data = await res.json();
                printToTerminal(data.message, 'bot');
                
                setTimeout(() => {
                    resetToMenu();
                }, 2000);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# --- API Endpoints ---

@app.route('/api/resources')
def resources():
    return jsonify(get_resources())

@app.after_request
def add_mobile_cors(response):
    # Allow only the local browser origins used by Vite and Capacitor.
    origin = request.headers.get('Origin')
    allowed_origins = {
        'http://localhost:5173', 'http://127.0.0.1:5173',
        'http://localhost', 'https://localhost', 'capacitor://localhost', 'http://localhost:3000'
    }
    allowed_origins.update(origin.strip() for origin in os.environ.get('HAVEN_ALLOWED_ORIGINS', '').split(',') if origin.strip())
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return response


@app.before_request
def begin_api_measurement():
    if request.path.startswith('/api/') and request.method != 'OPTIONS':
        g.haven_request_started = time.perf_counter()
        g.haven_request_id = str(uuid.uuid4())


@app.after_request
def record_api_measurement(response):
    started = getattr(g, 'haven_request_started', None)
    if started is None:
        return response

    request_id = getattr(g, 'haven_request_id', str(uuid.uuid4()))
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Response-Time-ms'] = str(duration_ms)

    status = response.status_code
    error_category = 'server_error' if status >= 500 else ('client_error' if status >= 400 else None)
    try:
        db.session.add(ApiRequestMetric(
            request_id=request_id,
            endpoint=(request.endpoint or 'unmatched')[:80],
            method=request.method,
            status_code=status,
            duration_ms=duration_ms,
            model_version=os.environ.get('HAVEN_MODEL_VERSION', 'haven-rule-based-textblob')
                if request.endpoint == 'chat_mode' else None,
            error_category=error_category,
        ))
        # Keep operational telemetry bounded. No request/response content is stored.
        ApiRequestMetric.query.filter(
            ApiRequestMetric.timestamp < datetime.utcnow() - timedelta(days=30)
        ).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.warning('Could not persist privacy-safe API metrics')
    return response


def require_admin_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = os.environ.get('HAVEN_ADMIN_TOKEN', '')
        if not expected:
            return jsonify({'error': 'Admin access is not configured'}), 503
        if len(expected) < 32:
            return jsonify({'error': 'Admin token configuration is invalid'}), 503
        authorization = request.headers.get('Authorization', '')
        supplied = authorization[7:] if authorization.startswith('Bearer ') else ''
        if not hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8')):
            return jsonify({'error': 'Unauthorized'}), 401
        return view(*args, **kwargs)
    return wrapped


def hash_secret(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode('utf-8'), bytes.fromhex(salt), 310000).hex()
    return f'{salt}${digest}'


@app.before_request
def bootstrap_first_admin():
    global _admin_bootstrap_checked
    if _admin_bootstrap_checked:
        return
    email = os.environ.get('HAVEN_ADMIN_EMAIL', '').strip().lower()
    password = os.environ.get('HAVEN_ADMIN_PASSWORD', '')
    if not email or len(password) < 12:
        _admin_bootstrap_checked = True
        return
    try:
        if HavenUser.query.filter_by(role='admin').count() == 0 and not HavenUser.query.filter_by(email=email).first():
            db.session.add(HavenUser(id=str(uuid.uuid4()), email=email,
                                     password_hash=hash_secret(password), role='admin'))
            db.session.commit()
        _admin_bootstrap_checked = True
    except Exception:
        db.session.rollback()
        app.logger.warning('Could not bootstrap the initial administrator account')


def verify_secret(value, encoded):
    try:
        salt, expected = encoded.split('$', 1)
        actual = hash_secret(value, salt).split('$', 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


def auth_rate_limited(email):
    now = time.time()
    key = hashlib.sha256((email or '').strip().lower().encode('utf-8')).hexdigest()
    recent = [stamp for stamp in _auth_failures.get(key, []) if now - stamp < 900]
    _auth_failures[key] = recent
    return len(recent) >= 10


def record_auth_failure(email):
    now = time.time()
    key = hashlib.sha256((email or '').strip().lower().encode('utf-8')).hexdigest()
    _auth_failures[key] = [stamp for stamp in _auth_failures.get(key, []) if now - stamp < 900] + [now]


def current_user():
    authorization = request.headers.get('Authorization', '')
    token = authorization[7:] if authorization.startswith('Bearer ') else ''
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    session = UserSession.query.filter_by(token_hash=token_hash).first()
    if not session or session.expires_at <= datetime.utcnow():
        return None
    user = db.session.get(HavenUser, session.user_id)
    return user if user and user.status == 'active' else None


def issue_session(user):
    raw_token = secrets.token_urlsafe(48)
    db.session.add(UserSession(id=str(uuid.uuid4()), user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(days=30)))
    return raw_token


def verify_google_credential(credential):
    # CLIENT_ID supports the existing Vercel environment variable name; prefer
    # the explicit name documented for Haven's API project.
    client_id = (os.environ.get('GOOGLE_CLIENT_ID') or os.environ.get('CLIENT_ID') or '').strip()
    if not client_id:
        raise RuntimeError('Google sign-in is not configured')
    if not isinstance(credential, str) or not credential or len(credential) > 12000:
        raise ValueError('Invalid Google credential')
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    claims = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    if claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
        raise ValueError('Invalid Google credential issuer')
    if not claims.get('sub') or not claims.get('email') or claims.get('email_verified') is not True:
        raise ValueError('Google must provide a verified email address')
    return claims


def require_user(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        g.haven_user = user
        return view(*args, **kwargs)
    return wrapped


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user:
            if user.role != 'admin':
                return jsonify({'error': 'Administrator access required'}), 403
            g.haven_user = user
            return view(*args, **kwargs)
        # Migration fallback for existing single-token deployments.
        expected = os.environ.get('HAVEN_ADMIN_TOKEN', '')
        authorization = request.headers.get('Authorization', '')
        supplied = authorization[7:] if authorization.startswith('Bearer ') else ''
        if len(expected) >= 32 and hmac.compare_digest(supplied.encode(), expected.encode()):
            g.haven_admin_actor = 'shared-token-admin'
            return view(*args, **kwargs)
        return jsonify({'error': 'Administrator authentication required'}), 401
    return wrapped


def audit_admin(action, target_id=None, outcome='success'):
    actor_id = getattr(getattr(g, 'haven_user', None), 'id', None) or getattr(g, 'haven_admin_actor', 'unknown')
    db.session.add(AdminAuditLog(actor_id=actor_id, action=action, target_id=target_id, outcome=outcome))


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')
    password = data.get('password', '')
    if not isinstance(email, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254:
        return jsonify({'error': 'A valid email is required'}), 400
    if not isinstance(password, str) or len(password) < 12 or len(password) > 256:
        return jsonify({'error': 'Password must be at least 12 characters'}), 400
    normalized = email.strip().lower()
    if HavenUser.query.filter_by(email=normalized).first():
        return jsonify({'error': 'Unable to create account with these details'}), 409
    user = HavenUser(id=str(uuid.uuid4()), email=normalized, password_hash=hash_secret(password))
    db.session.add(user)
    db.session.flush()
    raw_token = secrets.token_urlsafe(48)
    db.session.add(UserSession(id=str(uuid.uuid4()), user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(days=30)))
    db.session.commit()
    return jsonify({'token': raw_token, 'user': {'id': user.id, 'email': user.email, 'role': user.role}}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')
    password = data.get('password', '')
    if not isinstance(email, str) or auth_rate_limited(email):
        return jsonify({'error': 'Too many sign-in attempts. Try again in 15 minutes.'}), 429
    user = HavenUser.query.filter_by(email=email.strip().lower()).first() if isinstance(email, str) else None
    if not user or user.status != 'active' or not isinstance(password, str) or not verify_secret(password, user.password_hash):
        record_auth_failure(email)
        return jsonify({'error': 'Email or password is incorrect'}), 401
    _auth_failures.pop(hashlib.sha256(email.strip().lower().encode('utf-8')).hexdigest(), None)
    raw_token = secrets.token_urlsafe(48)
    db.session.add(UserSession(id=str(uuid.uuid4()), user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(days=30)))
    db.session.commit()
    return jsonify({'token': raw_token, 'user': {'id': user.id, 'email': user.email, 'role': user.role}})


@app.route('/api/auth/google', methods=['POST'])
def google_login():
    data = request.get_json(silent=True) or {}
    try:
        claims = verify_google_credential(data.get('credential'))
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception:
        return jsonify({'error': 'Could not verify your Google sign-in. Please try again.'}), 401

    identity = GoogleIdentity.query.filter_by(subject=claims['sub']).first()
    if identity:
        user = db.session.get(HavenUser, identity.user_id)
        if not user or user.status != 'active':
            return jsonify({'error': 'This Haven account is not active'}), 403
    else:
        email = claims['email'].strip().lower()
        user = HavenUser.query.filter_by(email=email).first()
        # Require an authenticated password session to link an existing account.
        if user:
            return jsonify({'error': 'This email already has a Haven account. Sign in with your password, then link Google from account settings.'}), 409
        user = HavenUser(id=str(uuid.uuid4()), email=email,
                         password_hash=hash_secret(secrets.token_urlsafe(48)))
        db.session.add(user)
        db.session.flush()
        db.session.add(GoogleIdentity(subject=claims['sub'], user_id=user.id))

    raw_token = issue_session(user)
    db.session.commit()
    return jsonify({'token': raw_token, 'user': {'id': user.id, 'email': user.email, 'role': user.role}})


@app.route('/api/auth/google/link', methods=['POST'])
@require_user
def google_link():
    data = request.get_json(silent=True) or {}
    try:
        claims = verify_google_credential(data.get('credential'))
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception:
        return jsonify({'error': 'Could not verify your Google sign-in. Please try again.'}), 401
    if claims['email'].strip().lower() != g.haven_user.email.lower():
        return jsonify({'error': 'The verified Google email must match your Haven account email'}), 409
    existing = GoogleIdentity.query.filter_by(subject=claims['sub']).first()
    if existing and existing.user_id != g.haven_user.id:
        return jsonify({'error': 'That Google account is already connected to another Haven account'}), 409
    if not existing:
        db.session.add(GoogleIdentity(subject=claims['sub'], user_id=g.haven_user.id))
        db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/auth/me')
@require_user
def auth_me():
    user = g.haven_user
    return jsonify({'id': user.id, 'email': user.email, 'role': user.role})


@app.route('/api/auth/logout', methods=['POST'])
@require_user
def logout():
    authorization = request.headers.get('Authorization', '')
    token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    UserSession.query.filter_by(token_hash=token_hash, user_id=g.haven_user.id).delete()
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/conversations', methods=['GET', 'POST'])
@require_user
def conversations():
    if request.method == 'GET':
        items = (SavedConversation.query.filter_by(user_id=g.haven_user.id)
                 .order_by(SavedConversation.updated_at.desc()).all())
        return jsonify([{'id': item.id, 'title': item.title, 'created_at': item.created_at.isoformat() + 'Z',
                         'updated_at': item.updated_at.isoformat() + 'Z'} for item in items])
    data = request.get_json(silent=True) or {}
    messages = data.get('messages')
    title = data.get('title', 'Safe Space conversation')
    if not isinstance(title, str) or len(title) > 120 or not isinstance(messages, list) or not 1 <= len(messages) <= 100:
        return jsonify({'error': 'Provide a title and 1–100 messages'}), 400
    convo = SavedConversation(id=str(uuid.uuid4()), user_id=g.haven_user.id, title=title.strip() or 'Safe Space conversation')
    for index, message in enumerate(messages):
        role, content = (message.get('role'), message.get('content')) if isinstance(message, dict) else (None, None)
        if role not in ('user', 'haven') or not isinstance(content, str) or not content.strip() or len(content) > 5000:
            return jsonify({'error': 'Each message needs a valid role and content up to 5000 characters'}), 400
        convo.messages.append(SavedMessage(role=role, content=content.strip(), position=index))
    db.session.add(convo)
    db.session.commit()
    return jsonify({'id': convo.id, 'title': convo.title}), 201


@app.route('/api/conversations/<conversation_id>', methods=['GET', 'DELETE'])
@require_user
def conversation_detail(conversation_id):
    item = SavedConversation.query.filter_by(id=conversation_id, user_id=g.haven_user.id).first()
    if not item:
        return jsonify({'error': 'Conversation not found'}), 404
    if request.method == 'DELETE':
        db.session.delete(item)
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'id': item.id, 'title': item.title, 'messages': [
        {'role': message.role, 'content': message.content} for message in item.messages]})


@app.route('/api/diary', methods=['GET', 'POST'])
@require_user
def diary():
    if request.method == 'GET':
        items = DiaryEntry.query.filter_by(user_id=g.haven_user.id).order_by(DiaryEntry.updated_at.desc()).all()
        return jsonify([{'id': item.id, 'title': item.title, 'content': item.content, 'mood': item.mood,
                         'created_at': item.created_at.isoformat() + 'Z', 'updated_at': item.updated_at.isoformat() + 'Z'} for item in items])
    data = request.get_json(silent=True) or {}
    title, content, mood = data.get('title', ''), data.get('content'), data.get('mood')
    if not isinstance(title, str) or len(title) > 120 or not isinstance(content, str) or not content.strip() or len(content) > 20000:
        return jsonify({'error': 'A diary entry up to 20000 characters is required'}), 400
    if mood is not None and (not isinstance(mood, str) or len(mood) > 30):
        return jsonify({'error': 'Mood must be a short label'}), 400
    item = DiaryEntry(id=str(uuid.uuid4()), user_id=g.haven_user.id, title=title.strip(), content=content.strip(), mood=mood)
    db.session.add(item)
    db.session.commit()
    return jsonify({'id': item.id}), 201


@app.route('/api/diary/<entry_id>', methods=['PATCH', 'DELETE'])
@require_user
def diary_detail(entry_id):
    item = DiaryEntry.query.filter_by(id=entry_id, user_id=g.haven_user.id).first()
    if not item:
        return jsonify({'error': 'Diary entry not found'}), 404
    if request.method == 'DELETE':
        db.session.delete(item)
        db.session.commit()
        return jsonify({'ok': True})
    data = request.get_json(silent=True) or {}
    if 'title' in data:
        if not isinstance(data['title'], str) or len(data['title']) > 120: return jsonify({'error': 'Invalid title'}), 400
        item.title = data['title'].strip()
    if 'content' in data:
        if not isinstance(data['content'], str) or not data['content'].strip() or len(data['content']) > 20000: return jsonify({'error': 'Invalid content'}), 400
        item.content = data['content'].strip()
    if 'mood' in data:
        if data['mood'] is not None and (not isinstance(data['mood'], str) or len(data['mood']) > 30): return jsonify({'error': 'Invalid mood'}), 400
        item.mood = data['mood']
    item.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/security/pin', methods=['PUT'])
@require_user
def set_pin():
    data = request.get_json(silent=True) or {}
    pin = data.get('pin')
    if not isinstance(pin, str) or not re.fullmatch(r'\d{6}', pin):
        return jsonify({'error': 'PIN must contain exactly six digits'}), 400
    g.haven_user.pin_hash = hash_secret(pin)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/security/pin/verify', methods=['POST'])
@require_user
def verify_pin():
    pin = (request.get_json(silent=True) or {}).get('pin')
    now = time.time()
    recent = [stamp for stamp in _pin_failures.get(g.haven_user.id, []) if now - stamp < 900]
    _pin_failures[g.haven_user.id] = recent
    if len(recent) >= 5:
        return jsonify({'error': 'Too many PIN attempts. Try again in 15 minutes.'}), 429
    if not isinstance(pin, str) or not g.haven_user.pin_hash or not verify_secret(pin, g.haven_user.pin_hash):
        _pin_failures[g.haven_user.id] = recent + [now]
        return jsonify({'error': 'PIN is incorrect or not configured'}), 401
    _pin_failures.pop(g.haven_user.id, None)
    return jsonify({'ok': True})


def metric_percentile(values, percentile):
    if not values:
        return 0
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percentile) - 1)], 2)


def metrics_since(since):
    return ApiRequestMetric.query.filter(ApiRequestMetric.timestamp >= since).all()


@app.route('/admin')
def admin_console():
    response = app.make_response(render_template('admin.html'))
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/api/admin/overview')
@require_admin
def admin_overview():
    rows = metrics_since(datetime.utcnow() - timedelta(hours=24))
    durations = [row.duration_ms for row in rows]
    failures = sum(1 for row in rows if row.status_code >= 500)
    chat_requests = sum(1 for row in rows if row.endpoint == 'chat_mode')
    audit_admin('overview.view')
    db.session.commit()
    return jsonify({
        'period': '24h',
        'request_count': len(rows),
        'server_error_count': failures,
        'server_error_rate': round((failures / len(rows)) * 100, 2) if rows else 0,
        'median_latency_ms': metric_percentile(durations, 0.5),
        'p95_latency_ms': metric_percentile(durations, 0.95),
        'chat_requests': chat_requests,
        'model_version': os.environ.get('HAVEN_MODEL_VERSION', 'haven-rule-based-textblob'),
        'updated_at': datetime.utcnow().isoformat() + 'Z',
    })


@app.route('/api/admin/model/metrics')
@require_admin
def admin_model_metrics():
    rows = metrics_since(datetime.utcnow() - timedelta(days=7))
    by_endpoint = {}
    for row in rows:
        item = by_endpoint.setdefault(row.endpoint, {'request_count': 0, 'server_error_count': 0, 'latencies': []})
        item['request_count'] += 1
        item['server_error_count'] += int(row.status_code >= 500)
        item['latencies'].append(row.duration_ms)
    result = []
    for endpoint, item in sorted(by_endpoint.items()):
        result.append({
            'endpoint': endpoint,
            'request_count': item['request_count'],
            'server_error_count': item['server_error_count'],
            'median_latency_ms': metric_percentile(item['latencies'], 0.5),
            'p95_latency_ms': metric_percentile(item['latencies'], 0.95),
        })
    audit_admin('model_metrics.view')
    db.session.commit()
    return jsonify({'period': '7d', 'endpoints': result})


@app.route('/api/admin/events')
@require_admin
def admin_events():
    rows = (ApiRequestMetric.query
            .order_by(ApiRequestMetric.timestamp.desc())
            .limit(100).all())
    audit_admin('events.view')
    db.session.commit()
    return jsonify([{
        'request_id': row.request_id,
        'endpoint': row.endpoint,
        'method': row.method,
        'status_code': row.status_code,
        'duration_ms': row.duration_ms,
        'error_category': row.error_category,
        'timestamp': row.timestamp.isoformat() + 'Z',
    } for row in rows])


@app.route('/api/admin/users')
@require_admin
def admin_users():
    rows = HavenUser.query.order_by(HavenUser.created_at.desc()).limit(500).all()
    audit_admin('users.list')
    db.session.commit()
    return jsonify([{'id': row.id, 'email': row.email, 'role': row.role, 'status': row.status,
                     'created_at': row.created_at.isoformat() + 'Z'} for row in rows])


@app.route('/api/admin/audit-logs')
@require_admin
def admin_audit_logs():
    rows = AdminAuditLog.query.order_by(AdminAuditLog.timestamp.desc()).limit(200).all()
    audit_admin('audit_logs.view')
    db.session.commit()
    return jsonify([{'actor_id': row.actor_id, 'action': row.action, 'target_id': row.target_id,
                     'outcome': row.outcome, 'timestamp': row.timestamp.isoformat() + 'Z'} for row in rows])


@app.route('/api/admin/users/<user_id>/status', methods=['PATCH'])
@require_admin
def admin_user_status(user_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    user = db.session.get(HavenUser, user_id)
    if not user or status not in ('active', 'disabled'):
        return jsonify({'error': 'User or status is invalid'}), 404
    if getattr(g, 'haven_user', None) and user.id == g.haven_user.id and status == 'disabled':
        return jsonify({'error': 'You cannot disable your own account'}), 400
    user.status = status
    audit_admin('users.status.update', user.id)
    if status == 'disabled':
        UserSession.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/users/<user_id>/role', methods=['PATCH'])
@require_admin
def admin_user_role(user_id):
    data = request.get_json(silent=True) or {}
    role = data.get('role')
    user = db.session.get(HavenUser, user_id)
    if not user or role not in ('admin', 'user'):
        return jsonify({'error': 'User or role is invalid'}), 404
    if user.role == 'admin' and role == 'user' and HavenUser.query.filter_by(role='admin', status='active').count() <= 1:
        return jsonify({'error': 'At least one active administrator is required'}), 409
    user.role = role
    audit_admin('users.role.update', user.id)
    db.session.commit()
    return jsonify({'ok': True})


@app.cli.command('create-admin')
def create_admin_command():
    """Create an admin account interactively; credentials are never stored in logs."""
    import click
    email = click.prompt('Admin email').strip().lower()
    password = click.prompt('Admin password (12+ characters)', hide_input=True, confirmation_prompt=True)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(password) < 12:
        raise click.ClickException('Provide a valid email and password of at least 12 characters')
    user = HavenUser.query.filter_by(email=email).first()
    if user:
        user.role = 'admin'
        user.password_hash = hash_secret(password)
        user.status = 'active'
    else:
        db.session.add(HavenUser(id=str(uuid.uuid4()), email=email,
                                 password_hash=hash_secret(password), role='admin'))
    db.session.commit()
    click.echo('Administrator account ready.')

@app.route('/api/chat', methods=['POST'])
def chat_mode():
    data = request.get_json(silent=True) or {}
    msg = data.get('message', '')
    if not isinstance(msg, str) or not msg.strip() or len(msg) > 500:
        return jsonify({'error': 'message must be a non-empty string up to 500 characters'}), 400
    response = get_safe_space_response(msg)
    return jsonify({"response": response})

@app.route('/api/extract', methods=['POST'])
def extract_mode():
    data = request.get_json(silent=True) or {}
    msg = data.get('message', '')
    if not isinstance(msg, str) or not msg.strip() or len(msg) > 500:
        return jsonify({'error': 'message must be a non-empty string up to 500 characters'}), 400
    entities = extract_entities_conversational(msg)
    return jsonify({"entities": entities})

@app.route('/api/checkin', methods=['POST'])
@require_user
def checkin_mode():
    data = request.get_json(silent=True) or {}
    msg = data.get('message', '')
    if not isinstance(msg, str) or not msg.strip() or len(msg) > 500:
        return jsonify({'error': 'message must be a non-empty string up to 500 characters'}), 400
    response = check_in(g.haven_user.id, msg)
    return jsonify({"response": response})

@app.route('/api/appointment', methods=['POST'])
@require_user
def appointment_mode():
    data = request.get_json(silent=True) or {}
    try:
        from datetime import datetime
        user_id = g.haven_user.id
        counselor = data.get('counselor')
        raw_time = data.get('time')
        if not all(isinstance(value, str) and value.strip() for value in (user_id, counselor, raw_time)):
            return jsonify({'message': 'user_id, counselor, and time are required'}), 400
        if len(user_id) > 50 or len(counselor) > 100:
            return jsonify({'message': 'user_id or counselor name is too long'}), 400
        appt_time = datetime.strptime(raw_time, '%Y-%m-%d %H:%M')
        
        result = schedule_appointment(
            user_id,
            counselor,
            appt_time
        )
        return jsonify({"message": result})
    except ValueError:
        return jsonify({"message": "Invalid date format. Please use YYYY-MM-DD HH:MM"}), 400
    except Exception:
        app.logger.error('appointment_request_save_failed')
        return jsonify({"message": "Could not save the appointment request"}), 500

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
