import os
import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- 1. SETUP GOOGLE SHEETS ---
# Render puts secret files in /etc/secrets/
# On your laptop, just put the file in the same folder
CREDENTIALS_FILE = '/etc/secrets/google-credentials.json'

# If running locally on laptop, look in the current folder
if not os.path.exists(CREDENTIALS_FILE):
    CREDENTIALS_FILE = 'google-credentials.json'

try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    # Open the sheet (Make sure you shared it with the robot email!)
    sheet = client.open("NSM Leads").sheet1
    print("SUCCESS: Connected to Google Sheets!")
except Exception as e:
    print(f"WARNING: Could not connect to Sheets. Leads won't be saved. Error: {e}")
    sheet = None

# --- 2. SETUP GEMINI AI ---
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    # Clean the key just in case
    GOOGLE_API_KEY = GOOGLE_API_KEY.strip().replace('"', '').replace("'", "")
    genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 3. THE SMART PERSONA ---
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

LEAD QUALIFICATION FLOW:
1. Project Type? (Residential / Commercial)
2. Location?
3. New Build or Renovation?
4. Timeline?
5. Budget?
6. Name & Email?

*** CRITICAL INSTRUCTION ***
When you have collected ALL the details (Type, Location, Build/Reno, Timeline, Budget, Name), you must output a "Secret Code" at the end of your message so our system can save it.
Format: SAVE_LEAD|Name|Phone|Type|Budget|Notes
Example: "Thank you John. We will be in touch. SAVE_LEAD|John Smith|Unknown|Residential|R2m|Wants a modern kitchen"
"""

conversation_history = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender_phone = request.values.get('From', '')

    print(f"Message from {sender_phone}: {incoming_msg}")

    # Initialize chat history if new user
    if sender_phone not in conversation_history:
        conversation_history[sender_phone] = model.start_chat(history=[
            {"role": "user", "parts": SYSTEM_PROMPT},
            {"role": "model", "parts": "Understood. I am ready."}
        ])
    
    chat_session = conversation_history[sender_phone]

    try:
        # Send message to AI
        response = chat_session.send_message(incoming_msg)
        bot_reply = response.text
        
        # --- 4. CHECK FOR THE SECRET CODE ---
        if "SAVE_LEAD|" in bot_reply:
            print("LEAD DETECTED! Saving to sheet...")
            try:
                # Extract the data
                parts = bot_reply.split("SAVE_LEAD|")[1].split("|")
                # Clean up the reply so the user doesn't see the ugly code
                bot_reply = bot_reply.split("SAVE_LEAD|")[0].strip()
                
                # Prepare row: [Date, Name, Phone, Type, Budget, Notes]
                # We use sender_phone for the phone number field
                if sheet:
                    row = [
                        str(datetime.date.today()), # Date
                        parts[0], # Name
                        sender_phone, # Phone (from WhatsApp)
                        parts[2] if len(parts) > 2 else "", # Type
                        parts[3] if len(parts) > 3 else "", # Budget
                        parts[4] if len(parts) > 4 else ""  # Notes
                    ]
                    sheet.append_row(row)
                    print("SAVED TO GOOGLE SHEET!")
            except Exception as e:
                print(f"Error saving to sheet: {e}")

    except Exception as e:
        print(f"Error talking to Google: {e}")
        bot_reply = "I apologize, I am currently connecting to our architectural database. Please try again in a moment."

    # Send response back to Twilio
    resp = MessagingResponse()
    resp.message(bot_reply)

    return str(resp)

if __name__ == '__main__':
    app.run(port=5000, debug=True)