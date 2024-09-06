import app_logic
import webbrowser
from datetime import datetime

def menu():
    """Display menu options and get user choice."""
    print("\nMain Menu")
    print("1. Safe Space ")
    print("2. Extract Entities")
    print("3. Check-in")
    print("4. View Resources")
    print("5. Schedule Appointment")
    print("6. Exit")
    
    choice = input("Enter your choice: ")
    return choice

def handle_choice(choice, app):
    """Handle user's choice and call the appropriate function."""
    if choice == '1':
        user_id = input("Enter your user ID (default 'anonymous'): ") or "anonymous"
        app_logic.safe_space(user_id)

    elif choice == '2':
        user_input = input("Enter a sentence: ")
        entities = app_logic.extract_entities(user_input)
        print(f"Entities: {entities}")

    elif choice == '3':
        user_id = input("Enter your user ID (default 'anonymous'): ") or "anonymous"
        message = input("Enter your message: ")

        with app.app_context():
            response = app_logic.check_in(user_id, message)
        print(response)

    elif choice == '4':
        select_resource()

    elif choice == '5':
        user_id = input("Enter your user ID (default 'anonymous'): ") or "anonymous"
        counselor_name = input("Enter the counselor's name: ")
        appointment_time_str = input("Enter the appointment time (YYYY-MM-DD HH:MM): ")
        appointment_time = datetime.strptime(appointment_time_str, '%Y-%m-%d %H:%M')

        with app.app_context():
            result = app_logic.schedule_appointment(user_id, counselor_name, appointment_time)
        print(result)

    elif choice == '6':
        print("Exiting...")
        return False

    else:
        print("Invalid choice, please try again.")

    return True

def select_resource():
    """Allow the user to choose a resource to view."""
    resources = app_logic.get_resources()

    print("\nWhat resource would you like to view?")
    for index, res in enumerate(resources, start=1):
        print(f"{index}. {res['name']}")

    print(f"{len(resources) + 1}. Back")

    choice = input("Enter the number of the resource you want to view: ")
    if choice.isdigit():
        choice = int(choice)
        if 1 <= choice <= len(resources):
            selected_resource = resources[choice - 1]
            print(f"Opening {selected_resource['name']} resource in your browser (please wait🙂)...")
            webbrowser.open(selected_resource['link'])
        elif choice == len(resources) + 1:
            print("Going back to the main menu...")
        else:
            print("Invalid selection, going back to the main menu.")
    else:
        print("Invalid input, going back to the main menu.")
