# db/database.py
# SQLite storage for QA results

import sqlite3
from datetime import datetime

DB_PATH = "qa_results.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT,
            workflow_name TEXT,
            url TEXT,
            status TEXT,
            message TEXT,
            analysis TEXT,
            severity TEXT,
            recommendation TEXT,
            duration_seconds INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_result(result: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO results
        (workflow_id, workflow_name, url, status, message,
         analysis, severity, recommendation, duration_seconds, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.get("workflow_id"),
        result.get("workflow_name"),
        result.get("url"),
        result.get("status"),
        result.get("message"),
        result.get("analysis"),
        result.get("severity"),
        result.get("recommendation"),
        result.get("duration_seconds", 0),
        result.get("timestamp", datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()

def get_all_results():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM results ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
