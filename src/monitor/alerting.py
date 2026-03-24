# ABOUTME: ntfy.sh push alert integration for host up/down notifications
# ABOUTME: Fire-and-forget async POST; logs errors but never raises

import logging
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)


async def send_alert(ntfy_url: str, topic: str, host_name: str, is_up: bool):
    title = f"🟢 {host_name} is back UP" if is_up else f"🔴 {host_name} is DOWN"
    priority = "default" if is_up else "urgent"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    body = f"{host_name} {'came back online' if is_up else 'went offline'} at {timestamp}"

    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{ntfy_url}/{topic}",
                data=body,
                headers={
                    "X-Title": title,
                    "X-Priority": priority,
                    "Content-Type": "text/plain",
                },
            )
    except Exception as e:
        logger.error("Failed to send ntfy alert for %s: %s", host_name, e)
