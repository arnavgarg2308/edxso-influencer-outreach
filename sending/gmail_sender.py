import os
import sys
import base64
import pandas as pd
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import initialize_db, save_generated, get_outreach, mark_sent, mark_failed

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
CSV_FILE = os.path.join(BASE_DIR, "final_enriched_influencers.csv")

DRY_RUN = True

creds = None

if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES
    )

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())

service = build(
    "gmail",
    "v1",
    credentials=creds
)

initialize_db()

df = pd.read_csv(CSV_FILE)

def create_message(to_email, subject, body):
    message = MIMEText(
        body,
        "plain",
        "utf-8"
    )

    message["to"] = to_email
    message["subject"] = subject

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    return {
        "raw": encoded_message
    }

def send_email(to_email, subject, body):
    message = create_message(
        to_email,
        subject,
        body
    )

    return service.users().messages().send(
        userId="me",
        body=message
    ).execute()

def process_creator(row):
    email = str(
        row.get("contact_email", "")
    ).strip()

    if not email or email.lower() == "not found":
        print(
            f"Skipped: {row['name']} - email not found"
        )
        return

    existing = get_outreach(email)

    if existing:
        status = existing[9]

        if status == "Sent":
            print(
                f"Already contacted: {email}"
            )
            return

        print(
            f"Existing record: {email} - {status}"
        )
        return

    subject = "Potential AI Collaboration with EDXSO"

    data = {
        "channel_id": row["channel_id"],
        "name": row["name"],
        "email": email,
        "platform": "YouTube",
        "profile_url": row.get(
            "profile_url",
            ""
        ),
        "subject": subject,
        "email_body": row["personalized_email"],
        "dm_body": row["personalized_dm"]
    }

    save_generated(data)

    if DRY_RUN:
        print()
        print("DRY RUN")
        print("Creator:", row["name"])
        print("Email:", email)
        print("Subject:", subject)
        print("Body:")
        print(row["personalized_email"])
        print("-" * 70)
        return

    try:
        result = send_email(
            email,
            subject,
            row["personalized_email"]
        )

        message_id = result.get(
            "id",
            ""
        )

        mark_sent(
            email,
            message_id
        )

        print(
            f"Sent: {row['name']} -> {email}"
        )

    except Exception as e:
        mark_failed(
            email,
            e
        )

        print(
            f"Failed: {row['name']} -> {email}"
        )

        print(str(e))

print()
print("EDXSO AI Influencer Outreach")
print("DRY RUN:", DRY_RUN)
print("Creators loaded:", len(df))
print()

for _, row in df.iterrows():
    process_creator(row)

print()
print("Outreach processing completed")