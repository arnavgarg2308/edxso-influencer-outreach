import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "outreach.db")

def get_connection():
    return sqlite3.connect(DB_FILE)

def initialize_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS outreach (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            creator_name TEXT,
            email TEXT UNIQUE,
            platform TEXT,
            profile_url TEXT,
            subject TEXT,
            email_body TEXT,
            dm_body TEXT,
            status TEXT DEFAULT 'Generated',
            sent_at TEXT,
            message_id TEXT,
            error TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_outreach(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM outreach WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()
    return row

def save_generated(data):
    conn = get_connection()

    conn.execute("""
        INSERT OR IGNORE INTO outreach
        (channel_id, creator_name, email, platform, profile_url, subject, email_body, dm_body, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["channel_id"],
        data["name"],
        data["email"],
        data["platform"],
        data["profile_url"],
        data["subject"],
        data["email_body"],
        data["dm_body"],
        "Generated"
    ))

    conn.commit()
    conn.close()

def mark_sent(email, message_id):
    conn = get_connection()

    conn.execute("""
        UPDATE outreach
        SET status = ?, sent_at = datetime('now'), message_id = ?, error = NULL
        WHERE email = ?
    """, (
        "Sent",
        message_id,
        email
    ))

    conn.commit()
    conn.close()

def mark_failed(email, error):
    conn = get_connection()

    conn.execute("""
        UPDATE outreach
        SET status = ?, error = ?
        WHERE email = ?
    """, (
        "Failed",
        str(error),
        email
    ))

    conn.commit()
    conn.close()