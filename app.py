import os
import sys
import base64
import sqlite3
import pandas as pd
import streamlit as st

from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_FILE = os.path.join(BASE_DIR, "final_enriched_influencers.csv")
DB_FILE = os.path.join(BASE_DIR, "outreach.db")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

st.set_page_config(
    page_title="EDXSO Influencer Outreach",
    page_icon="📣",
    layout="wide"
)

st.title("📣 EDXSO AI Influencer Outreach")
st.caption("Automated Micro-Influencer Discovery & Outreach System")

if not os.path.exists(CSV_FILE):
    st.error("final_enriched_influencers.csv not found.")
    st.stop()

df = pd.read_csv(CSV_FILE)

if "contact_email" not in df.columns:
    df["contact_email"] = "Not Found"

if "status" not in df.columns:
    df["status"] = "Pass"

if os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    outreach_df = pd.read_sql_query(
        "SELECT email, status, sent_at FROM outreach",
        conn
    )
    conn.close()
else:
    outreach_df = pd.DataFrame(columns=["email", "status", "sent_at"])

if not outreach_df.empty:
    df = df.merge(
        outreach_df,
        left_on="contact_email",
        right_on="email",
        how="left"
    )
    df["outreach_status"] = df["status_y"].fillna("Not Contacted")
else:
    df["outreach_status"] = "Not Contacted"

total = len(df)
passed = len(df[df["status_x"] == "Pass"]) if "status_x" in df.columns else len(df[df["status"] == "Pass"])
emails = len(df[
    (df["contact_email"].astype(str).str.strip() != "") &
    (df["contact_email"].astype(str).str.lower() != "not found")
])
sent = len(df[df["outreach_status"] == "Sent"])

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Influencers", total)
c2.metric("Qualified", passed)
c3.metric("Public Emails", emails)
c4.metric("Emails Sent", sent)

st.divider()

st.subheader("Influencer Database")

search = st.text_input(
    "Search creator",
    placeholder="Search by creator name..."
)

status_filter = st.selectbox(
    "Outreach Status",
    ["All", "Not Contacted", "Generated", "Sent", "Failed"]
)

filtered = df.copy()

if search:
    filtered = filtered[
        filtered["name"].astype(str).str.contains(
            search,
            case=False,
            na=False
        )
    ]

if status_filter != "All":
    filtered = filtered[
        filtered["outreach_status"] == status_filter
    ]

display_columns = [
    "name",
    "subscribers",
    "niche",
    "contact_email",
    "outreach_status"
]

display_columns = [
    col for col in display_columns
    if col in filtered.columns
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("Creator Details")

if len(filtered) == 0:
    st.warning("No creators found.")
    st.stop()

creator_names = filtered["name"].astype(str).tolist()

selected_name = st.selectbox(
    "Select Creator",
    creator_names
)

creator = filtered[
    filtered["name"].astype(str) == selected_name
].iloc[0]

left, right = st.columns(2)

with left:
    st.markdown("### Creator Information")

    st.write("**Name:**", creator.get("name", ""))
    st.write("**Platform:** YouTube")
    st.write("**Followers:**", creator.get("subscribers", ""))
    st.write("**Niche:**", creator.get("niche", ""))
    st.write("**Email:**", creator.get("contact_email", "Not Found"))

    if "channel_id" in creator:
        url = f"https://www.youtube.com/channel/{creator['channel_id']}"
        st.link_button("Open YouTube Channel", url)

with right:
    st.markdown("### Qualification")

    st.write(
        "**Content Relevance:**",
        creator.get("content_relevance", "")
    )

    st.write(
        "**Brand Fit:**",
        creator.get("brand_fit", "")
    )

    st.write(
        "**Reason:**",
        creator.get("reason", "")
    )

st.divider()

st.subheader("Personalized Outreach")

email_body = str(
    creator.get("personalized_email", "")
)

dm_body = str(
    creator.get("personalized_dm", "")
)

email_col, dm_col = st.columns(2)

with email_col:
    st.markdown("### Email")

    st.text_input(
        "Subject",
        value="Potential AI Collaboration with EDXSO",
        key="email_subject"
    )

    st.text_area(
        "Email Body",
        value=email_body,
        height=300,
        key="email_body"
    )

with dm_col:
    st.markdown("### Instagram DM")

    st.text_area(
        "DM Body",
        value=dm_body,
        height=300,
        key="dm_body"
    )

st.divider()

email = str(
    creator.get("contact_email", "")
).strip()

if not email or email.lower() == "not found":

    st.warning(
        "No public email was found. Instagram DM should be handled manually."
    )

else:

    st.success(f"Public email available: {email}")

    if st.button(
        "📧 Send Email",
        type="primary",
        use_container_width=True
    ):

        try:

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

                    creds = flow.run_local_server(
                        port=0
                    )

                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())

            service = build(
                "gmail",
                "v1",
                credentials=creds
            )

            message = MIMEText(
                st.session_state.email_body,
                "plain",
                "utf-8"
            )

            message["to"] = email
            message["subject"] = st.session_state.email_subject

            encoded = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            result = service.users().messages().send(
                userId="me",
                body={"raw": encoded}
            ).execute()

            conn = sqlite3.connect(DB_FILE)

            conn.execute(
                """
                UPDATE outreach
                SET status = ?,
                    sent_at = datetime('now'),
                    message_id = ?,
                    error = NULL
                WHERE email = ?
                """,
                (
                    "Sent",
                    result.get("id", ""),
                    email
                )
            )

            conn.commit()
            conn.close()

            st.success(
                f"Email sent successfully to {email}"
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Email sending failed: {str(e)}"
            )

st.divider()

st.subheader("System Workflow")

st.code(
    """
YouTube Discovery
        ↓
Creator Deduplication
        ↓
Channel Enrichment
        ↓
5K–100K Follower Filter
        ↓
Gemini Content Classification
        ↓
Public Email Enrichment
        ↓
AI Personalization
        ↓
Email / Instagram DM
        ↓
SQLite Outreach Tracking
    """,
    language="text"
)