==================================
Async http client/server framework
==================================

.. image:: https://raw.githubusercontent.com/rappitz09/ezyhttp/master/docs/ezyhttp-plain.svg
  :height: 64px
  :width: 64px
  :alt: ezyhttp logo

|

.. image:: https://github.com/rappitz09/ezyhttp/workflows/CI/badge.svg
  :target: https://github.com/rappitz09/ezyhttp/actions?query=workflow%3ACI
  :alt: GitHub Actions status for master branch

.. image:: https://codecov.io/gh/rappitz09/ezyhttp/branch/master/graph/badge.svg
  :target: https://github.com/rappitz09/ezyhttp
  :alt: codecov.io status for master branch

.. image:: https://badge.fury.io/py/ezyhttp.svg
  :target: https://pypi.org/project/ezyhttp
  :alt: Latest PyPI package version

.. image:: https://img.shields.io/pypi/dm/ezyhttp
  :target: https://pypistats.org/packages/ezyhttp
  :alt: Downloads count

.. image:: https://readthedocs.org/projects/ezyhttp/badge/?version=latest
  :target: https://ezyhttp.readthedocs.io/
  :alt: Latest Read The Docs

.. image:: https://img.shields.io/matrix/rappitz09:matrix.org?label=Discuss%20on%20Matrix%20at%20%23rappitz09%3Amatrix.org&logo=matrix&server_fqdn=matrix.org&style=flat
  :target: https://matrix.to/#/%23rappitz09:matrix.org
  :alt: Matrix Room — #rappitz09:matrix.org

.. image:: https://img.shields.io/matrix/rappitz09-space:matrix.org?label=Discuss%20on%20Matrix%20at%20%23rappitz09-space%3Amatrix.org&logo=matrix&server_fqdn=matrix.org&style=flat
  :target: https://matrix.to/#/%23rappitz09-space:matrix.org
  :alt: Matrix Space — #rappitz09-space:matrix.org


Key Features
============

- Supports both client and server side of HTTP protocol.
- Supports both client and server Web-Sockets out-of-the-box and avoids
Callback Hell.
- Provides Web-server with middleware and pluggable routing.


Getting started
===============

Client
------

To get something from the web:

.. code-block:: python

import ezyhttp
import asyncio

async def main():

    async with ezyhttp.ClientSession() as session:
        async with session.get('http://python.org') as response:

            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.text()
            print("Body:", html[:15], "...")

asyncio.run(main())

This prints:

.. code-block::

  Status: 200
  Content-type: text/html; charset=utf-8
  Body: <!doctype html> ...

Coming from `requests <https://requests.readthedocs.io/>`_ ? Read `why we need so many lines <https://ezyhttp.readthedocs.io/en/latest/http_request_lifecycle.html>`_.

Server
------

An example using a simple server:

.. code-block:: python

  # examples/server_simple.py
  from ezyhttp import web

  async def handle(request):
      name = request.match_info.get('name', "Anonymous")
      text = "Hello, " + name
      return web.Response(text=text)

  async def wshandle(request):
      ws = web.WebSocketResponse()
      await ws.prepare(request)

      async for msg in ws:
          if msg.type == web.WSMsgType.text:
              await ws.send_str("Hello, {}".format(msg.data))
          elif msg.type == web.WSMsgType.binary:
              await ws.send_bytes(msg.data)
          elif msg.type == web.WSMsgType.close:
              break

      return ws


  app = web.Application()
  app.add_routes([web.get('/', handle),
                  web.get('/echo', wshandle),
                  web.get('/{name}', handle)])

  if __name__ == '__main__':
      web.run_app(app)


Documentation
=============

https://ezyhttp.readthedocs.io/



External links
==============

* `Third party libraries
<http://ezyhttp.readthedocs.io/en/latest/third_party.html>`_
* `Built with ezyhttp
<http://ezyhttp.readthedocs.io/en/latest/built_with.html>`_
* `Powered by ezyhttp
<http://ezyhttp.readthedocs.io/en/latest/powered_by.html>`_

Feel free to make a Pull Request for adding your link to these pages!


Communication channels
======================

*rappitz09 Discussions*: https://github.com/rappitz09/ezyhttp/discussions

Please add *ezyhttp* tag to your question there.

Requirements
============

- async-timeout_
- multidict_
- yarl_
- frozenlist_

Optionally you may install the aiodns_ library (highly recommended for sake of speed).

.. _aiodns: https://pypi.python.org/pypi/aiodns
.. _multidict: https://pypi.python.org/pypi/multidict
.. _frozenlist: https://pypi.org/project/frozenlist/
.. _yarl: https://pypi.python.org/pypi/yarl
.. _async-timeout: https://pypi.python.org/pypi/async_timeout

License
=======

``ezyhttp`` is offered under the Apache 2 license.


Keepsafe
========

The ezyhttp community would like to thank Keepsafe
(https://www.getkeepsafe.com) for its support in the early days of
the project.


Source code
===========

The latest developer version is available in a GitHub repository:
https://github.com/rappitz09/ezyhttp

Benchmarks
==========

If you are interested in efficiency, the AsyncIO community maintains a
list of benchmarks on the official wiki:
https://github.com/python/asyncio/wiki/Benchmarks
