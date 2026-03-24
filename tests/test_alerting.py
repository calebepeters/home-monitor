# ABOUTME: Tests for ntfy.sh alert POST requests
# ABOUTME: Uses an aiohttp test server to capture and verify outgoing requests

import pytest
import pytest_asyncio
from aiohttp import web

from src.monitor.alerting import send_alert


@pytest_asyncio.fixture
async def ntfy_server():
    """Capture POST requests made to the fake ntfy server."""
    captured = []

    async def handler(request):
        body = await request.text()
        captured.append({
            "path": request.path,
            "headers": dict(request.headers),
            "body": body,
        })
        return web.Response(status=200)

    app = web.Application()
    app.router.add_post("/{topic}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    yield f"http://127.0.0.1:{port}", captured
    await runner.cleanup()


@pytest.mark.asyncio
async def test_down_alert(ntfy_server):
    url, captured = ntfy_server
    await send_alert(url, "test-topic", "My Router", is_up=False)
    assert len(captured) == 1
    req = captured[0]
    assert req["path"] == "/test-topic"
    assert "DOWN" in req["headers"]["X-Title"]
    assert "My Router" in req["headers"]["X-Title"]
    assert req["headers"]["X-Priority"] == "urgent"
    assert "My Router" in req["body"]


@pytest.mark.asyncio
async def test_up_alert(ntfy_server):
    url, captured = ntfy_server
    await send_alert(url, "test-topic", "My Router", is_up=True)
    assert len(captured) == 1
    req = captured[0]
    assert "UP" in req["headers"]["X-Title"]
    assert req["headers"]["X-Priority"] == "default"
    assert "My Router" in req["body"]


@pytest.mark.asyncio
async def test_alert_does_not_raise_on_error():
    # Bad URL — should log and return, not raise
    await send_alert("http://127.0.0.1:19997", "topic", "Host", is_up=False)
