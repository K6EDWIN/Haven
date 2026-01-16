from flask import Flask, request, jsonify, render_template_string
import os
import sys
from app_logic import analyze_sentiment, check_in_initial, extract_entities, get_resources, check_in, schedule_appointment
from models import db, Interaction

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

if not turso_url:
    raise ValueError("TURSO_DATABASE_URL environment variable is not set. Database connection is required.")

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
        .bot-msg { color: #c9d1d9; margin: 5px 0; }
        .user-msg { color: #00ff41; margin: 5px 0; font-weight: bold; }
        .system-msg { color: #f0ad4e; font-style: italic; }
        .error-msg { color: #ff6b6b; }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; }
    </style>
</head>
<body>
    <h1>Haven v1.0 [Online]</h1>
    <div id="terminal">
        <div class="system-msg">System initialized...</div>
        <div class="system-msg">Connecting to Haven Core... Connected.</div>
        <br>
        <div class="bot-msg">Welcome to Haven.</div>
        <div class="bot-msg">-------------------------</div>
        <div class="bot-msg">1. Safe Space (Ephemeral Mode)</div>
        <div class="bot-msg">2. Extract Entities (NLP Analysis)</div>
        <div class="bot-msg">3. Check-in (Log to Database)</div>
        <div class="bot-msg">4. View Resources</div>
        <div class="bot-msg">5. Schedule Appointment</div>
        <div class="bot-msg">Type 'menu' to see this list again.</div>
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
        
        // State Management
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
            div.innerText = type === 'user' ? `> ${text}` : text;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function processCommand(text) {
            const cmd = text.trim();

            // Global Exit Command
            if (cmd.toLowerCase() === 'exit' || cmd.toLowerCase() === 'menu') {
                currentMode = 'menu';
                promptText.innerText = 'menu >';
                printToTerminal("Returning to Main Menu...", "system");
                printToTerminal("1. Safe Space | 2. Entities | 3. Check-in | 4. Resources | 5. Appointment", "bot");
                return;
            }

            // --- MENU LOGIC ---
            if (currentMode === 'menu') {
                if (cmd === '1') {
                    currentMode = 'safe_space';
                    promptText.innerText = 'safe-space >';
                    printToTerminal("Entering Safe Space. (No data saved). How are you feeling?", "bot");
                } else if (cmd === '2') {
                    currentMode = 'entities';
                    promptText.innerText = 'nlp-analyzer >';
                    printToTerminal("Enter a sentence to extract entities:", "bot");
                } else if (cmd === '3') {
                    currentMode = 'check_in';
                    promptText.innerText = 'check-in >';
                    printToTerminal("This will be logged. How are you feeling today?", "bot");
                } else if (cmd === '4') {
                    // Fetch resources
                    const res = await fetch('/api/resources');
                    const data = await res.json();
                    printToTerminal("Available Resources (Click to open):", "bot");
                    data.forEach(r => {
                        // Create clickable links
                        const linkDiv = document.createElement('div');
                        linkDiv.innerHTML = `<a href="${r.link}" target="_blank" style="color:#58a6ff">${r.name}</a>`;
                        terminal.appendChild(linkDiv);
                    });
                    printToTerminal("Type 'menu' to return.", "system");
                } else if (cmd === '5') {
                    currentMode = 'appointment';
                    appointmentStep = 1;
                    appointmentData = {};
                    promptText.innerText = 'scheduler >';
                    printToTerminal("Let's book an appointment. Enter your User ID:", "bot");
                } else {
                    printToTerminal("Invalid option. Type 1-5.", "error");
                }
                return;
            }

            // --- SAFE SPACE LOGIC ---
            if (currentMode === 'safe_space') {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text, mode: 'safe_space' })
                });
                const data = await res.json();
                printToTerminal(data.response, 'bot');
            }

            // --- ENTITY LOGIC ---
            else if (currentMode === 'entities') {
                const res = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                printToTerminal(`Found: ${JSON.stringify(data.entities)}`, 'bot');
            }

            // --- CHECK-IN LOGIC ---
            else if (currentMode === 'check_in') {
                 // Ask for User ID first if we want to be strict, but for simplicity we default to 'web-user'
                const res = await fetch('/api/checkin', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: text, user_id: 'web-user' })
                });
                const data = await res.json();
                printToTerminal(data.response, 'bot');
                printToTerminal("[Log Saved]", "system");
            }

            // --- APPOINTMENT LOGIC (Multi-step) ---
            else if (currentMode === 'appointment') {
                if (appointmentStep === 1) {
                    appointmentData.user_id = text;
                    appointmentStep = 2;
                    printToTerminal("Enter Counselor Name:", "bot");
                } else if (appointmentStep === 2) {
                    appointmentData.counselor = text;
                    appointmentStep = 3;
                    printToTerminal("Enter Time (YYYY-MM-DD HH:MM):", "bot");
                } else if (appointmentStep === 3) {
                    appointmentData.time = text;
                    printToTerminal("Scheduling...", "system");
                    
                    const res = await fetch('/api/appointment', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(appointmentData)
                    });
                    const data = await res.json();
                    printToTerminal(data.message, 'bot');
                    
                    // Reset to menu
                    currentMode = 'menu';
                    promptText.innerText = 'menu >';
                    printToTerminal("Returning to menu...", "system");
                }
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

@app.route('/api/chat', methods=['POST'])
def chat_mode():
    data = request.json
    msg = data.get('message', '')
    response = check_in_initial(msg)
    return jsonify({"response": response})

@app.route('/api/extract', methods=['POST'])
def extract_mode():
    data = request.json
    msg = data.get('message', '')
    entities = extract_entities(msg)
    return jsonify({"entities": entities})

@app.route('/api/checkin', methods=['POST'])
def checkin_mode():
    data = request.json
    msg = data.get('message', '')
    user_id = data.get('user_id', 'anonymous')
    response = check_in(user_id, msg) 
    return jsonify({"response": response})

@app.route('/api/appointment', methods=['POST'])
def appointment_mode():
    data = request.json
    try:
        from datetime import datetime
        appt_time = datetime.strptime(data.get('time'), '%Y-%m-%d %H:%M')
        
        result = schedule_appointment(
            data.get('user_id'),
            data.get('counselor'),
            appt_time
        )
        return jsonify({"message": result})
    except ValueError:
        return jsonify({"message": "Error: Invalid date format. Use YYYY-MM-DD HH:MM"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

if __name__ == '__main__':

    app.run(debug=True)