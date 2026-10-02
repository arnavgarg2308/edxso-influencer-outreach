import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(BASE_DIR, "personalized_influencers.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "website_enriched_influencers.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

PAGE_NAMES = [
    "contact",
    "contact-us",
    "about",
    "about-us",
    "work-with-me",
    "collaborate",
    "collaboration",
    "business"
]

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
    matches = re.findall(EMAIL_PATTERN, text)

    emails = []

    for email in matches:
        email = clean_email(email)

        if email and email not in emails:
            emails.append(email)

    return emails

def fetch_page(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True
        )

        if response.status_code == 200:
            return response.text, response.url

    except Exception:
        pass

    return None, url

def find_emails_on_page(url):
    html, final_url = fetch_page(url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    emails = extract_emails(
        soup.get_text(" ", strip=True)
    )

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.lower().startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0]
            email = clean_email(email)

            if email and email not in emails:
                emails.append(email)

    return emails

def find_contact_pages(base_url):
    pages = [base_url]

    parsed = urlparse(base_url)

    root = f"{parsed.scheme}://{parsed.netloc}"

    for page_name in PAGE_NAMES:
        pages.append(
            urljoin(root, f"/{page_name}")
        )

    return list(dict.fromkeys(pages))

def find_website_from_description(description):
    if not isinstance(description, str):
        return None

    urls = re.findall(
        r"https?://[^\s<>\"]+",
        description
    )

    for url in urls:
        url = url.rstrip(".,)")

        if "youtube.com" not in url:
            return url

    return None

df = pd.read_csv(INPUT_FILE)

if "contact_email" not in df.columns:
    df["contact_email"] = "Not Found"

if "website" not in df.columns:
    df["website"] = ""

total = len(df)

for index, row in df.iterrows():

    name = row["name"]

    current_email = str(
        row.get("contact_email", "Not Found")
    ).strip()

    if current_email.lower() != "not found" and "@" in current_email:
        print(f"Already found: {name}")
        continue

    description = str(
        row.get("description", "")
    )

    website = find_website_from_description(
        description
    )

    if not website:
        print(f"No website: {name}")
        df.at[index, "contact_email"] = "Not Found"
        continue

    print(
        f"Processing {index + 1}/{total}: {name}"
    )

    df.at[index, "website"] = website

    pages = find_contact_pages(website)

    found_email = None

    for page in pages:

        emails = find_emails_on_page(page)

        if emails:
            found_email = emails[0]
            break

        time.sleep(0.5)

    if found_email:
        df.at[index, "contact_email"] = found_email
        print(f"Email found: {found_email}")
    else:
        df.at[index, "contact_email"] = "Not Found"
        print("Email not found")

    time.sleep(1)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("Website enrichment completed")
print("Creators processed:", len(df))
print("Saved:", OUTPUT_FILE)