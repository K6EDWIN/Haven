from datetime import datetime
import time
from textblob import TextBlob
import spacy
import webbrowser
import random  # Added for varied responses
from models import db, Interaction, Log, Appointment 

nlp = spacy.load("en_core_web_sm")

def greet():
    return "Hello! How are you feeling today?"

def analyze_sentiment(user_input):
    blob = TextBlob(user_input)
    sentiment = blob.sentiment.polarity
    return sentiment

# --- NEW: Reusable Safe Space Logic ---
def get_safe_space_response(user_input):
    """
    Returns a supportive response based on sentiment without saving data.
    Used by both Web and CLI Safe Space modes.
    """
    sentiment = analyze_sentiment(user_input)
    
    if sentiment < -0.5:
        return random.choice([
            "I'm really sorry you're feeling this way. It might help to talk to a counselor or therapist.",
            "That sounds incredibly heavy. Please remember you don't have to carry this alone.",
            "I hear how much pain you're in. Reaching out to a crisis line might provide immediate support."
        ])
    elif sentiment < 0:
        return random.choice([
            "It sounds like you're going through a tough time. I'm here to listen.",
            "I'm sorry things are difficult right now. Want to tell me more?",
            "That sounds challenging. I'm here for you."
        ])
    elif sentiment == 0:
        return random.choice([
            "Thank you for sharing. I'm here if you need to talk more.",
            "I'm listening. Feel free to say whatever is on your mind.",
            "I understand. Go on."
        ])
    else:
        return random.choice([
            "It's great to hear you're feeling positive! How can I support you further?",
            "That sounds wonderful. I'm glad things are looking up.",
            "Thanks for sharing that joy with me!"
        ])

# --- OLD: Updated to use the new reusable logic ---
def safe_space(user_id):
    print(f"Hello, {user_id}. Let's talk in a safe space.")
    print("NOTE: Nothing you say here is saved to the database. This is just between us.")
    time.sleep(1)
    
    while True:
        user_input = input("How are you feeling? (type 'exit' to leave the session): ")
        
        if user_input.lower() == 'exit':
            print("Thank you for sharing. Remember, you can always return to this safe space.")
            break
        
        # Use the shared logic function
        response = get_safe_space_response(user_input)
        print(response)
        time.sleep(1)

def check_in_initial(user_input):
    # This remains for the main menu initial check-in
    sentiment = analyze_sentiment(user_input)
    if sentiment < -0.5:
        return "I'm really sorry you're feeling this way. Please reach out to a counselor or call a crisis hotline."
    elif sentiment < 0:
        return "I'm sorry you're feeling down. Here are some resources that might help."
    elif sentiment == 0:
        return "Thank you for sharing. How can I assist you today?"
    else:
        return "I'm glad you're feeling good! How can I assist you today?"

def extract_entities(user_input):
    doc = nlp(user_input)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def check_in(user_id, message):
    sentiment = analyze_sentiment(message)
    response = get_safe_space_response(message) 

    interaction = Interaction(
        user_id=user_id,
        user_input=message,
        ai_response=response,
        sentiment=sentiment,
        timestamp=datetime.utcnow()
    )
    db.session.add(interaction)
    db.session.commit()

    log_event(user_id, f"User interaction saved. Sentiment: {sentiment}")
    return response

def log_event(user_id, event, log_level='INFO'):
    log = Log(user_id=user_id, event=event, log_level=log_level, timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.commit()

def get_resources():
    return [
        {"name": "Stress", "link": "https://www.cdc.gov/mentalhealth/cope-with-stress/index.html"},
        {"name": "Trauma", "link": "https://www.nimh.nih.gov/health/topics/coping-with-traumatic-events"},
        {"name": "Depression", "link": "https://www.nimh.nih.gov/health/publications/depression"},
        {"name": "Anxiety", "link": "https://adaa.org/"},
        {"name": "Grief", "link": "https://www.cdc.gov/mentalhealth/stress-coping/grief-loss/index.html"},
        {"name": "Mental Health", "link": "https://www.mind.org.uk/"}
    ]

def open_resource_link(resource_link):
    webbrowser.open(resource_link)

def schedule_appointment(user_id, counselor_name, appointment_time):
    appointment = Appointment(user_id=user_id, counselor_name=counselor_name, appointment_time=appointment_time)
    db.session.add(appointment)
    db.session.commit()
    log_event(user_id, f"Appointment scheduled with {counselor_name} at {appointment_time}")
    return "Appointment scheduled successfully!"