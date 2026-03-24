# ABOUTME: Core polling loop that checks all hosts concurrently on a fixed interval
# ABOUTME: Tracks consecutive failures and triggers alerts on state changes

import asyncio
import logging
from datetime import datetime, timezone

from .alerting import send_alert
from .checks import http_check, ping_check, tcp_check, CheckResult
from .database import get_host_state, record_check, upsert_host_state

logger = logging.getLogger(__name__)


async def check_host(host_config: dict, db_conn, check_timeout: float) -> bool:
    host_name = host_config["name"]
    results: list[CheckResult] = []

    for check in host_config["checks"]:
        check_type = check["type"]
        if check_type == "ping":
            result = await ping_check(check["host"], check_timeout)
        elif check_type == "http":
            result = await http_check(check["url"], check["expected_status"], check_timeout)
        elif check_type == "tcp":
            result = await tcp_check(check["host"], check["port"], check_timeout)
        else:
            logger.warning("Unknown check type '%s' for host %s", check_type, host_name)
            continue

        record_check(
            db_conn,
            host_name,
            check_type,
            result.success,
            result.latency_ms,
            result.error,
        )
        results.append(result)

    all_passed = all(r.success for r in results) if results else False
    return all_passed


async def poll_forever(config: dict, db_conn, ntfy_config: dict):
    hosts = config["hosts"]
    interval = config["polling"]["interval_seconds"]
    alert_after = config["polling"]["alert_after_failures"]
    timeout = config["polling"]["check_timeout_seconds"]

    while True:
        poll_results = await asyncio.gather(
            *[check_host(host, db_conn, timeout) for host in hosts],
            return_exceptions=True,
        )

        now = datetime.now(timezone.utc).isoformat()

        for host, is_up in zip(hosts, poll_results):
            host_name = host["name"]

            if isinstance(is_up, Exception):
                logger.error("Error checking host %s: %s", host_name, is_up)
                is_up = False

            state = get_host_state(db_conn, host_name)
            if state is None:
                state = {
                    "host_name": host_name,
                    "is_up": True,
                    "consecutive_failures": 0,
                    "last_changed_at": now,
                }

            was_up = bool(state["is_up"])
            failures = state["consecutive_failures"]

            if is_up:
                # Recovery alert: was tracked as down, now up
                if not was_up:
                    logger.info("[%s] RECOVERED", host_name)
                    await send_alert(ntfy_config["url"], ntfy_config["topic"], host_name, True)
                    last_changed_at = now
                else:
                    last_changed_at = state["last_changed_at"]
                failures = 0
            else:
                failures += 1
                if failures == alert_after:
                    logger.warning("[%s] DOWN (failure #%d) — sending alert", host_name, failures)
                    await send_alert(ntfy_config["url"], ntfy_config["topic"], host_name, False)
                    last_changed_at = now
                else:
                    last_changed_at = state["last_changed_at"]
                is_up = False

            upsert_host_state(db_conn, host_name, is_up, failures, last_changed_at)

            status_str = "UP" if is_up else f"DOWN (failures={failures})"
            logger.info("[%s] %s", host_name, status_str)

        await asyncio.sleep(interval)
