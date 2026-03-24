# ABOUTME: Tests for SQLite database init, reads, writes, and uptime calculation
# ABOUTME: Uses an in-memory database to avoid filesystem side effects

import sqlite3
import pytest
from datetime import datetime, timezone, timedelta

from src.monitor.database import (
    get_host_state,
    get_recent_checks,
    get_uptime_percent,
    init_db,
    record_check,
    upsert_host_state,
)


@pytest.fixture
def db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_init_db_creates_tables(db):
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "checks" in tables
    assert "state" in tables


def test_record_and_retrieve_check(db):
    record_check(db, "TestHost", "ping", True, 12.5, None)
    rows = get_recent_checks(db, "TestHost")
    assert len(rows) == 1
    assert rows[0]["host_name"] == "TestHost"
    assert rows[0]["check_type"] == "ping"
    assert rows[0]["success"] == 1
    assert abs(rows[0]["latency_ms"] - 12.5) < 0.001
    assert rows[0]["error"] is None


def test_record_check_failure(db):
    record_check(db, "TestHost", "http", False, None, "Connection refused")
    rows = get_recent_checks(db, "TestHost")
    assert rows[0]["success"] == 0
    assert rows[0]["latency_ms"] is None
    assert rows[0]["error"] == "Connection refused"


def test_upsert_and_get_host_state(db):
    now = datetime.now(timezone.utc).isoformat()
    upsert_host_state(db, "TestHost", True, 0, now)
    state = get_host_state(db, "TestHost")
    assert state is not None
    assert state["host_name"] == "TestHost"
    assert state["is_up"] == 1
    assert state["consecutive_failures"] == 0

    # Update existing state
    upsert_host_state(db, "TestHost", False, 2, now)
    state = get_host_state(db, "TestHost")
    assert state["is_up"] == 0
    assert state["consecutive_failures"] == 2


def test_get_host_state_missing(db):
    assert get_host_state(db, "Nonexistent") is None


def test_get_recent_checks_limit(db):
    for i in range(10):
        record_check(db, "TestHost", "ping", True, float(i), None)
    rows = get_recent_checks(db, "TestHost", limit=5)
    assert len(rows) == 5


def test_get_uptime_percent_all_success(db):
    for _ in range(10):
        record_check(db, "TestHost", "ping", True, 1.0, None)
    assert get_uptime_percent(db, "TestHost", hours=24) == 100.0


def test_get_uptime_percent_mixed(db):
    for i in range(10):
        record_check(db, "TestHost", "ping", i % 2 == 0, 1.0, None)
    pct = get_uptime_percent(db, "TestHost", hours=24)
    assert pct == 50.0


def test_get_uptime_percent_no_data(db):
    assert get_uptime_percent(db, "NoHost", hours=24) == 100.0
