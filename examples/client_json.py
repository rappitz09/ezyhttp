#!/usr/bin/env python3
import asyncio

import ezyhttp


async def fetch(session: ezyhttp.ClientSession) -> None:
    print("Query http://httpbin.org/get")
    async with session.get("http://httpbin.org/get") as resp:
        print(resp.status)
        data = await resp.json()
        print(data)


async def go() -> None:
    async with ezyhttp.ClientSession() as session:
        await fetch(session)


loop = asyncio.get_event_loop()
loop.run_until_complete(go())
loop.close()
