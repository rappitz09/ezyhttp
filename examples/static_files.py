#!/usr/bin/env python3
import pathlib

from ezyhttp import web

app = web.Application()
app.router.add_static("/", pathlib.Path(__file__).parent, show_index=True)

web.run_app(app)
