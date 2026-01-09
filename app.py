from flask import Flask, request, jsonify, render_template_string
import os
from app_logic import analyze_sentiment, extract_entities, get_resources
from models import db, Interaction

app = Flask(__name__)

db_user = os.getenv('DB_USER', 'root')
db_pass = os.getenv('DB_PASS', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'rosa')

if db_host != 'localhost':
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Fallback for local testing

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Haven | Safe Space</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .chat-box { height: 400px; overflow-y: scroll; border: 1px solid #ddd; background: white; padding: 10px; margin-bottom: 10px; border-radius: 8px; }
        .message { margin: 10px 0; padding: 8px; border-radius: 5px; }
        .user { background: #e3f2fd; text-align: right; margin-left: 20%; }
        .bot { background: #f1f0f0; text-align: left; margin-right: 20%; }
        input { width: 75%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 15px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #218838; }
    </style>
</head>
<body>
    <h1>Haven 🌿</h1>
    <p>Safe Space Mode (Powered by spaCy)</p>
    <div class="chat-box" id="chat-box">
        <div class="message bot">Hello! I am Haven. I'm here to listen. How are you feeling today?</div>
    </div>
    <div>
        <input type="text" id="user-input" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        async function sendMessage() {
            const inputField = document.getElementById('user-input');
            const message = inputField.value;
            if (!message) return;

            addMessage(message, 'user');
            inputField.value = '';

            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            
            // Show entities if found (Debugging/Feature)
            let botText = data.response;
            if (data.entities && data.entities.length > 0) {
                const entityNames = data.entities.map(e => e[0]).join(", ");
                botText += ` (I noticed these topics: ${entityNames})`;
            }
            
            addMessage(botText, 'bot');
        }

        function addMessage(text, sender) {
            const chatBox = document.getElementById('chat-box');
            const div = document.createElement('div');
            div.className = 'message ' + sender;
            div.innerText = text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter') sendMessage();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Analyze Sentiment
    sentiment = analyze_sentiment(user_message)
    entities = extract_entities(user_message)
    if sentiment < -0.5:
        bot_response = "I'm really sorry you're feeling this way. It might help to talk to a professional."
    elif sentiment < 0:
        bot_response = "It sounds like you're going through a tough time. I'm here to listen."
    elif sentiment == 0:
        bot_response = "I hear you. Thank you for sharing."
    else:
        bot_response = "It's great to hear you're feeling positive! How can I support you further?"

    return jsonify({"response": bot_response, "sentiment": sentiment, "entities": entities})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)