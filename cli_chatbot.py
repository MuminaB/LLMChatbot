import time
import sys
from chatbot import get_chatbot_response
from colorama import init, Fore, Style

# Initialize colorama for Windows terminal compatibility
init(autoreset=True)

# Optional: keep a simple in-memory chat log for session
chat_log = []

def type_effect(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def main():
    print(Fore.CYAN + Style.BRIGHT + "\n🎓 Welcome to the RMU Chatbot CLI 🎓")
    print(Fore.YELLOW + "Type 'exit' to quit. Type 'history' to show the current session.\n")

    while True:
        user_input = input(Fore.GREEN + "You: " + Style.RESET_ALL)
        if user_input.lower() in ['exit', 'quit']:
            print(Fore.CYAN + "Exiting chatbot. Goodbye!")
            break
        elif user_input.lower() == 'history':
            print(Fore.MAGENTA + "\n🕘 Chat History:")
            for pair in chat_log:
                print(Fore.GREEN + "You: " + pair['user'])
                print(Fore.BLUE + "Bot: " + pair['bot'] + "\n")
            continue

        print(Fore.BLUE + "Bot: ", end="")
        bot_reply = get_chatbot_response(user_input)
        type_effect(bot_reply, delay=0.02)

        # Save to history log
        chat_log.append({
            "user": user_input,
            "bot": bot_reply
        })

if __name__ == "__main__":
    main()
