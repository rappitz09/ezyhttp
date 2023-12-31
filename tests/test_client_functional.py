# type: ignore
# HTTP client functional tests against ezyhttp.web server

import asyncio
import datetime
import http.cookies
import io
import json
import pathlib
import socket
import ssl
from typing import Any, AsyncIterator
from unittest import mock

import pytest
from multidict import MultiDict
from yarl import URL

import ezyhttp
from ezyhttp import Fingerprint, ServerFingerprintMismatch, hdrs, web
from ezyhttp.abc import AbstractResolver
from ezyhttp.client_exceptions import SocketTimeoutError, TooManyRedirects
from ezyhttp.pytest_plugin import ezyhttpClient, TestClient
from ezyhttp.test_utils import unused_port


@pytest.fixture
def here():
    return pathlib.Path(__file__).parent


@pytest.fixture
def fname(here: Any):
    return here / "conftest.py"


async def test_keepalive_two_requests_success(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(body=b"OK")

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(app, connector=connector)

    resp1 = await client.get("/")
    await resp1.read()
    resp2 = await client.get("/")
    await resp2.read()

    assert 1 == len(client._session.connector._conns)


async def test_keepalive_after_head_requests_success(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(body=b"OK")

    cnt_conn_reuse = 0

    async def on_reuseconn(session, ctx, params):
        nonlocal cnt_conn_reuse
        cnt_conn_reuse += 1

    trace_config = ezyhttp.TraceConfig()
    trace_config._on_connection_reuseconn.append(on_reuseconn)

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    app.router.add_route("HEAD", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(
        app, connector=connector, trace_configs=[trace_config]
    )

    resp1 = await client.head("/")
    await resp1.read()
    resp2 = await client.get("/")
    await resp2.read()

    assert 1 == cnt_conn_reuse


@pytest.mark.parametrize("status", (101, 204, 304))
async def test_keepalive_after_empty_body_status(
    ezyhttp_client: Any, status: int
) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(status=status)

    cnt_conn_reuse = 0

    async def on_reuseconn(session, ctx, params):
        nonlocal cnt_conn_reuse
        cnt_conn_reuse += 1

    trace_config = ezyhttp.TraceConfig()
    trace_config._on_connection_reuseconn.append(on_reuseconn)

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(
        app, connector=connector, trace_configs=[trace_config]
    )

    resp1 = await client.get("/")
    await resp1.read()
    resp2 = await client.get("/")
    await resp2.read()

    assert cnt_conn_reuse == 1


@pytest.mark.parametrize("status", (101, 204, 304))
async def test_keepalive_after_empty_body_status_stream_response(
    ezyhttp_client: Any, status: int
) -> None:
    async def handler(request):
        stream_response = web.StreamResponse(status=status)
        await stream_response.prepare(request)
        return stream_response

    cnt_conn_reuse = 0

    async def on_reuseconn(session, ctx, params):
        nonlocal cnt_conn_reuse
        cnt_conn_reuse += 1

    trace_config = ezyhttp.TraceConfig()
    trace_config._on_connection_reuseconn.append(on_reuseconn)

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(
        app, connector=connector, trace_configs=[trace_config]
    )

    resp1 = await client.get("/")
    await resp1.read()
    resp2 = await client.get("/")
    await resp2.read()

    assert cnt_conn_reuse == 1


async def test_keepalive_response_released(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(body=b"OK")

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(app, connector=connector)

    resp1 = await client.get("/")
    resp1.release()
    resp2 = await client.get("/")
    resp2.release()

    assert 1 == len(client._session.connector._conns)


async def test_upgrade_connection_not_released_after_read(ezyhttp_client: Any) -> None:
    async def handler(request: web.Request) -> web.Response:
        body = await request.read()
        assert b"" == body
        return web.Response(
            status=101, headers={"Connection": "Upgrade", "Upgrade": "tcp"}
        )

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    client = await ezyhttp_client(app)

    resp = await client.get("/")
    await resp.read()
    assert resp.connection is not None
    assert not resp.closed


async def test_keepalive_server_force_close_connection(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        response = web.Response(body=b"OK")
        response.force_close()
        return response

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(app, connector=connector)

    resp1 = await client.get("/")
    resp1.close()
    resp2 = await client.get("/")
    resp2.close()

    assert 0 == len(client._session.connector._conns)


async def test_release_early(ezyhttp_client: Any) -> None:
    async def handler(request):
        await request.read()
        return web.Response(body=b"OK")

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    client = await ezyhttp_client(app)
    resp = await client.get("/")
    assert resp.closed
    await resp.wait_for_close()
    assert 1 == len(client._session.connector._conns)


async def test_HTTP_304(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(status=304)

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert resp.status == 304
    content = await resp.read()
    assert content == b""


async def test_stream_request_on_server_eof(ezyhttp_client) -> None:
    async def handler(request):
        return web.Response(text="OK", status=200)

    app = web.Application()
    app.add_routes([web.get("/", handler)])
    app.add_routes([web.put("/", handler)])

    client = await ezyhttp_client(app)

    async def data_gen():
        for _ in range(2):
            yield b"just data"
            await asyncio.sleep(0.1)

    async with client.put("/", data=data_gen()) as resp:
        assert 200 == resp.status
        assert len(client.session.connector._acquired) == 1
        conn = next(iter(client.session.connector._acquired))

    async with client.get("/") as resp:
        assert 200 == resp.status

    # Connection should have been reused
    conns = next(iter(client.session.connector._conns.values()))
    assert len(conns) == 1
    assert conns[0][0] is conn


async def test_stream_request_on_server_eof_nested(ezyhttp_client) -> None:
    async def handler(request):
        return web.Response(text="OK", status=200)

    app = web.Application()
    app.add_routes([web.get("/", handler)])
    app.add_routes([web.put("/", handler)])

    client = await ezyhttp_client(app)

    async def data_gen():
        for _ in range(2):
            yield b"just data"
            await asyncio.sleep(0.1)

    async with client.put("/", data=data_gen()) as resp:
        assert 200 == resp.status
        async with client.get("/") as resp:
            assert 200 == resp.status

    # Should be 2 separate connections
    conns = next(iter(client.session.connector._conns.values()))
    assert len(conns) == 2


async def test_HTTP_304_WITH_BODY(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        return web.Response(body=b"test", status=304)

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert resp.status == 304
    content = await resp.read()
    assert content == b""


async def test_auto_header_user_agent(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert "ezyhttp" in request.headers["user-agent"]
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert 200 == resp.status


async def test_skip_auto_headers_user_agent(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert hdrs.USER_AGENT not in request.headers
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/", skip_auto_headers=["user-agent"]) as resp:
        assert 200 == resp.status


async def test_skip_default_auto_headers_user_agent(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert hdrs.USER_AGENT not in request.headers
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app, skip_auto_headers=["user-agent"])

    async with client.get("/") as resp:
        assert 200 == resp.status


async def test_skip_auto_headers_content_type(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert hdrs.CONTENT_TYPE not in request.headers
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/", skip_auto_headers=["content-type"]) as resp:
        assert 200 == resp.status


async def test_post_data_bytesio(ezyhttp_client: Any) -> None:
    data = b"some buffer"

    async def handler(request):
        assert len(data) == request.content_length
        val = await request.read()
        assert data == val
        return web.Response()

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    client = await ezyhttp_client(app)

    with io.BytesIO(data) as file_handle:
        async with client.post("/", data=file_handle) as resp:
            assert 200 == resp.status


async def test_post_data_with_bytesio_file(ezyhttp_client: Any) -> None:
    data = b"some buffer"

    async def handler(request):
        post_data = await request.post()
        assert ["file"] == list(post_data.keys())
        assert data == post_data["file"].file.read()
        return web.Response()

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    client = await ezyhttp_client(app)

    with io.BytesIO(data) as file_handle:
        async with client.post("/", data={"file": file_handle}) as resp:
            assert 200 == resp.status


async def test_post_data_stringio(ezyhttp_client: Any) -> None:
    data = "some buffer"

    async def handler(request):
        assert len(data) == request.content_length
        assert request.headers["CONTENT-TYPE"] == "text/plain; charset=utf-8"
        val = await request.text()
        assert data == val
        return web.Response()

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    client = await ezyhttp_client(app)

    async with client.post("/", data=io.StringIO(data)) as resp:
        assert 200 == resp.status


async def test_post_data_textio_encoding(ezyhttp_client: Any) -> None:
    data = "текст"

    async def handler(request):
        assert request.headers["CONTENT-TYPE"] == "text/plain; charset=koi8-r"
        val = await request.text()
        assert data == val
        return web.Response()

    app = web.Application()
    app.router.add_route("POST", "/", handler)
    client = await ezyhttp_client(app)

    pl = ezyhttp.TextIOPayload(io.StringIO(data), encoding="koi8-r")
    async with client.post("/", data=pl) as resp:
        assert 200 == resp.status


async def test_ssl_client(
    ezyhttp_server: Any, ssl_ctx: Any, ezyhttp_client: Any, client_ssl_ctx: Any
) -> None:
    connector = ezyhttp.TCPConnector(ssl=client_ssl_ctx)

    async def handler(request):
        return web.Response(text="Test message")

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_server(app, ssl=ssl_ctx)
    client = await ezyhttp_client(server, connector=connector)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "Test message"


async def test_tcp_connector_fingerprint_ok(
    ezyhttp_server: Any,
    ezyhttp_client: Any,
    ssl_ctx: Any,
    tls_certificate_fingerprint_sha256: Any,
):
    tls_fingerprint = Fingerprint(tls_certificate_fingerprint_sha256)

    async def handler(request):
        return web.Response(text="Test message")

    connector = ezyhttp.TCPConnector(ssl=tls_fingerprint)
    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_server(app, ssl=ssl_ctx)
    client = await ezyhttp_client(server, connector=connector)

    async with client.get("/") as resp:
        assert resp.status == 200


async def test_tcp_connector_fingerprint_fail(
    ezyhttp_server: Any,
    ezyhttp_client: Any,
    ssl_ctx: Any,
    tls_certificate_fingerprint_sha256: Any,
):
    async def handler(request):
        return web.Response(text="Test message")

    bad_fingerprint = b"\x00" * len(tls_certificate_fingerprint_sha256)

    connector = ezyhttp.TCPConnector(ssl=Fingerprint(bad_fingerprint))

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_server(app, ssl=ssl_ctx)
    client = await ezyhttp_client(server, connector=connector)

    with pytest.raises(ServerFingerprintMismatch) as cm:
        await client.get("/")
    exc = cm.value
    assert exc.expected == bad_fingerprint
    assert exc.got == tls_certificate_fingerprint_sha256


async def test_format_task_get(ezyhttp_server: Any) -> None:
    async def handler(request):
        return web.Response(body=b"OK")

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_server(app)
    client = ezyhttp.ClientSession()
    task = asyncio.create_task(client.get(server.make_url("/")))
    assert f"{task}".startswith("<Task pending")
    resp = await task
    resp.close()
    await client.close()


async def test_str_params(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert "q=t est" in request.rel_url.query_string
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/", params="q=t+est") as resp:
        assert 200 == resp.status


async def test_drop_params_on_redirect(ezyhttp_client: Any) -> None:
    async def handler_redirect(request):
        return web.Response(status=301, headers={"Location": "/ok?a=redirect"})

    async def handler_ok(request):
        assert request.rel_url.query_string == "a=redirect"
        return web.Response(status=200)

    app = web.Application()
    app.router.add_route("GET", "/ok", handler_ok)
    app.router.add_route("GET", "/redirect", handler_redirect)
    client = await ezyhttp_client(app)

    async with client.get("/redirect", params={"a": "initial"}) as resp:
        assert resp.status == 200


async def test_drop_fragment_on_redirect(ezyhttp_client: Any) -> None:
    async def handler_redirect(request):
        return web.Response(status=301, headers={"Location": "/ok#fragment"})

    async def handler_ok(request):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_route("GET", "/ok", handler_ok)
    app.router.add_route("GET", "/redirect", handler_redirect)
    client = await ezyhttp_client(app)

    async with client.get("/redirect") as resp:
        assert resp.status == 200
        assert resp.url.path == "/ok"


async def test_drop_fragment(ezyhttp_client: Any) -> None:
    async def handler_ok(request):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_route("GET", "/ok", handler_ok)
    client = await ezyhttp_client(app)

    async with client.get("/ok#fragment") as resp:
        assert resp.status == 200
        assert resp.url.path == "/ok"


async def test_history(ezyhttp_client: Any) -> None:
    async def handler_redirect(request):
        return web.Response(status=301, headers={"Location": "/ok"})

    async def handler_ok(request):
        return web.Response(status=200)

    app = web.Application()
    app.router.add_route("GET", "/ok", handler_ok)
    app.router.add_route("GET", "/redirect", handler_redirect)
    client = await ezyhttp_client(app)

    async with client.get("/ok") as resp:
        assert len(resp.history) == 0
        assert resp.status == 200

    async with client.get("/redirect") as resp_redirect:
        assert len(resp_redirect.history) == 1
        assert resp_redirect.history[0].status == 301
        assert resp_redirect.status == 200


async def test_keepalive_closed_by_server(ezyhttp_client: Any) -> None:
    async def handler(request):
        body = await request.read()
        assert b"" == body
        resp = web.Response(body=b"OK")
        resp.force_close()
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    connector = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(app, connector=connector)

    resp1 = await client.get("/")
    val1 = await resp1.read()
    assert val1 == b"OK"
    resp2 = await client.get("/")
    val2 = await resp2.read()
    assert val2 == b"OK"

    assert 0 == len(client._session.connector._conns)


async def test_wait_for(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"OK")

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    resp = await asyncio.wait_for(client.get("/"), 10)
    assert resp.status == 200
    txt = await resp.text()
    assert txt == "OK"


async def test_raw_headers(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)
    async with client.get("/") as resp:
        assert resp.status == 200

        raw_headers = tuple((bytes(h), bytes(v)) for h, v in resp.raw_headers)
        assert raw_headers == (
            (b"Content-Length", b"0"),
            (b"Content-Type", b"application/octet-stream"),
            (b"Date", mock.ANY),
            (b"Server", mock.ANY),
        )


async def test_host_header_first(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert list(request.headers)[0] == hdrs.HOST
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)
    async with client.get("/") as resp:
        assert resp.status == 200


async def test_empty_header_values(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response()
        resp.headers["X-Empty"] = ""
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)
    async with client.get("/") as resp:
        assert resp.status == 200
        raw_headers = tuple((bytes(h), bytes(v)) for h, v in resp.raw_headers)
        assert raw_headers == (
            (b"X-Empty", b""),
            (b"Content-Length", b"0"),
            (b"Content-Type", b"application/octet-stream"),
            (b"Date", mock.ANY),
            (b"Server", mock.ANY),
        )


async def test_204_with_gzipped_content_encoding(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse(status=204)
        resp.content_length = 0
        resp.content_type = "application/json"
        # resp.enable_compression(web.ContentCoding.gzip)
        resp.headers["Content-Encoding"] = "gzip"
        await resp.prepare(request)
        return resp

    app = web.Application()
    app.router.add_route("DELETE", "/", handler)
    client = await ezyhttp_client(app)

    async with client.delete("/") as resp:
        assert resp.status == 204
        assert resp.closed


async def test_timeout_on_reading_headers(ezyhttp_client: Any, mocker: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse()
        await asyncio.sleep(0.1)
        await resp.prepare(request)
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    with pytest.raises(asyncio.TimeoutError):
        await client.get("/", timeout=ezyhttp.ClientTimeout(total=0.01))


async def test_timeout_on_conn_reading_headers(
    ezyhttp_client: Any, mocker: Any
) -> None:
    # tests case where user did not set a connection timeout

    async def handler(request):
        resp = web.StreamResponse()
        await asyncio.sleep(0.1)
        await resp.prepare(request)
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    conn = ezyhttp.TCPConnector()
    client = await ezyhttp_client(app, connector=conn)

    with pytest.raises(asyncio.TimeoutError):
        await client.get("/", timeout=ezyhttp.ClientTimeout(total=0.01))


async def test_timeout_on_session_read_timeout(
    ezyhttp_client: Any, mocker: Any
) -> None:
    async def handler(request):
        resp = web.StreamResponse()
        await asyncio.sleep(0.1)
        await resp.prepare(request)
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    conn = ezyhttp.TCPConnector()
    client = await ezyhttp_client(
        app, connector=conn, timeout=ezyhttp.ClientTimeout(sock_read=0.01)
    )

    with pytest.raises(asyncio.TimeoutError):
        await client.get("/")


async def test_read_timeout_between_chunks(ezyhttp_client: Any, mocker: Any) -> None:
    async def handler(request):
        resp = ezyhttp.web.StreamResponse()
        await resp.prepare(request)
        # write data 4 times, with pauses. Total time 2 seconds.
        for _ in range(4):
            await asyncio.sleep(0.5)
            await resp.write(b"data\n")
        return resp

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    # A timeout of 0.2 seconds should apply per read.
    timeout = ezyhttp.ClientTimeout(sock_read=1)
    client = await ezyhttp_client(app, timeout=timeout)

    res = b""
    async with await client.get("/") as resp:
        res += await resp.read()

    assert res == b"data\n" * 4


async def test_read_timeout_on_reading_chunks(ezyhttp_client: Any, mocker: Any) -> None:
    async def handler(request):
        resp = ezyhttp.web.StreamResponse()
        await resp.prepare(request)
        await resp.write(b"data\n")
        await asyncio.sleep(1)
        await resp.write(b"data\n")
        return resp

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    # A timeout of 0.2 seconds should apply per read.
    timeout = ezyhttp.ClientTimeout(sock_read=0.2)
    client = await ezyhttp_client(app, timeout=timeout)

    async with await client.get("/") as resp:
        assert (await resp.content.read(5)) == b"data\n"
        with pytest.raises(asyncio.TimeoutError):
            await resp.content.read()


async def test_read_timeout_on_write(ezyhttp_client: Any) -> None:
    async def gen_payload() -> AsyncIterator[str]:
        # Delay writing to ensure read timeout isn't triggered before writing completes.
        await asyncio.sleep(0.5)
        yield b"foo"

    async def handler(request: web.Request) -> web.Response:
        return web.Response(body=await request.read())

    app = web.Application()
    app.router.add_put("/", handler)

    timeout = ezyhttp.ClientTimeout(total=None, sock_read=0.1)
    client = await ezyhttp_client(app)
    async with client.put("/", data=gen_payload(), timeout=timeout) as resp:
        result = await resp.read()  # Should not trigger a read timeout.
    assert result == b"foo"


async def test_timeout_on_reading_data(ezyhttp_client: Any, mocker: Any) -> None:
    loop = asyncio.get_event_loop()

    fut = loop.create_future()

    async def handler(request):
        resp = web.StreamResponse(headers={"content-length": "100"})
        await resp.prepare(request)
        fut.set_result(None)
        await asyncio.sleep(0.2)
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/", timeout=ezyhttp.ClientTimeout(1))
    await fut

    with pytest.raises(asyncio.TimeoutError):
        await resp.read()


async def test_timeout_none(ezyhttp_client: Any, mocker: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse()
        await resp.prepare(request)
        return resp

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/", timeout=None) as resp:
        assert resp.status == 200


async def test_readline_error_on_conn_close(ezyhttp_client: Any) -> None:
    loop = asyncio.get_event_loop()

    async def handler(request):
        resp_ = web.StreamResponse()
        await resp_.prepare(request)

        # make sure connection is closed by client.
        with pytest.raises(ezyhttp.ServerDisconnectedError):
            for _ in range(10):
                await resp_.write(b"data\n")
                await asyncio.sleep(0.5)
            return resp_

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_client(app)

    session = ezyhttp.ClientSession()
    try:
        timer_started = False
        url, headers = server.make_url("/"), {"Connection": "Keep-alive"}
        resp = await session.get(url, headers=headers)
        with pytest.raises(ezyhttp.ClientConnectionError):
            while True:
                data = await resp.content.readline()
                data = data.strip()
                if not data:
                    break
                assert data == b"data"
                if not timer_started:

                    def do_release():
                        loop.create_task(resp.release())

                    loop.call_later(1.0, do_release)
                    timer_started = True
    finally:
        await session.close()


async def test_no_error_on_conn_close_if_eof(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp_ = web.StreamResponse()
        await resp_.prepare(request)
        await resp_.write(b"data\n")
        await asyncio.sleep(0.5)
        return resp_

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_client(app)

    session = ezyhttp.ClientSession()
    try:
        url, headers = server.make_url("/"), {"Connection": "Keep-alive"}
        resp = await session.get(url, headers=headers)
        while True:
            data = await resp.content.readline()
            data = data.strip()
            if not data:
                break
            assert data == b"data"

        assert resp.content.exception() is None
    finally:
        await session.close()


async def test_error_not_overwrote_on_conn_close(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp_ = web.StreamResponse()
        await resp_.prepare(request)
        return resp_

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    server = await ezyhttp_client(app)

    session = ezyhttp.ClientSession()
    try:
        url, headers = server.make_url("/"), {"Connection": "Keep-alive"}
        resp = await session.get(url, headers=headers)
        resp.content.set_exception(ValueError())
    finally:
        await session.close()

    assert isinstance(resp.content.exception(), ValueError)


async def test_HTTP_200_OK_METHOD(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    app = web.Application()
    for meth in ("get", "post", "put", "delete", "head", "patch", "options"):
        app.router.add_route(meth.upper(), "/", handler)

    client = await ezyhttp_client(app)
    for meth in ("get", "post", "put", "delete", "head", "patch", "options"):
        resp = await client.request(meth, "/")
        assert resp.status == 200
        assert len(resp.history) == 0

        content1 = await resp.read()
        content2 = await resp.read()
        assert content1 == content2
        content = await resp.text()

        if meth == "head":
            assert b"" == content1
        else:
            assert meth.upper() == content


async def test_HTTP_200_OK_METHOD_connector(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    conn = ezyhttp.TCPConnector()
    conn.clear_dns_cache()

    app = web.Application()
    for meth in ("get", "post", "put", "delete", "head"):
        app.router.add_route(meth.upper(), "/", handler)
    client = await ezyhttp_client(app, connector=conn)

    for meth in ("get", "post", "put", "delete", "head"):
        resp = await client.request(meth, "/")

        content1 = await resp.read()
        content2 = await resp.read()
        assert content1 == content2
        content = await resp.text()

        assert resp.status == 200
        if meth == "head":
            assert b"" == content1
        else:
            assert meth.upper() == content


async def test_HTTP_302_REDIRECT_GET(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        raise web.HTTPFound(location="/")

    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get("/redirect", redirect)
    client = await ezyhttp_client(app)

    async with client.get("/redirect") as resp:
        assert 200 == resp.status
        assert 1 == len(resp.history)


async def test_HTTP_302_REDIRECT_HEAD(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        raise web.HTTPFound(location="/")

    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get("/redirect", redirect)
    app.router.add_head("/", handler)
    app.router.add_head("/redirect", redirect)
    client = await ezyhttp_client(app)

    async with client.request("head", "/redirect") as resp:
        assert 200 == resp.status
        assert 1 == len(resp.history)
        assert resp.method == "HEAD"


async def test_HTTP_302_REDIRECT_NON_HTTP(ezyhttp_client: Any) -> None:
    async def redirect(request):
        raise web.HTTPFound(location="ftp://127.0.0.1/test/")

    app = web.Application()
    app.router.add_get("/redirect", redirect)
    client = await ezyhttp_client(app)

    with pytest.raises(ValueError):
        await client.get("/redirect")


async def test_HTTP_302_REDIRECT_POST(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        raise web.HTTPFound(location="/")

    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_post("/redirect", redirect)
    client = await ezyhttp_client(app)

    resp = await client.post("/redirect")
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = await resp.text()
    assert txt == "GET"
    resp.close()


async def test_HTTP_302_REDIRECT_POST_with_content_length_hdr(
    ezyhttp_client: Any,
) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        await request.read()
        raise web.HTTPFound(location="/")

    data = json.dumps({"some": "data"})
    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_post("/redirect", redirect)
    client = await ezyhttp_client(app)

    resp = await client.post(
        "/redirect", data=data, headers={"Content-Length": str(len(data))}
    )
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = await resp.text()
    assert txt == "GET"
    resp.close()


async def test_HTTP_307_REDIRECT_POST(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        await request.read()
        raise web.HTTPTemporaryRedirect(location="/")

    app = web.Application()
    app.router.add_post("/", handler)
    app.router.add_post("/redirect", redirect)
    client = await ezyhttp_client(app)

    resp = await client.post("/redirect", data={"some": "data"})
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = await resp.text()
    assert txt == "POST"
    resp.close()


async def test_HTTP_308_PERMANENT_REDIRECT_POST(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        await request.read()
        raise web.HTTPPermanentRedirect(location="/")

    app = web.Application()
    app.router.add_post("/", handler)
    app.router.add_post("/redirect", redirect)
    client = await ezyhttp_client(app)

    resp = await client.post("/redirect", data={"some": "data"})
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = await resp.text()
    assert txt == "POST"
    resp.close()


async def test_HTTP_302_max_redirects(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        count = int(request.match_info["count"])
        if count:
            raise web.HTTPFound(location=f"/redirect/{count - 1}")
        else:
            raise web.HTTPFound(location="/")

    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get(r"/redirect/{count:\d+}", redirect)
    client = await ezyhttp_client(app)

    with pytest.raises(TooManyRedirects) as ctx:
        await client.get("/redirect/5", max_redirects=2)
    assert 2 == len(ctx.value.history)
    assert ctx.value.request_info.url.path == "/redirect/5"
    assert ctx.value.request_info.method == "GET"


async def test_HTTP_200_GET_WITH_PARAMS(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(
            text="&".join(k + "=" + v for k, v in request.query.items())
        )

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/", params={"q": "test"})
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "q=test"
    resp.close()


async def test_HTTP_200_GET_WITH_MultiDict_PARAMS(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(
            text="&".join(k + "=" + v for k, v in request.query.items())
        )

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/", params=MultiDict([("q", "test"), ("q", "test2")]))
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "q=test&q=test2"
    resp.close()


async def test_HTTP_200_GET_WITH_MIXED_PARAMS(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(
            text="&".join(k + "=" + v for k, v in request.query.items())
        )

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/?test=true", params={"q": "test"})
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "test=true&q=test"
    resp.close()


async def test_POST_DATA(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        return web.json_response(dict(data))

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.post("/", data={"some": "data"})
    assert 200 == resp.status
    content = await resp.json()
    assert content == {"some": "data"}
    resp.close()


async def test_POST_DATA_with_explicit_formdata(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        return web.json_response(dict(data))

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData()
    form.add_field("name", "text")

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.json()
    assert content == {"name": "text"}
    resp.close()


async def test_POST_DATA_with_charset(ezyhttp_client: Any) -> None:
    async def handler(request):
        mp = await request.multipart()
        part = await mp.next()
        text = await part.text()
        return web.Response(text=text)

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData()
    form.add_field("name", "текст", content_type="text/plain; charset=koi8-r")

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.text()
    assert content == "текст"
    resp.close()


async def test_POST_DATA_formdats_with_charset(ezyhttp_client: Any) -> None:
    async def handler(request):
        mp = await request.post()
        assert "name" in mp
        return web.Response(text=mp["name"])

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData(charset="koi8-r")
    form.add_field("name", "текст")

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.text()
    assert content == "текст"
    resp.close()


async def test_POST_DATA_with_charset_post(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        return web.Response(text=data["name"])

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData()
    form.add_field("name", "текст", content_type="text/plain; charset=koi8-r")

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.text()
    assert content == "текст"
    resp.close()


async def test_POST_DATA_with_context_transfer_encoding(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data["name"] == "text"
        return web.Response(text=data["name"])

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData()
    form.add_field("name", "text", content_transfer_encoding="base64")

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.text()
    assert content == "text"
    resp.close()


async def test_POST_DATA_with_content_type_context_transfer_encoding(
    ezyhttp_client: Any,
):
    async def handler(request):
        data = await request.post()
        assert data["name"] == "text"
        return web.Response(body=data["name"])

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    form = ezyhttp.FormData()
    form.add_field(
        "name", "text", content_type="text/plain", content_transfer_encoding="base64"
    )

    resp = await client.post("/", data=form)
    assert 200 == resp.status
    content = await resp.text()
    assert content == "text"
    resp.close()


async def test_POST_MultiDict(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data == MultiDict([("q", "test1"), ("q", "test2")])
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    async with client.post(
        "/", data=MultiDict([("q", "test1"), ("q", "test2")])
    ) as resp:
        assert 200 == resp.status


async def test_POST_DATA_DEFLATE(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        return web.json_response(dict(data))

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.post("/", data={"some": "data"}, compress=True)
    assert 200 == resp.status
    content = await resp.json()
    assert content == {"some": "data"}
    resp.close()


async def test_POST_FILES(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data["some"].filename == fname.name
        with fname.open("rb") as f:
            content1 = f.read()
        content2 = data["some"].file.read()
        assert content1 == content2
        assert data["test"].file.read() == b"data"
        data["some"].file.close()
        data["test"].file.close()
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post(
            "/", data={"some": f, "test": b"data"}, chunked=True
        ) as resp:
            assert 200 == resp.status


async def test_POST_FILES_DEFLATE(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data["some"].filename == fname.name
        with fname.open("rb") as f:
            content1 = f.read()
        content2 = data["some"].file.read()
        data["some"].file.close()
        assert content1 == content2
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post(
            "/", data={"some": f}, chunked=True, compress="deflate"
        ) as resp:
            assert 200 == resp.status


async def test_POST_bytes(ezyhttp_client: Any) -> None:
    body = b"0" * 12345

    async def handler(request):
        data = await request.read()
        assert body == data
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    async with client.post("/", data=body) as resp:
        assert 200 == resp.status


async def test_POST_bytes_too_large(ezyhttp_client: Any) -> None:
    body = b"0" * (2**20 + 1)

    async def handler(request):
        data = await request.content.read()
        assert body == data
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with pytest.warns(ResourceWarning):
        resp = await client.post("/", data=body)

    assert 200 == resp.status
    resp.close()


async def test_POST_FILES_STR(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        with fname.open("rb") as f:
            content1 = f.read().decode()
        content2 = data["some"]
        assert content1 == content2
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data={"some": f.read().decode()}) as resp:
            assert 200 == resp.status


async def test_POST_FILES_STR_SIMPLE(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.read()
        with fname.open("rb") as f:
            content = f.read()
        assert content == data
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data=f.read()) as resp:
            assert 200 == resp.status


async def test_POST_FILES_LIST(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert fname.name == data["some"].filename
        with fname.open("rb") as f:
            content = f.read()
        assert content == data["some"].file.read()
        data["some"].file.close()
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data=[("some", f)]) as resp:
            assert 200 == resp.status


async def test_POST_FILES_CT(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert fname.name == data["some"].filename
        assert "text/plain" == data["some"].content_type
        with fname.open("rb") as f:
            content = f.read()
        assert content == data["some"].file.read()
        data["some"].file.close()
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        form = ezyhttp.FormData()
        form.add_field("some", f, content_type="text/plain")
        async with client.post("/", data=form) as resp:
            assert 200 == resp.status


async def test_POST_FILES_SINGLE(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.text()
        with fname.open("rb") as f:
            content = f.read().decode()
            assert content == data
        # if system cannot determine 'text/x-python' MIME type
        # then use 'application/octet-stream' default
        assert request.content_type in [
            "text/plain",
            "application/octet-stream",
            "text/x-python",
        ]
        assert "content-disposition" not in request.headers

        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data=f) as resp:
            assert 200 == resp.status


async def test_POST_FILES_SINGLE_content_disposition(
    ezyhttp_client: Any, fname: Any
) -> None:
    async def handler(request):
        data = await request.text()
        with fname.open("rb") as f:
            content = f.read().decode()
            assert content == data
        # if system cannot determine 'application/pgp-keys' MIME type
        # then use 'application/octet-stream' default
        assert request.content_type in [
            "text/plain",
            "application/octet-stream",
            "text/x-python",
        ]
        assert request.headers["content-disposition"] == (
            'inline; filename="conftest.py"'
        )

        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post(
            "/", data=ezyhttp.get_payload(f, disposition="inline")
        ) as resp:
            assert 200 == resp.status


async def test_POST_FILES_SINGLE_BINARY(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.read()
        with fname.open("rb") as f:
            content = f.read()
        assert content == data
        # if system cannot determine 'application/pgp-keys' MIME type
        # then use 'application/octet-stream' default
        assert request.content_type in [
            "application/pgp-keys",
            "text/plain",
            "text/x-python",
            "application/octet-stream",
        ]
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data=f) as resp:
            assert 200 == resp.status


async def test_POST_FILES_IO(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert b"data" == data["unknown"].file.read()
        assert data["unknown"].content_type == "application/octet-stream"
        assert data["unknown"].filename == "unknown"
        data["unknown"].file.close()
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with io.BytesIO(b"data") as file_handle:
        async with client.post("/", data=[file_handle]) as resp:
            assert 200 == resp.status


async def test_POST_FILES_IO_WITH_PARAMS(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data["test"] == "true"
        assert data["unknown"].content_type == "application/octet-stream"
        assert data["unknown"].filename == "unknown"
        assert data["unknown"].file.read() == b"data"
        data["unknown"].file.close()
        assert data.getall("q") == ["t1", "t2"]

        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with io.BytesIO(b"data") as file_handle:
        async with client.post(
            "/",
            data=(("test", "true"), MultiDict([("q", "t1"), ("q", "t2")]), file_handle),
        ) as resp:
            assert 200 == resp.status


async def test_POST_FILES_WITH_DATA(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        data = await request.post()
        assert data["test"] == "true"
        assert data["some"].content_type in [
            "text/x-python",
            "text/plain",
            "application/octet-stream",
        ]
        assert data["some"].filename == fname.name
        with fname.open("rb") as f:
            assert data["some"].file.read() == f.read()
            data["some"].file.close()

        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        async with client.post("/", data={"test": "true", "some": f}) as resp:
            assert 200 == resp.status


async def test_POST_STREAM_DATA(ezyhttp_client: Any, fname: Any) -> None:
    async def handler(request):
        assert request.content_type == "application/octet-stream"
        content = await request.read()
        with fname.open("rb") as f:
            expected = f.read()
            assert request.content_length == len(expected)
            assert content == expected

        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    with fname.open("rb") as f:
        data_size = len(f.read())

    async def gen(fname):
        with fname.open("rb") as f:
            data = f.read(100)
            while data:
                yield data
                data = f.read(100)

    async with client.post(
        "/", data=gen(fname), headers={"Content-Length": str(data_size)}
    ) as resp:
        assert 200 == resp.status


async def test_json(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert request.content_type == "application/json"
        data = await request.json()
        return web.Response(body=ezyhttp.JsonPayload(data))

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.post("/", json={"some": "data"})
    assert 200 == resp.status
    content = await resp.json()
    assert content == {"some": "data"}
    resp.close()

    with pytest.raises(ValueError):
        await client.post("/", data="some data", json={"some": "data"})


async def test_json_custom(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert request.content_type == "application/json"
        data = await request.json()
        return web.Response(body=ezyhttp.JsonPayload(data))

    used = False

    def dumps(obj):
        nonlocal used
        used = True
        return json.dumps(obj)

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app, json_serialize=dumps)

    resp = await client.post("/", json={"some": "data"})
    assert 200 == resp.status
    assert used
    content = await resp.json()
    assert content == {"some": "data"}
    resp.close()

    with pytest.raises(ValueError):
        await client.post("/", data="some data", json={"some": "data"})


async def test_expect_continue(ezyhttp_client: Any) -> None:
    expect_called = False

    async def handler(request):
        data = await request.post()
        assert data == {"some": "data"}
        return web.Response()

    async def expect_handler(request):
        nonlocal expect_called
        expect = request.headers.get(hdrs.EXPECT)
        if expect.lower() == "100-continue":
            request.transport.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            expect_called = True

    app = web.Application()
    app.router.add_post("/", handler, expect_handler=expect_handler)
    client = await ezyhttp_client(app)

    async with client.post("/", data={"some": "data"}, expect100=True) as resp:
        assert 200 == resp.status
    assert expect_called


async def test_encoding_deflate(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.enable_chunked_encoding()
        resp.enable_compression(web.ContentCoding.deflate)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "text"
    resp.close()


async def test_encoding_deflate_nochunk(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.enable_compression(web.ContentCoding.deflate)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "text"
    resp.close()


async def test_encoding_gzip(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.enable_chunked_encoding()
        resp.enable_compression(web.ContentCoding.gzip)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "text"
    resp.close()


async def test_encoding_gzip_write_by_chunks(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse()
        resp.enable_compression(web.ContentCoding.gzip)
        await resp.prepare(request)
        await resp.write(b"0")
        await resp.write(b"0")
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "00"
    resp.close()


async def test_encoding_gzip_nochunk(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.enable_compression(web.ContentCoding.gzip)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    txt = await resp.text()
    assert txt == "text"
    resp.close()


async def test_bad_payload_compression(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.headers["Content-Encoding"] = "gzip"
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status

    with pytest.raises(ezyhttp.ClientPayloadError):
        await resp.read()

    resp.close()


async def test_bad_payload_chunked_encoding(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse()
        resp.force_close()
        resp._length_check = False
        resp.headers["Transfer-Encoding"] = "chunked"
        writer = await resp.prepare(request)
        await writer.write(b"9\r\n\r\n")
        await writer.write_eof()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status

    with pytest.raises(ezyhttp.ClientPayloadError):
        await resp.read()

    resp.close()


async def test_no_payload_304_with_chunked_encoding(ezyhttp_client: Any) -> None:
    """Test a 304 response with no payload with chunked set should have it removed."""

    async def handler(request):
        resp = web.StreamResponse(status=304)
        resp.enable_chunked_encoding()
        resp._length_check = False
        resp.headers["Transfer-Encoding"] = "chunked"
        writer = await resp.prepare(request)
        await writer.write_eof()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert resp.status == 304
    assert hdrs.CONTENT_LENGTH not in resp.headers
    assert hdrs.TRANSFER_ENCODING not in resp.headers
    await resp.read()

    resp.close()


async def test_head_request_with_chunked_encoding(ezyhttp_client: Any) -> None:
    """Test a head response with chunked set should have it removed."""

    async def handler(request):
        resp = web.StreamResponse(status=200)
        resp.enable_chunked_encoding()
        resp._length_check = False
        resp.headers["Transfer-Encoding"] = "chunked"
        writer = await resp.prepare(request)
        await writer.write_eof()
        return resp

    app = web.Application()
    app.router.add_head("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.head("/")
    assert resp.status == 200
    assert hdrs.CONTENT_LENGTH not in resp.headers
    assert hdrs.TRANSFER_ENCODING not in resp.headers
    await resp.read()

    resp.close()


async def test_no_payload_200_with_chunked_encoding(ezyhttp_client: Any) -> None:
    """Test chunked is preserved on a 200 response with no payload."""

    async def handler(request):
        resp = web.StreamResponse(status=200)
        resp.enable_chunked_encoding()
        resp._length_check = False
        resp.headers["Transfer-Encoding"] = "chunked"
        writer = await resp.prepare(request)
        await writer.write_eof()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert resp.status == 200
    assert hdrs.CONTENT_LENGTH not in resp.headers
    assert hdrs.TRANSFER_ENCODING in resp.headers
    await resp.read()

    resp.close()


async def test_bad_payload_content_length(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.headers["Content-Length"] = "10000"
        resp.force_close()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status

    with pytest.raises(ezyhttp.ClientPayloadError):
        await resp.read()

    resp.close()


async def test_payload_content_length_by_chunks(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse(headers={"content-length": "2"})
        await resp.prepare(request)
        await resp.write(b"answer")
        await resp.write(b"two")
        request.transport.close()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    data = await resp.read()
    assert data == b"an"
    resp.close()


async def test_chunked(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.Response(text="text")
        resp.enable_chunked_encoding()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    assert 200 == resp.status
    assert resp.headers["Transfer-Encoding"] == "chunked"
    txt = await resp.text()
    assert txt == "text"
    resp.close()


async def test_shortcuts(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    app = web.Application()
    for meth in ("get", "post", "put", "delete", "head", "patch", "options"):
        app.router.add_route(meth.upper(), "/", handler)
    client = await ezyhttp_client(app)

    for meth in ("get", "post", "put", "delete", "head", "patch", "options"):
        coro = getattr(client.session, meth)
        resp = await coro(client.make_url("/"))

        assert resp.status == 200
        assert len(resp.history) == 0

        content1 = await resp.read()
        content2 = await resp.read()
        assert content1 == content2
        content = await resp.text()

        if meth == "head":
            assert b"" == content1
        else:
            assert meth.upper() == content


async def test_cookies(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert request.cookies.keys() == {"test1", "test3"}
        assert request.cookies["test1"] == "123"
        assert request.cookies["test3"] == "456"
        return web.Response()

    c = http.cookies.Morsel()
    c.set("test3", "456", "456")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app, cookies={"test1": "123", "test2": c})

    async with client.get("/") as resp:
        assert 200 == resp.status


async def test_cookies_per_request(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert request.cookies.keys() == {"test1", "test3", "test4", "test6"}
        assert request.cookies["test1"] == "123"
        assert request.cookies["test3"] == "456"
        assert request.cookies["test4"] == "789"
        assert request.cookies["test6"] == "abc"
        return web.Response()

    c = http.cookies.Morsel()
    c.set("test3", "456", "456")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app, cookies={"test1": "123", "test2": c})

    rc = http.cookies.Morsel()
    rc.set("test6", "abc", "abc")

    async with client.get("/", cookies={"test4": "789", "test5": rc}) as resp:
        assert 200 == resp.status


async def test_cookies_redirect(ezyhttp_client: Any) -> None:
    async def redirect1(request):
        ret = web.Response(status=301, headers={"Location": "/redirect2"})
        ret.set_cookie("c", "1")
        return ret

    async def redirect2(request):
        ret = web.Response(status=301, headers={"Location": "/"})
        ret.set_cookie("c", "2")
        return ret

    async def handler(request):
        assert request.cookies.keys() == {"c"}
        assert request.cookies["c"] == "2"
        return web.Response()

    app = web.Application()
    app.router.add_get("/redirect1", redirect1)
    app.router.add_get("/redirect2", redirect2)
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app)
    async with client.get("/redirect1") as resp:
        assert 200 == resp.status


async def test_cookies_on_empty_session_jar(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert "custom-cookie" in request.cookies
        assert request.cookies["custom-cookie"] == "abc"
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app, cookies=None)

    async with client.get("/", cookies={"custom-cookie": "abc"}) as resp:
        assert 200 == resp.status


async def test_morsel_with_attributes(ezyhttp_client: Any) -> None:
    # A comment from original test:
    #
    # No cookie attribute should pass here
    # they are only used as filters
    # whether to send particular cookie or not.
    # E.g. if cookie expires it just becomes thrown away.
    # Server who sent the cookie with some attributes
    # already knows them, no need to send this back again and again

    async def handler(request):
        assert request.cookies.keys() == {"test3"}
        assert request.cookies["test3"] == "456"
        return web.Response()

    c = http.cookies.Morsel()
    c.set("test3", "456", "456")
    c["httponly"] = True
    c["secure"] = True
    c["max-age"] = 1000

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app, cookies={"test2": c})

    async with client.get("/") as resp:
        assert 200 == resp.status


async def test_set_cookies(ezyhttp_client: Any) -> None:
    async def handler(request):
        ret = web.Response()
        ret.set_cookie("c1", "cookie1")
        ret.set_cookie("c2", "cookie2")
        ret.headers.add(
            "Set-Cookie",
            "ISAWPLB{A7F52349-3531-4DA9-8776-F74BC6F4F1BB}="
            "{925EC0B8-CB17-4BEB-8A35-1033813B0523}; "
            "HttpOnly; Path=/",
        )
        return ret

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    with mock.patch("ezyhttp.client_reqrep.client_logger") as m_log:
        async with client.get("/") as resp:
            assert 200 == resp.status
            cookie_names = {c.key for c in client.session.cookie_jar}
        assert cookie_names == {"c1", "c2"}

        m_log.warning.assert_called_with("Can not load response cookies: %s", mock.ANY)


async def test_set_cookies_expired(ezyhttp_client: Any) -> None:
    async def handler(request):
        ret = web.Response()
        ret.set_cookie("c1", "cookie1")
        ret.set_cookie("c2", "cookie2")
        ret.headers.add(
            "Set-Cookie",
            "c3=cookie3; " "HttpOnly; Path=/" " Expires=Tue, 1 Jan 1980 12:00:00 GMT; ",
        )
        return ret

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert 200 == resp.status
        cookie_names = {c.key for c in client.session.cookie_jar}
    assert cookie_names == {"c1", "c2"}


async def test_set_cookies_max_age(ezyhttp_client: Any) -> None:
    async def handler(request):
        ret = web.Response()
        ret.set_cookie("c1", "cookie1")
        ret.set_cookie("c2", "cookie2")
        ret.headers.add("Set-Cookie", "c3=cookie3; " "HttpOnly; Path=/" " Max-Age=1; ")
        return ret

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert 200 == resp.status
        cookie_names = {c.key for c in client.session.cookie_jar}
        assert cookie_names == {"c1", "c2", "c3"}
        await asyncio.sleep(2)
        cookie_names = {c.key for c in client.session.cookie_jar}
        assert cookie_names == {"c1", "c2"}


async def test_set_cookies_max_age_overflow(ezyhttp_client: Any) -> None:
    async def handler(request):
        ret = web.Response()
        ret.headers.add(
            "Set-Cookie",
            "overflow=overflow; " "HttpOnly; Path=/" " Max-Age=" + str(overflow) + "; ",
        )
        return ret

    overflow = int(
        datetime.datetime.max.replace(tzinfo=datetime.timezone.utc).timestamp()
    )
    empty = None
    try:
        empty = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=overflow
        )
    except OverflowError as ex:
        assert isinstance(ex, OverflowError)
    assert not isinstance(empty, datetime.datetime)
    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert 200 == resp.status
        for cookie in client.session.cookie_jar:
            if cookie.key == "overflow":
                assert int(cookie["max-age"]) == int(overflow)


async def test_request_conn_error() -> None:
    client = ezyhttp.ClientSession()
    with pytest.raises(ezyhttp.ClientConnectionError):
        await client.get("http://0.0.0.0:1")
    await client.close()


@pytest.mark.xfail
async def test_broken_connection(ezyhttp_client: Any) -> None:
    async def handler(request):
        request.transport.close()
        return web.Response(text="answer" * 1000)

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    with pytest.raises(ezyhttp.ClientResponseError):
        await client.get("/")


async def test_broken_connection_2(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse(headers={"content-length": "1000"})
        await resp.prepare(request)
        await resp.write(b"answer")
        request.transport.close()
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    client = await ezyhttp_client(app)

    resp = await client.get("/")
    with pytest.raises(ezyhttp.ClientPayloadError):
        await resp.read()
    resp.close()


async def test_custom_headers(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert request.headers["x-api-key"] == "foo"
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)
    client = await ezyhttp_client(app)

    async with client.post(
        "/", headers={"Content-Type": "application/json", "x-api-key": "foo"}
    ) as resp:
        assert resp.status == 200


async def test_redirect_to_absolute_url(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(text=request.method)

    async def redirect(request):
        raise web.HTTPFound(location=client.make_url("/"))

    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get("/redirect", redirect)

    client = await ezyhttp_client(app)
    async with client.get("/redirect") as resp:
        assert 200 == resp.status


async def test_redirect_without_location_header(ezyhttp_client: Any) -> None:
    body = b"redirect"

    async def handler_redirect(request):
        return web.Response(status=301, body=body)

    app = web.Application()
    app.router.add_route("GET", "/redirect", handler_redirect)
    client = await ezyhttp_client(app)

    resp = await client.get("/redirect")
    data = await resp.read()
    assert data == body


@pytest.mark.parametrize(
    ("status", "expected_ok"),
    (
        (200, True),
        (201, True),
        (301, True),
        (400, False),
        (403, False),
        (500, False),
    ),
)
async def test_ok_from_status(
    ezyhttp_client: Any, status: Any, expected_ok: Any
) -> None:
    async def handler(request):
        return web.Response(status=status, body=b"")

    app = web.Application()
    app.router.add_route("GET", "/endpoint", handler)
    client = await ezyhttp_client(app, raise_for_status=False)
    async with client.get("/endpoint") as resp:
        assert resp.ok is expected_ok


async def test_raise_for_status(ezyhttp_client: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app, raise_for_status=True)

    with pytest.raises(ezyhttp.ClientResponseError):
        await client.get("/")


async def test_raise_for_status_per_request(ezyhttp_client: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app)

    with pytest.raises(ezyhttp.ClientResponseError):
        await client.get("/", raise_for_status=True)


async def test_raise_for_status_disable_per_request(ezyhttp_client: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_route("GET", "/", handler)
    client = await ezyhttp_client(app, raise_for_status=True)

    async with client.get("/", raise_for_status=False) as resp:
        assert 400 == resp.status


async def test_request_raise_for_status_default(ezyhttp_server: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    async with ezyhttp.request("GET", server.make_url("/")) as resp:
        assert resp.status == 400


async def test_request_raise_for_status_disabled(ezyhttp_server: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)
    url = server.make_url("/")

    async with ezyhttp.request("GET", url, raise_for_status=False) as resp:
        assert resp.status == 400


async def test_request_raise_for_status_enabled(ezyhttp_server: Any) -> None:
    async def handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)
    url = server.make_url("/")

    with pytest.raises(ezyhttp.ClientResponseError):
        async with ezyhttp.request("GET", url, raise_for_status=True):
            assert False, "never executed"  # pragma: no cover


async def test_session_raise_for_status_coro(ezyhttp_client: Any) -> None:
    async def handle(request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_route("GET", "/", handle)

    raise_for_status_called = 0

    async def custom_r4s(response):
        nonlocal raise_for_status_called
        raise_for_status_called += 1
        assert response.status == 200
        assert response.request_info.method == "GET"

    client = await ezyhttp_client(app, raise_for_status=custom_r4s)
    await client.get("/")
    assert raise_for_status_called == 1
    await client.get("/", raise_for_status=True)
    assert raise_for_status_called == 1  # custom_r4s not called again
    await client.get("/", raise_for_status=False)
    assert raise_for_status_called == 1  # custom_r4s not called again


async def test_request_raise_for_status_coro(ezyhttp_client: Any) -> None:
    async def handle(request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_route("GET", "/", handle)

    raise_for_status_called = 0

    async def custom_r4s(response):
        nonlocal raise_for_status_called
        raise_for_status_called += 1
        assert response.status == 200
        assert response.request_info.method == "GET"

    client = await ezyhttp_client(app)
    await client.get("/", raise_for_status=custom_r4s)
    assert raise_for_status_called == 1
    await client.get("/", raise_for_status=True)
    assert raise_for_status_called == 1  # custom_r4s not called again
    await client.get("/", raise_for_status=False)
    assert raise_for_status_called == 1  # custom_r4s not called again


async def test_invalid_idna() -> None:
    session = ezyhttp.ClientSession()
    try:
        with pytest.raises(ezyhttp.InvalidURL):
            await session.get("http://\u2061owhefopw.com")
    finally:
        await session.close()


async def test_creds_in_auth_and_url() -> None:
    session = ezyhttp.ClientSession()
    try:
        with pytest.raises(ValueError):
            await session.get(
                "http://user:pass@example.com", auth=ezyhttp.BasicAuth("user2", "pass2")
            )
    finally:
        await session.close()


@pytest.fixture
def create_server_for_url_and_handler(
    ezyhttp_server: Any, tls_certificate_authority: Any
):
    def create(url: URL, srv: Any):
        app = web.Application()
        app.router.add_route("GET", url.path, srv)

        kwargs = {}
        if url.scheme == "https":
            cert = tls_certificate_authority.issue_cert(
                url.host, "localhost", "127.0.0.1"
            )
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            cert.configure_cert(ssl_ctx)
            kwargs["ssl"] = ssl_ctx
        return ezyhttp_server(app, **kwargs)

    return create


@pytest.mark.parametrize(
    ["url_from", "url_to", "is_drop_header_expected"],
    [
        [
            "http://host1.com/path1",
            "http://host2.com/path2",
            True,
        ],
        ["http://host1.com/path1", "https://host1.com/path1", False],
        ["https://host1.com/path1", "http://host1.com/path2", True],
    ],
    ids=(
        "entirely different hosts",
        "http -> https",
        "https -> http",
    ),
)
async def test_drop_auth_on_redirect_to_other_host(
    create_server_for_url_and_handler: Any,
    url_from: str,
    url_to: str,
    is_drop_header_expected: bool,
) -> None:
    url_from, url_to = URL(url_from), URL(url_to)

    async def srv_from(request):
        assert request.host == url_from.host
        assert request.headers["Authorization"] == "Basic dXNlcjpwYXNz"
        raise web.HTTPFound(url_to)

    async def srv_to(request):
        assert request.host == url_to.host
        if is_drop_header_expected:
            assert "Authorization" not in request.headers, "Header wasn't dropped"
        else:
            assert "Authorization" in request.headers, "Header was dropped"
        return web.Response()

    server_from = await create_server_for_url_and_handler(url_from, srv_from)
    server_to = await create_server_for_url_and_handler(url_to, srv_to)

    assert (
        url_from.host != url_to.host or server_from.scheme != server_to.scheme
    ), "Invalid test case, host or scheme must differ"

    protocol_port_map = {
        "http": 80,
        "https": 443,
    }
    etc_hosts = {
        (url_from.host, protocol_port_map[server_from.scheme]): server_from,
        (url_to.host, protocol_port_map[server_to.scheme]): server_to,
    }

    class FakeResolver(AbstractResolver):
        async def resolve(self, host, port=0, family=socket.AF_INET):
            server = etc_hosts[(host, port)]

            return [
                {
                    "hostname": host,
                    "host": server.host,
                    "port": server.port,
                    "family": socket.AF_INET,
                    "proto": 0,
                    "flags": socket.AI_NUMERICHOST,
                }
            ]

        async def close(self):
            pass

    connector = ezyhttp.TCPConnector(resolver=FakeResolver(), ssl=False)

    async with ezyhttp.ClientSession(connector=connector) as client:
        resp = await client.get(
            url_from,
            auth=ezyhttp.BasicAuth("user", "pass"),
        )
        assert resp.status == 200
        resp = await client.get(
            url_from,
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status == 200


async def test_async_with_session() -> None:
    async with ezyhttp.ClientSession() as session:
        pass

    assert session.closed


async def test_session_close_awaitable() -> None:
    session = ezyhttp.ClientSession()
    await session.close()

    assert session.closed


async def test_close_resp_on_error_async_with_session(ezyhttp_server: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse(headers={"content-length": "100"})
        await resp.prepare(request)
        await asyncio.sleep(0.1)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    async with ezyhttp.ClientSession() as session:
        with pytest.raises(RuntimeError):
            async with session.get(server.make_url("/")) as resp:
                resp.content.set_exception(RuntimeError())
                await resp.read()

        assert len(session._connector._conns) == 0


async def test_release_resp_on_normal_exit_from_cm(ezyhttp_server: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    async with ezyhttp.ClientSession() as session:
        async with session.get(server.make_url("/")) as resp:
            await resp.read()

        assert len(session._connector._conns) == 1


async def test_non_close_detached_session_on_error_cm(ezyhttp_server: Any) -> None:
    async def handler(request):
        resp = web.StreamResponse(headers={"content-length": "100"})
        await resp.prepare(request)
        await asyncio.sleep(0.1)
        return resp

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    session = ezyhttp.ClientSession()
    cm = session.get(server.make_url("/"))
    assert not session.closed
    with pytest.raises(RuntimeError):
        async with cm as resp:
            resp.content.set_exception(RuntimeError())
            await resp.read()
    assert not session.closed


async def test_close_detached_session_on_non_existing_addr() -> None:
    class FakeResolver(AbstractResolver):
        async def resolve(host, port=0, family=socket.AF_INET):
            return {}

        async def close(self):
            pass

    connector = ezyhttp.TCPConnector(resolver=FakeResolver())

    session = ezyhttp.ClientSession(connector=connector)

    async with session:
        cm = session.get("http://non-existing.example.com")
        assert not session.closed
        with pytest.raises(Exception):
            await cm

    assert session.closed


async def test_ezyhttp_request_context_manager(ezyhttp_server: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    async with ezyhttp.request("GET", server.make_url("/")) as resp:
        await resp.read()
        assert resp.status == 200


async def test_ezyhttp_request_ctx_manager_close_sess_on_error(
    ssl_ctx: Any, ezyhttp_server: Any
) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app, ssl=ssl_ctx)

    cm = ezyhttp.request("GET", server.make_url("/"))

    with pytest.raises(ezyhttp.ClientConnectionError):
        async with cm:
            pass

    assert cm._session.closed


async def test_ezyhttp_request_ctx_manager_not_found() -> None:
    with pytest.raises(ezyhttp.ClientConnectionError):
        async with ezyhttp.request("GET", "http://wrong-dns-name.com"):
            assert False, "never executed"  # pragma: no cover


async def test_ezyhttp_request_coroutine(ezyhttp_server: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await ezyhttp_server(app)

    not_an_awaitable = ezyhttp.request("GET", server.make_url("/"))
    with pytest.raises(
        TypeError,
        match="^object _SessionRequestContextManager "
        "can't be used in 'await' expression$",
    ):
        await not_an_awaitable

    await not_an_awaitable._coro  # coroutine 'ClientSession._request' was never awaited
    await server.close()


async def test_yield_from_in_session_request(ezyhttp_client: Any) -> None:
    # a test for backward compatibility with yield from syntax
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app)
    async with client.get("/") as resp:
        assert resp.status == 200


async def test_close_context_manager(ezyhttp_client: Any) -> None:
    # a test for backward compatibility with yield from syntax
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app)
    ctx = client.get("/")
    ctx.close()
    assert not ctx._coro.cr_running


async def test_session_auth(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.json_response({"headers": dict(request.headers)})

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app, auth=ezyhttp.BasicAuth("login", "pass"))

    r = await client.get("/")
    assert r.status == 200
    content = await r.json()
    assert content["headers"]["Authorization"] == "Basic bG9naW46cGFzcw=="


async def test_session_auth_override(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.json_response({"headers": dict(request.headers)})

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app, auth=ezyhttp.BasicAuth("login", "pass"))

    r = await client.get("/", auth=ezyhttp.BasicAuth("other_login", "pass"))
    assert r.status == 200
    content = await r.json()
    val = content["headers"]["Authorization"]
    assert val == "Basic b3RoZXJfbG9naW46cGFzcw=="


async def test_session_auth_header_conflict(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app, auth=ezyhttp.BasicAuth("login", "pass"))
    headers = {"Authorization": "Basic b3RoZXJfbG9naW46cGFzcw=="}
    with pytest.raises(ValueError):
        await client.get("/", headers=headers)


async def test_session_headers(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.json_response({"headers": dict(request.headers)})

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app, headers={"X-Real-IP": "192.168.0.1"})

    r = await client.get("/")
    assert r.status == 200
    content = await r.json()
    assert content["headers"]["X-Real-IP"] == "192.168.0.1"


async def test_session_headers_merge(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.json_response({"headers": dict(request.headers)})

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(
        app, headers=[("X-Real-IP", "192.168.0.1"), ("X-Sent-By", "requests")]
    )

    r = await client.get("/", headers={"X-Sent-By": "ezyhttp"})
    assert r.status == 200
    content = await r.json()
    assert content["headers"]["X-Real-IP"] == "192.168.0.1"
    assert content["headers"]["X-Sent-By"] == "ezyhttp"


async def test_multidict_headers(ezyhttp_client: Any) -> None:
    async def handler(request):
        assert await request.read() == data
        return web.Response()

    app = web.Application()
    app.router.add_post("/", handler)

    client = await ezyhttp_client(app)

    data = b"sample data"

    async with client.post(
        "/", data=data, headers=MultiDict({"Content-Length": str(len(data))})
    ) as r:
        assert r.status == 200


async def test_request_conn_closed(ezyhttp_client: Any) -> None:
    async def handler(request):
        request.transport.close()
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app)
    with pytest.raises(ezyhttp.ServerDisconnectedError) as excinfo:
        resp = await client.get("/")
        await resp.read()

    assert str(excinfo.value) != ""


async def test_dont_close_explicit_connector(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_get("/", handler)

    client = await ezyhttp_client(app)
    r = await client.get("/")
    await r.read()

    assert 1 == len(client.session.connector._conns)


async def test_server_close_keepalive_connection() -> None:
    loop = asyncio.get_event_loop()

    class Proto(asyncio.Protocol):
        def connection_made(self, transport):
            self.transp = transport
            self.data = b""

        def data_received(self, data):
            self.data += data
            if data.endswith(b"\r\n\r\n"):
                self.transp.write(
                    b"HTTP/1.1 200 OK\r\n"
                    b"CONTENT-LENGTH: 2\r\n"
                    b"CONNECTION: close\r\n"
                    b"\r\n"
                    b"ok"
                )
                self.transp.close()

        def connection_lost(self, exc):
            self.transp = None

    server = await loop.create_server(Proto, "127.0.0.1", unused_port())

    addr = server.sockets[0].getsockname()

    connector = ezyhttp.TCPConnector(limit=1)
    session = ezyhttp.ClientSession(connector=connector)

    url = "http://{}:{}/".format(*addr)
    for i in range(2):
        r = await session.request("GET", url)
        await r.read()
        assert 0 == len(connector._conns)
    await session.close()
    await connector.close()
    server.close()
    await server.wait_closed()


async def test_handle_keepalive_on_closed_connection() -> None:
    loop = asyncio.get_event_loop()

    class Proto(asyncio.Protocol):
        def connection_made(self, transport):
            self.transp = transport
            self.data = b""

        def data_received(self, data):
            self.data += data
            if data.endswith(b"\r\n\r\n"):
                self.transp.write(
                    b"HTTP/1.1 200 OK\r\n" b"CONTENT-LENGTH: 2\r\n" b"\r\n" b"ok"
                )
                self.transp.close()

        def connection_lost(self, exc):
            self.transp = None

    server = await loop.create_server(Proto, "127.0.0.1", unused_port())

    addr = server.sockets[0].getsockname()

    connector = ezyhttp.TCPConnector(limit=1)
    session = ezyhttp.ClientSession(connector=connector)

    url = "http://{}:{}/".format(*addr)

    r = await session.request("GET", url)
    await r.read()
    assert 1 == len(connector._conns)

    with pytest.raises(ezyhttp.ClientConnectionError):
        await session.request("GET", url)
    assert 0 == len(connector._conns)

    await session.close()
    await connector.close()
    server.close()
    await server.wait_closed()


async def test_error_in_performing_request(
    ssl_ctx: Any, ezyhttp_client: Any, ezyhttp_server: Any
):
    async def handler(request):
        return web.Response()

    def exception_handler(loop, context):
        # skip log messages about destroyed but pending tasks
        pass

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    server = await ezyhttp_server(app, ssl=ssl_ctx)

    conn = ezyhttp.TCPConnector(limit=1)
    client = await ezyhttp_client(server, connector=conn)

    with pytest.raises(ezyhttp.ClientConnectionError):
        await client.get("/")

    # second try should not hang
    with pytest.raises(ezyhttp.ClientConnectionError):
        await client.get("/")


async def test_await_after_cancelling(ezyhttp_client: Any) -> None:
    loop = asyncio.get_event_loop()

    async def handler(request):
        return web.Response()

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    client = await ezyhttp_client(app)

    fut1 = loop.create_future()
    fut2 = loop.create_future()

    async def fetch1():
        resp = await client.get("/")
        assert resp.status == 200
        fut1.set_result(None)
        with pytest.raises(asyncio.CancelledError):
            await fut2
        resp.release()

    async def fetch2():
        await fut1
        resp = await client.get("/")
        assert resp.status == 200

    async def canceller():
        await fut1
        fut2.cancel()

    await asyncio.gather(fetch1(), fetch2(), canceller())


async def test_async_payload_generator(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.read()
        assert data == b"1234567890" * 100
        return web.Response()

    app = web.Application()
    app.add_routes([web.post("/", handler)])

    client = await ezyhttp_client(app)

    async def gen():
        for i in range(100):
            yield b"1234567890"

    async with client.post("/", data=gen()) as resp:
        assert resp.status == 200


async def test_read_from_closed_response(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"data")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert resp.status == 200

    with pytest.raises(ezyhttp.ClientConnectionError):
        await resp.read()


async def test_read_from_closed_response2(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"data")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert resp.status == 200
        await resp.read()

    with pytest.raises(ezyhttp.ClientConnectionError):
        await resp.read()


async def test_read_from_closed_content(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"data")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with client.get("/") as resp:
        assert resp.status == 200

    with pytest.raises(ezyhttp.ClientConnectionError):
        await resp.content.readline()


async def test_read_timeout(ezyhttp_client: Any) -> None:
    async def handler(request):
        await asyncio.sleep(5)
        return web.Response()

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    timeout = ezyhttp.ClientTimeout(sock_read=0.1)
    client = await ezyhttp_client(app, timeout=timeout)

    with pytest.raises(ezyhttp.ServerTimeoutError):
        await client.get("/")


async def test_socket_timeout(ezyhttp_client: Any) -> None:
    async def handler(request):
        await asyncio.sleep(5)
        return web.Response()

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    timeout = ezyhttp.ClientTimeout(sock_read=0.1)
    client = await ezyhttp_client(app, timeout=timeout)

    with pytest.raises(SocketTimeoutError):
        await client.get("/")


async def test_read_timeout_closes_connection(ezyhttp_client: ezyhttpClient) -> None:
    request_count = 0

    async def handler(request):
        nonlocal request_count
        request_count += 1
        if request_count < 3:
            await asyncio.sleep(0.5)
        return web.Response(body=f"request:{request_count}")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    timeout = ezyhttp.ClientTimeout(total=0.1)
    client: TestClient = await ezyhttp_client(app, timeout=timeout)
    with pytest.raises(asyncio.TimeoutError):
        await client.get("/")

    # Make sure its really closed
    assert not client.session.connector._conns

    with pytest.raises(asyncio.TimeoutError):
        await client.get("/")

    # Make sure its really closed
    assert not client.session.connector._conns
    result = await client.get("/")
    assert await result.read() == b"request:3"

    # Make sure its not closed
    assert client.session.connector._conns


async def test_read_timeout_on_prepared_response(ezyhttp_client: Any) -> None:
    async def handler(request):
        resp = ezyhttp.web.StreamResponse()
        await resp.prepare(request)
        await asyncio.sleep(5)
        await resp.drain()
        return resp

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    timeout = ezyhttp.ClientTimeout(sock_read=0.1)
    client = await ezyhttp_client(app, timeout=timeout)

    with pytest.raises(ezyhttp.ServerTimeoutError):
        async with await client.get("/") as resp:
            await resp.read()


async def test_timeout_with_full_buffer(ezyhttp_client: Any) -> None:
    async def handler(request):
        """Server response that never ends and always has more data available."""
        resp = web.StreamResponse()
        await resp.prepare(request)
        while True:
            await resp.write(b"1" * 1000)
            await asyncio.sleep(0.01)

    async def request(client):
        timeout = ezyhttp.ClientTimeout(total=0.5)
        async with await client.get("/", timeout=timeout) as resp:
            with pytest.raises(asyncio.TimeoutError):
                async for data in resp.content.iter_chunked(1):
                    await asyncio.sleep(0.01)

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)
    # wait_for() used just to ensure that a failing test doesn't hang.
    await asyncio.wait_for(request(client), 1)


async def test_read_bufsize_session_default(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"1234567")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app, read_bufsize=2)

    async with await client.get("/") as resp:
        assert resp.content.get_read_buffer_limits() == (2, 4)


async def test_read_bufsize_explicit(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(body=b"1234567")

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.get("/", read_bufsize=4) as resp:
        assert resp.content.get_read_buffer_limits() == (4, 8)


async def test_http_empty_data_text(ezyhttp_client: Any) -> None:
    async def handler(request):
        data = await request.read()
        ret = "ok" if data == b"" else "fail"
        resp = web.Response(text=ret)
        resp.headers["Content-Type"] = request.headers["Content-Type"]
        return resp

    app = web.Application()
    app.add_routes([web.post("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.post("/", data="") as resp:
        assert resp.status == 200
        assert await resp.text() == "ok"
        assert resp.headers["Content-Type"] == "text/plain; charset=utf-8"


async def test_max_field_size_session_default(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(headers={"Custom": "x" * 8190})

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.get("/") as resp:
        assert resp.headers["Custom"] == "x" * 8190


async def test_max_field_size_session_default_fail(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(headers={"Custom": "x" * 8191})

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)
    with pytest.raises(ezyhttp.ClientResponseError):
        await client.get("/")


async def test_max_field_size_session_explicit(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(headers={"Custom": "x" * 8191})

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app, max_field_size=8191)

    async with await client.get("/") as resp:
        assert resp.headers["Custom"] == "x" * 8191


async def test_max_field_size_request_explicit(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(headers={"Custom": "x" * 8191})

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.get("/", max_field_size=8191) as resp:
        assert resp.headers["Custom"] == "x" * 8191


async def test_max_line_size_session_default(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(status=200, reason="x" * 8190)

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.get("/") as resp:
        assert resp.reason == "x" * 8190


async def test_max_line_size_session_default_fail(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(status=200, reason="x" * 8192)

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)
    with pytest.raises(ezyhttp.ClientResponseError):
        await client.get("/")


async def test_max_line_size_session_explicit(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(status=200, reason="x" * 8191)

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app, max_line_size=8191)

    async with await client.get("/") as resp:
        assert resp.reason == "x" * 8191


async def test_max_line_size_request_explicit(ezyhttp_client: Any) -> None:
    async def handler(request):
        return web.Response(status=200, reason="x" * 8191)

    app = web.Application()
    app.add_routes([web.get("/", handler)])

    client = await ezyhttp_client(app)

    async with await client.get("/", max_line_size=8191) as resp:
        assert resp.reason == "x" * 8191


@pytest.mark.xfail(raises=asyncio.TimeoutError, reason="#7599")
async def test_rejected_upload(ezyhttp_client: Any, tmp_path: Any) -> None:
    async def ok_handler(request):
        return web.Response()

    async def not_ok_handler(request):
        raise web.HTTPBadRequest()

    app = web.Application()
    app.router.add_get("/ok", ok_handler)
    app.router.add_post("/not_ok", not_ok_handler)
    client = await ezyhttp_client(app)

    file_size_bytes = 1024 * 1024
    file_path = tmp_path / "uploaded.txt"
    file_path.write_text("0" * file_size_bytes, encoding="utf8")

    with open(file_path, "rb") as file:
        data = {"file": file}
        async with await client.post("/not_ok", data=data) as resp_not_ok:
            assert 400 == resp_not_ok.status

    async with await client.get(
        "/ok", timeout=ezyhttp.ClientTimeout(total=0.01)
    ) as resp_ok:
        assert 200 == resp_ok.status
