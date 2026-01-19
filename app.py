from flask import Flask, request, jsonify, render_template_string
import os
import sys
from app_logic import (
    analyze_sentiment, 
    check_in_initial, 
    extract_entities_conversational, 
    get_resources, 
    check_in, 
    schedule_appointment,
    get_safe_space_response
)
from models import db, Interaction

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

if not turso_url:
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

@app.route('/api/chat', methods=['POST'])
def chat_mode():
    data = request.json
    msg = data.get('message', '')
    response = get_safe_space_response(msg)
    return jsonify({"response": response})

@app.route('/api/extract', methods=['POST'])
def extract_mode():
    data = request.json
    msg = data.get('message', '')
    entities = extract_entities_conversational(msg)
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
        return jsonify({"message": "Invalid date format. Please use YYYY-MM-DD HH:MM"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)