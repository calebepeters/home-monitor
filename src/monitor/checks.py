# ABOUTME: Async check functions for ping, HTTP, and TCP connectivity tests
# ABOUTME: Each function returns a CheckResult with success, latency, and error info

import asyncio
import time
from dataclasses import dataclass

import aiohttp
import icmplib


@dataclass
class CheckResult:
    success: bool
    latency_ms: float | None  # None if check failed before getting a response
    error: str | None         # None if success


async def ping_check(host: str, timeout: float) -> CheckResult:
    try:
        result = await icmplib.async_ping(host, count=1, timeout=timeout, privileged=False)
        if result.is_alive:
            return CheckResult(success=True, latency_ms=result.avg_rtt, error=None)
        else:
            return CheckResult(success=False, latency_ms=None, error="Host did not respond to ping")
    except Exception as e:
        return CheckResult(success=False, latency_ms=None, error=str(e))


async def http_check(url: str, expected_status: int, timeout: float) -> CheckResult:
    start = time.monotonic()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url, ssl=False) as response:
                latency_ms = (time.monotonic() - start) * 1000
                if response.status == expected_status:
                    return CheckResult(success=True, latency_ms=latency_ms, error=None)
                else:
                    return CheckResult(
                        success=False,
                        latency_ms=latency_ms,
                        error=f"Expected status {expected_status}, got {response.status}",
                    )
    except Exception as e:
        return CheckResult(success=False, latency_ms=None, error=str(e))


async def tcp_check(host: str, port: int, timeout: float) -> CheckResult:
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return CheckResult(success=True, latency_ms=latency_ms, error=None)
    except asyncio.TimeoutError:
        return CheckResult(success=False, latency_ms=None, error="Connection timed out")
    except Exception as e:
        return CheckResult(success=False, latency_ms=None, error=str(e))
