.. ezyhttp documentation master file, created by
   sphinx-quickstart on Wed Mar  5 12:35:35 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==================
Welcome to ezyhttp
==================

Asynchronous HTTP Client/Server for :term:`asyncio` and Python.

Current version is |release|.

.. _GitHub: https://github.com/rappitz09/ezyhttp


Key Features
============

- Supports both :ref:`ezyhttp-client` and :ref:`HTTP Server <ezyhttp-web>`.
- Supports both :ref:`Server WebSockets <ezyhttp-web-websockets>` and
  :ref:`Client WebSockets <ezyhttp-client-websockets>` out-of-the-box
  without the Callback Hell.
- Web-server has :ref:`ezyhttp-web-middlewares`,
  :ref:`ezyhttp-web-signals` and pluggable routing.

.. _ezyhttp-installation:

Library Installation
====================

.. code-block:: bash

   $ pip install ezyhttp

For speeding up DNS resolving by client API you may install
:term:`aiodns` as well.
This option is highly recommended:

.. code-block:: bash

   $ pip install aiodns

Installing all speedups in one command
--------------------------------------

The following will get you ``ezyhttp`` along with :term:`aiodns` and ``Brotli`` in one
bundle.
No need to type separate commands anymore!

.. code-block:: bash

   $ pip install ezyhttp[speedups]

Getting Started
===============

Client example
--------------

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

.. code-block:: text

    Status: 200
    Content-type: text/html; charset=utf-8
    Body: <!doctype html> ...

Coming from :term:`requests` ? Read :ref:`why we need so many lines <ezyhttp-request-lifecycle>`.

Server example:
----------------

.. code-block:: python

    from ezyhttp import web

    async def handle(request):
        name = request.match_info.get('name', "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    app = web.Application()
    app.add_routes([web.get('/', handle),
                    web.get('/{name}', handle)])

    if __name__ == '__main__':
        web.run_app(app)


For more information please visit :ref:`ezyhttp-client` and
:ref:`ezyhttp-web` pages.

Development mode
================

When writing your code, we recommend enabling Python's
`development mode <https://docs.python.org/3/library/devmode.html>`_
(``python -X dev``). In addition to the extra features enabled for asyncio, ezyhttp
will:

- Use a strict parser in the client code (which can help detect malformed responses
  from a server).
- Enable some additional checks (resulting in warnings in certain situations).

What's new in ezyhttp 3?
========================

Go to :ref:`ezyhttp_whats_new_3_0` page for ezyhttp 3.0 major release
changes.


Tutorial
========

:ref:`Polls tutorial <ezyhttpdemos:ezyhttp-demos-polls-beginning>`


Source code
===========

The project is hosted on GitHub_

Please feel free to file an issue on the `bug tracker
<https://github.com/rappitz09/ezyhttp/issues>`_ if you have found a bug
or have some suggestion in order to improve the library.


Dependencies
============

- *async_timeout*
- *multidict*
- *yarl*

- *Optional* :term:`aiodns` for fast DNS resolving. The
  library is highly recommended.

  .. code-block:: bash

     $ pip install aiodns

- *Optional* :term:`Brotli` or :term:`brotlicffi` for brotli (:rfc:`7932`)
  client compression support.

  .. code-block:: bash

     $ pip install Brotli


Communication channels
======================

*rappitz09 Discussions*: https://github.com/rappitz09/ezyhttp/discussions

Feel free to post your questions and ideas here.

*gitter chat* https://gitter.im/rappitz09/Lobby

We support `Stack Overflow
<https://stackoverflow.com/questions/tagged/ezyhttp>`_.
Please add *ezyhttp* tag to your question there.

Contributing
============

Please read the :ref:`instructions for contributors<ezyhttp-contributing>`
before making a Pull Request.


Authors and License
===================

The ``ezyhttp`` package is written mostly by Nikolay Kim and Andrew Svetlov.

It's *Apache 2* licensed and freely available.

Feel free to improve this package and send a pull request to GitHub_.


.. _ezyhttp-backward-compatibility-policy:

Policy for Backward Incompatible Changes
========================================

*ezyhttp* keeps backward compatibility.

When a new release is published that deprecates a *Public API* (method, class,
function argument, etc.), the library will guarantee its usage for at least
a year and half from the date of release.

Deprecated APIs are reflected in their documentation, and their use will raise
:exc:`DeprecationWarning`.

However, if there is a strong reason, we may be forced to break this guarantee.
The most likely reason would be a critical bug, such as a security issue, which
cannot be solved without a major API change. We are working hard to keep these
breaking changes as rare as possible.


Table Of Contents
=================

.. toctree::
   :name: mastertoc
   :maxdepth: 2

   client
   web
   utilities
   faq
   misc
   external
   contributing
