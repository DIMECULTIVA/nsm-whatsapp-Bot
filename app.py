import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Model
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# THE BRAIN: NSM Architects Persona
SYSTEM_PROMPT = """
You are NSM ARCHITECTS’ official WhatsApp AI Assistant. 
Your goal is to professionally engage with clients, qualify leads, and guide them to book a consultation.

COMPANY CONTEXT:
- Name: NSM ARCHITECTS
- Location: South Africa
- Services: Residential (New builds, renovations), Commercial, Council Submissions.
- Contact: 076 308 8254 | info@nsmarch.co.za

RULES:
1. NEVER give specific construction prices.
2. ASK ONE QUESTION AT A TIME.
3. Keep replies concise (max 3 short paragraphs).
4. If a user asks for structural/legal advice, escalate to human.

LEAD QUALIFICATION FLOW:
1. Project Type? (Residential / Commercial)
2. Location?
3. New Build or Renovation?
4. Timeline?
5. Budget?

If qualified, ask for Name and Email.
"""

# Simple memory storage
conversation_history = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender_phone = request.values.get('From', '')

    print(f"Message from {sender_phone}: {incoming_msg}")

    # Initialize chat history if new user
    if sender_phone not in conversation_history:
        # Gemini handles history differently, so we start a new chat session object
        conversation_history[sender_phone] = model.start_chat(history=[
            {"role": "user", "parts": SYSTEM_PROMPT},
            {"role": "model", "parts": "Understood. I am ready to act as NSM Architects."}
        ])
    
    chat_session = conversation_history[sender_phone]

    try:
        # Send message to Google Gemini
        response = chat_session.send_message(incoming_msg)
        bot_reply = response.text
        
    except Exception as e:
        print(f"Error: {e}")
        bot_reply = "I apologize, I am currently connecting to our architectural database. Please try again in a moment."

    # Send response back to Twilio
    resp = MessagingResponse()
    resp.message(bot_reply)

    return str(resp)

if __name__ == '__main__':
    print("NSM ARCHITECTS (GOOGLE POWERED) IS STARTING...")
    app.run(port=5000, debug=True)