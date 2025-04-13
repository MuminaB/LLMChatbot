import time
import sys
from chatbot import get_chatbot_response
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def type_effect(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()  # Move to next line

def main():
    print(Fore.CYAN + Style.BRIGHT + "\n🎓 Welcome to the RMU Chatbot CLI 🎓")
    print(Fore.YELLOW + "Type 'exit' to quit.\n")

    while True:
        user_input = input(Fore.GREEN + "You: " + Style.RESET_ALL)
        if user_input.lower() in ['exit', 'quit']:
            print(Fore.CYAN + "Exiting chatbot. Goodbye!")
            break

        print(Fore.BLUE + "Bot: ", end="")
        bot_reply = get_chatbot_response(user_input)
        type_effect(bot_reply, delay=0.02)
        print("\n")

if __name__ == "__main__":
    main()
