#!/usr/bin/env python3
import asyncio

import ezyhttp


async def fetch(session: ezyhttp.ClientSession) -> None:
    print("Query http://httpbin.org/basic-auth/andrew/password")
    async with session.get("http://httpbin.org/basic-auth/andrew/password") as resp:
        print(resp.status)
        body = await resp.text()
        print(body)


async def go() -> None:
    async with ezyhttp.ClientSession(
        auth=ezyhttp.BasicAuth("andrew", "password")
    ) as session:
        await fetch(session)


loop = asyncio.get_event_loop()
loop.run_until_complete(go())
