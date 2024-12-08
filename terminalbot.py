import os
import sqlite3
import markdown
from bs4 import BeautifulSoup
import html
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI

# Load environment variables
load_dotenv()

# Load API keys
XAI_API_KEY = os.getenv("XAI_API_KEY")  # Grok API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Grok AI
grok_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Database setup
DB_FILE = "chatbot.sqlite"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Create tables for conversations
cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT,
    grok_response TEXT,
    gemini_response TEXT
)
""")
conn.commit()

# Utility function to save chat to SQLite
def save_to_db(user_input, grok_response, gemini_response):
    cursor.execute(
        """
        INSERT INTO conversations (user_input, grok_response, gemini_response)
        VALUES (?, ?, ?)
        """,
        (user_input, grok_response, gemini_response)
    )
    conn.commit()

# Utility function to load chat history
def load_chat_history():
    cursor.execute("SELECT * FROM conversations")
    return cursor.fetchall()

# Format text with Markdown and HTML cleanup
def format_text(text):
    try:
        html_text = markdown.markdown(text)
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator="\n")
    except Exception as e:
        return f"Error formatting text: {e}"

# Fetch response from Grok AI
def get_grok_response(prompt):
    try:
        completion = grok_client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are Grok, a chatbot inspired by the Hitchhiker's Guide to the Galaxy."},
                {"role": "user", "content": prompt},
            ],
        )
        return format_text(completion.choices[0].message.content.strip())
    except Exception as e:
        return f"Error: {e}"

# Fetch response from Gemini AI
def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return format_text(response.text)
    except Exception as e:
        return f"Error: {e}"

# Chat interface
def chat():
    print("Welcome to the AI Chatbot! Type 'exit' to end the conversation or 'history' to view chat history.")
    current_context = []

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        if user_input.lower() == "history":
            history = load_chat_history()
            if not history:
                print("No chat history available.")
            else:
                for chat in history:
                    print(f"User: {chat[1]}")
                    print(f"Grok: {chat[2]}")
                    print(f"Gemini: {chat[3]}")
            continue

        # Include prior conversation context
        context_prompt = "\n".join(current_context) + f"\nUser: {user_input}"

        # Start AI-to-AI interaction loop
        current_input = user_input
        interaction_limit = 3  # Number of exchanges between Grok and Gemini

        for i in range(interaction_limit):
            # Get response from Grok AI
            grok_response = get_grok_response(current_input)
            print(f"Grok (Iteration {i+1}):\n{grok_response}")

            # Get response from Gemini AI
            gemini_response = get_gemini_response(grok_response)
            print(f"Gemini (Iteration {i+1}):\n{gemini_response}")

            # Update context for the next iteration
            current_context.append(f"Grok: {grok_response}")
            current_context.append(f"Gemini: {gemini_response}")

            # Update current input for the loop
            current_input = gemini_response

        # Save the user's input and both AI responses to the database
        save_to_db(user_input, grok_response, gemini_response)

# Start the chatbot
if __name__ == "__main__":
    chat()
