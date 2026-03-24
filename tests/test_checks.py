# ABOUTME: Tests for ping, HTTP, and TCP check functions
# ABOUTME: Uses local servers and RFC5737 non-routable address for failure cases

import asyncio
import pytest
import pytest_asyncio
from aiohttp import web

from src.monitor.checks import http_check, ping_check, tcp_check


@pytest.mark.asyncio
async def test_ping_success():
    result = await ping_check("127.0.0.1", timeout=5)
    assert result.success is True
    assert result.latency_ms is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_ping_failure():
    # RFC5737 TEST-NET-1 — non-routable, should time out/fail
    result = await ping_check("192.0.2.1", timeout=2)
    assert result.success is False
    assert result.latency_ms is None


@pytest.fixture
def aiohttp_app():
    async def handler_ok(request):
        return web.Response(status=200, text="ok")

    async def handler_404(request):
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/ok", handler_ok)
    app.router.add_get("/notfound", handler_404)
    return app


@pytest_asyncio.fixture
async def http_server(aiohttp_app):
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    yield f"http://127.0.0.1:{port}"
    await runner.cleanup()


@pytest.mark.asyncio
async def test_http_check_success(http_server):
    result = await http_check(f"{http_server}/ok", expected_status=200, timeout=5)
    assert result.success is True
    assert result.latency_ms is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_http_check_wrong_status(http_server):
    result = await http_check(f"{http_server}/notfound", expected_status=200, timeout=5)
    assert result.success is False
    assert "404" in result.error


@pytest.mark.asyncio
async def test_http_check_unreachable():
    result = await http_check("http://127.0.0.1:19999/nope", expected_status=200, timeout=2)
    assert result.success is False
    assert result.error is not None


@pytest_asyncio.fixture
async def tcp_server():
    async def handle(reader, writer):
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield "127.0.0.1", port
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_tcp_check_success(tcp_server):
    host, port = tcp_server
    result = await tcp_check(host, port, timeout=5)
    assert result.success is True
    assert result.latency_ms is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_tcp_check_failure():
    result = await tcp_check("127.0.0.1", 19998, timeout=2)
    assert result.success is False
    assert result.error is not None
