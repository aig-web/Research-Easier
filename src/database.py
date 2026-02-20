import sqlite3
import os
from datetime import datetime

ON_VERCEL = os.environ.get("VERCEL", False)

if ON_VERCEL:
    DB_PATH = "/tmp/ideas.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ideas.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_url TEXT NOT NULL,
            tweet_text TEXT,
            author TEXT,
            author_handle TEXT,
            topic_name TEXT,
            summary TEXT,
            tweet_date TEXT,
            view_count TEXT,
            has_video BOOLEAN DEFAULT 0,
            video_analysis TEXT,
            category TEXT,
            week_number INTEGER,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_idea(data):
    now = datetime.utcnow()
    week_number = now.isocalendar()[1]
    year = now.isocalendar()[0]

    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO ideas (
            tweet_url, tweet_text, author, author_handle,
            topic_name, summary, tweet_date, view_count,
            has_video, video_analysis, category,
            week_number, year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("tweet_url"),
        data.get("tweet_text"),
        data.get("author"),
        data.get("author_handle"),
        data.get("topic_name"),
        data.get("summary"),
        data.get("tweet_date"),
        data.get("view_count"),
        data.get("has_video", False),
        data.get("video_analysis"),
        data.get("category"),
        week_number,
        year,
    ))
    conn.commit()
    idea_id = cursor.lastrowid
    conn.close()
    return idea_id


def get_all_ideas():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ideas ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ideas_by_week():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ideas ORDER BY year DESC, week_number DESC, created_at DESC"
    ).fetchall()
    conn.close()

    weekly = {}
    for row in rows:
        r = dict(row)
        key = f"{r['year']}-W{r['week_number']:02d}"
        if key not in weekly:
            weekly[key] = []
        weekly[key].append(r)
    return weekly


def get_category_summary():
    conn = get_db()
    rows = conn.execute("""
        SELECT category, COUNT(*) as count
        FROM ideas
        WHERE category IS NOT NULL AND category != ''
        GROUP BY category
        ORDER BY count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_idea(idea_id):
    conn = get_db()
    conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    conn.commit()
    conn.close()
