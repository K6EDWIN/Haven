from datetime import datetime
import time
from textblob import TextBlob
import spacy
import webbrowser
import random
from models import db, Interaction, Log, Appointment 

nlp = spacy.load("en_core_web_sm")

def greet():
    return "Hello! How are you feeling today?"

def analyze_sentiment(user_input):
    blob = TextBlob(user_input)
    sentiment = blob.sentiment.polarity
    return sentiment

def get_safe_space_response(user_input):
    """
    Returns a supportive, conversational response based on sentiment AND keywords.
    """
    text = user_input.lower()
    sentiment = analyze_sentiment(user_input)
    
    # --- Keyword Specific Logic ---
    if "work" in text or "job" in text or "boss" in text:
        return "Work can be a huge source of stress. Is it the workload, or something specific happening there?"
    
    if "tired" in text or "exhausted" in text or "sleep" in text:
        return "Physical exhaustion often comes with mental load. Have you been able to get any rest lately?"
        
    if "anxious" in text or "anxiety" in text or "panic" in text:
        return "Anxiety is really tough. Sometimes grounding helps—can you tell me 5 things you see around you right now?"

    if "lonely" in text or "alone" in text:
        return "Loneliness is a heavy feeling. I'm here with you right now. Do you have anyone close you can text?"

    if sentiment < -0.5:
        return random.choice([
            "I'm really sorry you're feeling this way. It sounds like a lot to carry. What's weighing on you the most?",
            "That sounds incredibly heavy. I'm listening—let it all out."
        ])
    elif sentiment < 0:
        return random.choice([
            "It sounds like a rough moment. Do you want to vent about it?",
            "I'm sorry things are difficult. What happened today that made you feel this way?"
        ])
    elif sentiment == 0:
        return random.choice([
            "I'm listening. Tell me more.",
            "I'm here. What else is on your mind?"
        ])
    else:
        return random.choice([
            "It's great to hear some positivity! What's the best part of your day so far?",
            "I'm glad to hear that. What's keeping your spirits up?"
        ])

def extract_entities_conversational(user_input):
    """
    Extracts entities but returns a conversational sentence.
    """
    doc = nlp(user_input)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    if not entities:
        return "I didn't catch any specific names or places there. Could you be more specific?"
    
    response = "I noticed you mentioned: " + ", ".join([f"{e[0]}" for e in entities]) + ". "
    response += "How do these play a role in how you're feeling?"
    return response

def check_in(user_id, message):
    sentiment = analyze_sentiment(message)

    response_text = get_safe_space_response(message)
    
    final_response = f"{response_text} (I've logged this entry for you)."

    interaction = Interaction(
        user_id=user_id,
        user_input=message,
        ai_response=final_response,
        sentiment=sentiment,
        timestamp=datetime.utcnow()
    )
    db.session.add(interaction)
    db.session.commit()

    log_event(user_id, f"User interaction saved. Sentiment: {sentiment}")
    return final_response


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

def schedule_appointment(user_id, counselor_name, appointment_time):
    appointment = Appointment(user_id=user_id, counselor_name=counselor_name, appointment_time=appointment_time)
    db.session.add(appointment)
    db.session.commit()
    log_event(user_id, f"Appointment scheduled with {counselor_name} at {appointment_time}")
    return f"Done. You are booked with {counselor_name} for {appointment_time}. I've sent a request to their calendar."

def extract_entities(user_input):
    doc = nlp(user_input)
    return [(ent.text, ent.label_) for ent in doc.ents]

def check_in_initial(user_input):
    return get_safe_space_response(user_input)