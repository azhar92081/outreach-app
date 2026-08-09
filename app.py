import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Vercel aur Frontend ke connection ke liye CORS enable

DB_PATH = "/tmp/outreach.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_name TEXT,
            subject TEXT,
            total_contacts INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Yahan apna Gmail aur App Password daalo
GMAIL_SENDER = "tumhara.email@gmail.com"  
GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop" 

def send_real_email(contact_email, contact_name, subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_SENDER
        msg['To'] = contact_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "Active", "message": "Flask Backend on Vercel is live!"})

@app.route("/api/campaign/launch", methods=["POST"])
def launch_campaign():
    try:
        data = request.json
        campaign_name = data.get("campaign_name")
        subject = data.get("subject")
        message_body = data.get("message_body")
        contacts = data.get("contacts", [])

        if not contacts:
            return jsonify({"detail": "Contacts list is empty."}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO campaigns (campaign_name, subject, total_contacts, status) VALUES (?, ?, ?, ?)",
            (campaign_name, subject, len(contacts), "Completed")
        )
        conn.commit()
        conn.close()

        # Emails bhejne ka process
        for contact in contacts:
            personalized_message = message_body.replace("{{name}}", contact.get("name", ""))
            send_real_email(contact.get("email"), contact.get("name"), subject, personalized_message)

        return jsonify({
            "status": "success",
            "message": f"Campaign executed successfully for {len(contacts)} contacts."
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/api/campaigns", methods=["GET"])
def get_campaigns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY id DESC")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"campaigns": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)