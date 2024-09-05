import app_logic
import cli

def main():
    """Main entry point of the application."""
    print(app_logic.greet())
    user_input = input("Enter how you're feeling 🙂: ")
    response = app_logic.check_in_initial(user_input)
    print(response)
    
    while True:
        choice = cli.menu()
        if not cli.handle_choice(choice):
            break

if __name__ == "__main__":
    main()
