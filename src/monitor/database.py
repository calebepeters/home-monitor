# ABOUTME: SQLite database schema initialization and query functions
# ABOUTME: Stores check results and host state; no ORM, plain sqlite3

import sqlite3
from datetime import datetime, timezone


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_name TEXT NOT NULL,
            check_type TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            success INTEGER NOT NULL,
            latency_ms REAL,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS state (
            host_name TEXT PRIMARY KEY,
            is_up INTEGER NOT NULL,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            last_changed_at TEXT
        );
    """)
    conn.commit()
    return conn


def record_check(conn, host_name, check_type, success, latency_ms, error):
    checked_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO checks (host_name, check_type, checked_at, success, latency_ms, error) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (host_name, check_type, checked_at, int(success), latency_ms, error),
    )
    conn.commit()


def get_host_state(conn, host_name) -> dict | None:
    row = conn.execute(
        "SELECT * FROM state WHERE host_name = ?", (host_name,)
    ).fetchone()
    return dict(row) if row else None


def upsert_host_state(conn, host_name, is_up, consecutive_failures, last_changed_at):
    conn.execute(
        "INSERT OR REPLACE INTO state (host_name, is_up, consecutive_failures, last_changed_at) "
        "VALUES (?, ?, ?, ?)",
        (host_name, int(is_up), consecutive_failures, last_changed_at),
    )
    conn.commit()


def get_recent_checks(conn, host_name, limit=100) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM checks WHERE host_name = ? ORDER BY checked_at DESC LIMIT ?",
        (host_name, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_uptime_percent(conn, host_name, hours=24) -> float:
    rows = conn.execute(
        "SELECT success FROM checks "
        "WHERE host_name = ? AND checked_at >= datetime('now', ? || ' hours') ",
        (host_name, f"-{hours}"),
    ).fetchall()
    if not rows:
        return 100.0
    total = len(rows)
    successes = sum(1 for r in rows if r["success"])
    return round((successes / total) * 100, 2)
