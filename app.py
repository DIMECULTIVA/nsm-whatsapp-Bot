import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    print("CRITICAL ERROR: Google API Key is missing from Environment Variables!")
else:
    # Clean the key in case there are accidental spaces
    GOOGLE_API_KEY = GOOGLE_API_KEY.strip().replace('"', '').replace("'", "")
    genai.configure(api_key=GOOGLE_API_KEY)

# --- DEBUGGING: PRINT AVAILABLE MODELS ---
# This will show up in your Render Logs so we know what works
try:
    print("--- CHECKING AVAILABLE MODELS ---")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Found model: {m.name}")
    print("--- END MODEL CHECK ---")
except Exception as e:
    print(f"Error checking models: {e}")

# Use the most standard model name
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """
You are NSM ARCHITECTS’ official WhatsApp AI Assistant. 
Your goal is to professionally engage with clients.

RULES:
1. Keep replies concise (max 3 short paragraphs).
2. ASK ONE QUESTION AT A TIME.
"""

conversation_history = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender_phone = request.values.get('From', '')

    print(f"Message from {sender_phone}: {incoming_msg}")

    if sender_phone not in conversation_history:
        conversation_history[sender_phone] = model.start_chat(history=[
            {"role": "user", "parts": SYSTEM_PROMPT},
            {"role": "model", "parts": "Understood. I am NSM Architects."}
        ])
    
    chat_session = conversation_history[sender_phone]

    try:
        response = chat_session.send_message(incoming_msg)
        bot_reply = response.text
    except Exception as e:
        print(f"CRITICAL ERROR talking to Google: {e}")
        bot_reply = "I apologize, I am currently connecting to our architectural database. Please try again in a moment."

    resp = MessagingResponse()
    resp.message(bot_reply)
    return str(resp)

if __name__ == '__main__':
    app.run(port=5000, debug=True)