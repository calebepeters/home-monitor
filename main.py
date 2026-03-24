# ABOUTME: Entry point that starts the polling loop and the FastAPI web server
# ABOUTME: Loads config.yaml, initializes the DB, and runs both concurrently

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn
import yaml

from src.monitor.api import create_app
from src.monitor.database import init_db
from src.monitor.poller import poll_forever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def load_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


async def main():
    config = load_config()

    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = str(data_dir / "monitor.db")
    db_conn = init_db(db_path)
    logger.info("Database initialized at %s", db_path)

    static_dir = str(BASE_DIR / "static")
    app = create_app(db_conn, static_dir)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    poller_task = asyncio.create_task(
        poll_forever(config, db_conn, config["ntfy"])
    )

    server_config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="warning")
    server = uvicorn.Server(server_config)
    server_task = asyncio.create_task(server.serve())

    logger.info("Dashboard available at http://0.0.0.0:8080")

    await stop_event.wait()

    poller_task.cancel()
    server.should_exit = True
    await asyncio.gather(poller_task, server_task, return_exceptions=True)
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
