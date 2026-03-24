# ABOUTME: FastAPI application with REST endpoints and static dashboard serving
# ABOUTME: Exposes /api/status, /api/history/{host_name}, and the dashboard at /

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import get_host_state, get_recent_checks, get_uptime_percent


def create_app(db_conn, static_dir: str) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db_conn
        yield

    app = FastAPI(title="Home Network Monitor", lifespan=lifespan)

    @app.get("/api/status")
    async def get_status():
        db = app.state.db
        rows = db.execute("SELECT DISTINCT host_name FROM state").fetchall()
        result = []
        for row in rows:
            host_name = row["host_name"]
            state = get_host_state(db, host_name)
            if not state:
                continue
            uptime = get_uptime_percent(db, host_name, hours=24)
            recent = get_recent_checks(db, host_name, limit=1)
            last_latency = recent[0]["latency_ms"] if recent else None
            result.append({
                "name": host_name,
                "is_up": bool(state["is_up"]),
                "consecutive_failures": state["consecutive_failures"],
                "last_changed_at": state["last_changed_at"],
                "uptime_24h": uptime,
                "last_latency_ms": last_latency,
            })
        return result

    @app.get("/api/history/{host_name}")
    async def get_history(host_name: str):
        db = app.state.db
        checks = get_recent_checks(db, host_name, limit=100)
        if not checks and not get_host_state(db, host_name):
            raise HTTPException(status_code=404, detail="Host not found")
        return [
            {
                "checked_at": c["checked_at"],
                "check_type": c["check_type"],
                "success": bool(c["success"]),
                "latency_ms": c["latency_ms"],
                "error": c["error"],
            }
            for c in checks
        ]

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
