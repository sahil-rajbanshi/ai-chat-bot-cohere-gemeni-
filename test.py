import tkinter as tk
from tkinter import scrolledtext, Listbox, END, messagebox
import cohere
import os
import pymongo
from dotenv import load_dotenv
import google.generativeai as genai
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Load API keys
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Configure Cohere
cohere_client = cohere.Client(COHERE_API_KEY)

# Configure Gemini API Key
genai.configure(api_key=GEMINI_API_KEY)

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["chatbot_db"]
collection = db["conversations"]

# Track the current conversation ID
current_conversation_id = None

# Fetch response from Cohere API
def get_cohere_response(prompt):
    try:
        response = cohere_client.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=1000
        )
        return response.generations[0].text.strip()
    except Exception as e:
        return f"Error: {e}"

# Fetch response from Gemini API
def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# Save chat to MongoDB
def save_to_db(user_input, cohere_response, gemini_response, conversation_id=None):
    if conversation_id:
        collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$push": {"messages": {
                "user_input": user_input,
                "cohere_response": cohere_response,
                "gemini_response": gemini_response
            }}}
        )
    else:
        result = collection.insert_one({
            "messages": [{
                "user_input": user_input,
                "cohere_response": cohere_response,
                "gemini_response": gemini_response
            }]
        })
        return str(result.inserted_id)

# Load chat history from MongoDB
def load_chat_history():
    return list(collection.find())

# Load chat into the main display
def load_chat(chat_data):
    global current_conversation_id
    chat_display.delete(1.0, tk.END)
    current_conversation_id = str(chat_data["_id"])

    for message in chat_data["messages"]:
        chat_display.insert(tk.END, f"You: {message['user_input']}\n", "user")
        chat_display.insert(tk.END, f"Cohere: {message['cohere_response']}\n", "chatgpt")
        chat_display.insert(tk.END, f"Gemini: {message['gemini_response']}\n", "gemini")

# Refresh chat history in the sidebar
def refresh_chat_history():
    chat_history_listbox.delete(0, END)
    for chat in load_chat_history():
        messages = chat.get('messages')
        if messages and len(messages) > 0:
            chat_history_listbox.insert(END, messages[0]['user_input'])
        else:
            chat_history_listbox.insert(END, "[No messages in chat]")

# Handle sending messages
def send_message():
    global current_conversation_id
    user_input = input_field.get()
    if not user_input.strip():
        return

    chat_display.insert(tk.END, f"You: {user_input}\n", "user")
    input_field.delete(0, tk.END)

    # Initialize interaction
    current_input = user_input
    interaction_limit = 1  # Limit to 1 interactions

    for i in range(interaction_limit):
        cohere_response = get_cohere_response(current_input)
        chat_display.insert(tk.END, f"Cohere: {cohere_response}\n", "chatgpt")

        gemini_response = get_gemini_response(cohere_response)
        chat_display.insert(tk.END, f"Gemini: {gemini_response}\n", "gemini")

        current_input = gemini_response

    # Save to MongoDB
    if current_conversation_id:
        save_to_db(user_input, cohere_response, gemini_response, conversation_id=current_conversation_id)
    else:
        current_conversation_id = save_to_db(user_input, cohere_response, gemini_response)

    refresh_chat_history()

# Handle chat history selection
def on_chat_history_select(event):
    selected_index = chat_history_listbox.curselection()
    if not selected_index:
        return

    selected_chat = load_chat_history()[selected_index[0]]
    load_chat(selected_chat)

# Start a new chat
def start_new_chat():
    global current_conversation_id
    current_conversation_id = None
    chat_display.delete(1.0, tk.END)
    input_field.delete(0, tk.END)
    refresh_chat_history()

# GUI setup
root = tk.Tk()
root.title("AI Chatbot with Interaction")
root.geometry("800x600")
root.configure(bg="#2D2D2D")

# Sidebar
sidebar = tk.Frame(root, bg="#3C3F41", width=200)
sidebar.pack(side=tk.LEFT, fill=tk.Y)

chat_history_listbox = Listbox(sidebar, bg="#3C3F41", fg="#EAEAEA", selectbackground="#007ACC", height=30)
chat_history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
chat_history_listbox.bind("<<ListboxSelect>>", on_chat_history_select)

new_chat_button = tk.Button(sidebar, text="New Chat", command=start_new_chat, bg="#007ACC", fg="white")
new_chat_button.pack(fill=tk.X, padx=5, pady=5)

# Main chat display
main_frame = tk.Frame(root, bg="#2D2D2D")
main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

chat_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=20, width=50, state="normal", bg="#1E1E1E", fg="#EAEAEA", insertbackground="white")
chat_display.tag_config("user", foreground="#EAEAEA")
chat_display.tag_config("chatgpt", foreground="#85E085")
chat_display.tag_config("gemini", foreground="#BDB76B")
chat_display.pack(pady=10, padx=10)

input_frame = tk.Frame(main_frame, bg="#2D2D2D")
input_frame.pack(fill=tk.X, padx=10)

input_field = tk.Entry(input_frame, font=("Arial", 14), bg="#1E1E1E", fg="#EAEAEA", insertbackground="white")
input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

send_button = tk.Button(input_frame, text="Send", command=send_message, bg="#007ACC", fg="white")
send_button.pack(side=tk.RIGHT, padx=5)

refresh_chat_history()
root.mainloop()
