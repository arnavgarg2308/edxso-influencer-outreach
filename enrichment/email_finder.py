import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(BASE_DIR, "personalized_influencers.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "final_enriched_influencers.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

def clean_email(email):
    email = email.strip().lower()

    if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return None

    if "example.com" in email:
        return None

    if "yourdomain" in email:
        return None

    return email

def extract_emails(text):
    if not isinstance(text, str):
        return []

    matches = re.findall(EMAIL_PATTERN, text)

    emails = []

    for email in matches:
        email = clean_email(email)

        if email and email not in emails:
            emails.append(email)

    return emails

def fetch_youtube_about(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/about"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        if response.status_code == 200:
            return response.text

    except Exception:
        pass

    return ""

def find_email_from_youtube(channel_id, description):
    emails = extract_emails(description)

    if emails:
        return emails[0]

    html = fetch_youtube_about(channel_id)

    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        emails = extract_emails(text)

        if emails:
            return emails[0]

    return "Not Found"

df = pd.read_csv(INPUT_FILE)

if "contact_email" not in df.columns:
    df["contact_email"] = "Not Found"

total = len(df)
found = 0
not_found = 0

for index, row in df.iterrows():

    name = str(row.get("name", "Unknown"))
    channel_id = str(row.get("channel_id", ""))
    description = str(row.get("description", ""))

    current_email = str(row.get("contact_email", "")).strip()

    if current_email and current_email.lower() != "not found" and "@" in current_email:
        print(f"Already found: {name} -> {current_email}")
        found += 1
        continue

    print(f"Processing {index + 1}/{total}: {name}")

    email = find_email_from_youtube(
        channel_id,
        description
    )

    df.at[index, "contact_email"] = email

    if email != "Not Found":
        found += 1
        print(f"Email found: {email}")
    else:
        not_found += 1
        print("Email not found")

    time.sleep(0.5)

df.to_csv(OUTPUT_FILE, index=False)

print()
print("Email enrichment completed")
print("Creators processed:", total)
print("Emails found:", found)
print("Not found:", not_found)
print("Saved:", OUTPUT_FILE)