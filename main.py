from flask import Flask
import os
import app_logic
import cli
from models import db

app = Flask(__name__)

db_user = os.getenv('DB_USER', 'Rosa')
db_pass = os.getenv('DB_PASS', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'rosa')

if db_pass:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}@{db_host}/{db_name}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)

with app.app_context():
    try:
        db.create_all() 
        print("Database connection successful.")
    except Exception as e:
        print(f"Error connecting to the database: {e}")

def main():
    """Main entry point of the application."""
    with app.app_context():
        print(app_logic.greet())  
        user_input = input("Enter how you're feeling 🙂: ")
        response = app_logic.check_in_initial(user_input)
        print(response)
        
    
        try:
            while True:
                choice = cli.menu()
                with app.app_context():
                    if not cli.handle_choice(choice, app):  
                        break
        except KeyboardInterrupt:
            print("\nExiting the application...")

if __name__ == "__main__":
    main()
