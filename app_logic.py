try:
    from textblob import TextBlob
except ImportError:
    print("Please install the 'textblob' library.")
try:
    import spacy
except ImportError:
    print("Please install the 'spacy' library.")
import webbrowser
from models import db, Interaction, Resource, Appointment
from datetime import datetime
import time

nlp = spacy.load("en_core_web_sm")

def greet():
    return "Hello! How are you feeling today?"

def analyze_sentiment(user_input):
    blob = TextBlob(user_input)
    sentiment = blob.sentiment.polarity
    return sentiment

def check_in_initial(user_input):
    sentiment = analyze_sentiment(user_input)
    
    if sentiment < -0.5:
        response = "I'm really sorry you're feeling this way. Please reach out to a counselor or call a crisis hotline."
    elif sentiment < 0:
        response = "I'm sorry you're feeling down. Here are some resources that might help."
    elif sentiment == 0:
        response = "Thank you for sharing. How can I assist you today?"
    else:
        response = "I'm glad you're feeling good! How can I assist you today?"
    
    return response

def extract_entities(user_input):
    doc = nlp(user_input)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def check_in(user_id, message):
    sentiment = analyze_sentiment(message)
    
    interaction = Interaction(user_id=user_id, message=message, sentiment=sentiment, timestamp=datetime.utcnow())
    db.session.add(interaction)
    db.session.commit()
    
    if sentiment < -0.5:
        response = "I'm really sorry you're feeling this way. Please reach out to a counselor or call a crisis hotline."
    elif sentiment < 0:
        response = "I'm sorry you're feeling down. Here are some resources that might help."
    elif sentiment == 0:
        response = "Thank you for sharing. How can I assist you today?"
    else:
        response = "I'm glad you're feeling good! How can I assist you today?"
    
    return response

def get_resources():
    resources = [
        {"name": "Stress", "link": "https://www.cdc.gov/mentalhealth/cope-with-stress/index.html"},
        {"name": "Trauma", "link": "https://www.nimh.nih.gov/health/topics/coping-with-traumatic-events"},
        {"name": "Depression", "link": "https://www.nimh.nih.gov/health/publications/depression"},
        {"name": "Anxiety", "link": "https://adaa.org/"},
        {"name": "Grief", "link": "https://www.cdc.gov/mentalhealth/stress-coping/grief-loss/index.html"},
        {"name": "Mental Health", "link": "https://www.mind.org.uk/"}
    ]
    return resources

def open_resource_link(resource_link):
    webbrowser.open(resource_link)

def schedule_appointment(user_id, counselor_name, appointment_time):
    appointment = Appointment(user_id=user_id, counselor_name=counselor_name, appointment_time=appointment_time)
    db.session.add(appointment)
    db.session.commit()
    return "Appointment scheduled successfully!"

def safe_space(user_id):
    print(f"Hello, {user_id}. Let's talk in a safe space.")
    time.sleep(1)
    
    while True:
        user_input = input("How are you feeling? (type 'exit' to leave the session): ")
        
        if user_input.lower() == 'exit':
            print("Thank you for sharing. Remember, you can always return to this safe space.")
            break
        
        sentiment = analyze_sentiment(user_input)
        
        if sentiment < -0.5:
            response = "I'm really sorry you're feeling this way. It might help to talk to a counselor or therapist."
        elif sentiment < 0:
            response = "It sounds like you're going through a tough time. I'm here to listen."
        elif sentiment == 0:
            response = "Thank you for sharing. I'm here if you need to talk more."
        else:
            response = "It's great to hear you're feeling positive! How can I support you further?"
        
        time.sleep(1)