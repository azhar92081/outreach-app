import uvicorn
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional

# ==========================================
# 1. Database Setup
# ==========================================
def init_db():
    conn = sqlite3.connect("outreach.db")
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

# Start karte hi DB initialize ho jayegi
init_db()

# ==========================================
# 2. App Initialization & Setup
# ==========================================
app = FastAPI(title="Outreach Tool API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Deployment ke waqt isko Vercel ke URL se replace kar denge
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. Email Credentials (YAHAN APNI DETAILS DAALO)
# ==========================================
GMAIL_SENDER = "tumhara.email@gmail.com"  
GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop" 

# ==========================================
# 4. Data Models
# ==========================================
class Contact(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None

class CampaignPayload(BaseModel):
    campaign_name: str
    subject: str
    message_body: str
    contacts: List[Contact]

# ==========================================
# 5. Core Logic
# ==========================================
def send_real_email(contact: Contact, subject: str, message: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_SENDER
        msg['To'] = contact.email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() 
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[❌ ERROR] {contact.email}: {e}")
        return False

def process_outreach_campaign(campaign_id: int, campaign: CampaignPayload):
    print(f"--- Processing Campaign ID: {campaign_id} ---")
    
    for contact in campaign.contacts:
        personalized_message = campaign.message_body.replace("{{name}}", contact.name)
        send_real_email(contact, campaign.subject, personalized_message)
            
    # Jab emails chali jayen toh DB mein status 'Completed' kar do
    conn = sqlite3.connect("outreach.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE campaigns SET status = 'Completed' WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()
    print(f"--- Campaign ID {campaign_id} Completed! ---")

# ==========================================
# 6. API Endpoints
# ==========================================
@app.get("/", tags=["System"])
async def root():
    return {"status": "Active", "message": "Backend with DB is live!"}

@app.post("/api/campaign/launch", tags=["Outreach"])
async def launch_campaign(payload: CampaignPayload, background_tasks: BackgroundTasks):
    try:
        if not payload.contacts:
            raise HTTPException(status_code=400, detail="Contacts list is empty.")

        # Database mein naya campaign 'Processing' status ke sath save karo
        conn = sqlite3.connect("outreach.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO campaigns (campaign_name, subject, total_contacts, status) VALUES (?, ?, ?, ?)",
            (payload.campaign_name, payload.subject, len(payload.contacts), "Processing...")
        )
        campaign_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Background task run karo
        background_tasks.add_task(process_outreach_campaign, campaign_id, payload)

        return {
            "status": "success",
            "message": f"Campaign saved to DB and queued for {len(payload.contacts)} contacts.",
            "campaign_id": campaign_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns", tags=["Outreach"])
async def get_campaigns():
    # Frontend par dashboard dikhane ke liye endpoint
    conn = sqlite3.connect("outreach.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY id DESC")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"campaigns": results}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)