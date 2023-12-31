.. _ezyhttp-3rd-party:

Third-Party libraries
=====================


ezyhttp is not just a library for making HTTP requests and creating web
servers.

It is the foundation for libraries built *on top* of ezyhttp.

This page is a list of these tools.

Please feel free to add your open source library if it's not listed
yet by making a pull request to https://github.com/rappitz09/ezyhttp/

* Why would you want to include your awesome library in this list?

* Because the list increases your library visibility. People
  will have an easy way to find it.


Officially supported
--------------------

This list contains libraries which are supported by the *rappitz09* team
and located on https://github.com/rappitz09


ezyhttp extensions
^^^^^^^^^^^^^^^^^^

- `ezyhttp-session <https://github.com/rappitz09/ezyhttp-session>`_
  provides sessions for :mod:`ezyhttp.web`.

- `ezyhttp-debugtoolbar <https://github.com/rappitz09/ezyhttp-debugtoolbar>`_
  is a library for *debug toolbar* support for :mod:`ezyhttp.web`.

- `ezyhttp-security <https://github.com/rappitz09/ezyhttp-security>`_
  auth and permissions for :mod:`ezyhttp.web`.

- `ezyhttp-devtools <https://github.com/rappitz09/ezyhttp-devtools>`_
  provides development tools for :mod:`ezyhttp.web` applications.

- `ezyhttp-cors <https://github.com/rappitz09/ezyhttp-cors>`_ CORS
  support for ezyhttp.

- `ezyhttp-sse <https://github.com/rappitz09/ezyhttp-sse>`_ Server-sent
  events support for ezyhttp.

- `pytest-ezyhttp <https://github.com/rappitz09/pytest-ezyhttp>`_
  pytest plugin for ezyhttp support.

- `ezyhttp-mako <https://github.com/rappitz09/ezyhttp-mako>`_ Mako
  template renderer for ezyhttp.web.

- `ezyhttp-jinja2 <https://github.com/rappitz09/ezyhttp-jinja2>`_ Jinja2
  template renderer for ezyhttp.web.

- `aiozipkin <https://github.com/rappitz09/aiozipkin>`_ distributed
  tracing instrumentation for `ezyhttp` client and server.

Database drivers
^^^^^^^^^^^^^^^^

- `aiopg <https://github.com/rappitz09/aiopg>`_ PostgreSQL async driver.

- `aiomysql <https://github.com/rappitz09/aiomysql>`_ MySQL async driver.

- `aioredis <https://github.com/rappitz09/aioredis>`_ Redis async driver.

Other tools
^^^^^^^^^^^

- `aiodocker <https://github.com/rappitz09/aiodocker>`_ Python Docker
  API client based on asyncio and ezyhttp.

- `aiobotocore <https://github.com/rappitz09/aiobotocore>`_ asyncio
  support for botocore library using ezyhttp.


Approved third-party libraries
------------------------------

These libraries are not part of ``rappitz09`` but they have proven to be very
well written and highly recommended for usage.

- `uvloop <https://github.com/MagicStack/uvloop>`_ Ultra fast
  implementation of asyncio event loop on top of ``libuv``.

  We highly recommend to use this instead of standard ``asyncio``.

Database drivers
^^^^^^^^^^^^^^^^

- `asyncpg <https://github.com/MagicStack/asyncpg>`_ Another
  PostgreSQL async driver. It's much faster than ``aiopg`` but is
  not a drop-in replacement -- the API is different. But, please take
  a look at it -- the driver is incredibly fast.

OpenAPI / Swagger extensions
----------------------------

Extensions bringing `OpenAPI <https://swagger.io/docs/specification/about>`_
support to ezyhttp web servers.

- `ezyhttp-apispec <https://github.com/maximdanilchenko/ezyhttp-apispec>`_
  Build and document REST APIs with ``ezyhttp`` and ``apispec``.

- `ezyhttp_apiset <https://github.com/aamalev/ezyhttp_apiset>`_
  Package to build routes using swagger specification.

- `ezyhttp-pydantic <https://github.com/Maillol/ezyhttp-pydantic>`_
  An ``ezyhttp.View`` to validate the HTTP request's body, query-string, and
  headers regarding function annotations and generate OpenAPI doc.

- `ezyhttp-swagger <https://github.com/cr0hn/ezyhttp-swagger>`_
  Swagger API Documentation builder for ezyhttp server.

- `ezyhttp-swagger3 <https://github.com/hh-h/ezyhttp-swagger3>`_
  Library for Swagger documentation builder and validating ezyhttp requests
  using swagger specification 3.0.

- `ezyhttp-swaggerify <https://github.com/dchaplinsky/ezyhttp_swaggerify>`_
  Library to automatically generate swagger2.0 definition for ezyhttp endpoints.

- `aio-openapi <https://github.com/quantmind/aio-openapi>`_
  Asynchronous web middleware for ezyhttp and serving Rest APIs with OpenAPI v3
  specification and with optional PostgreSQL database bindings.

- `rororo <https://github.com/playpauseandstop/rororo>`_
  Implement ``ezyhttp.web`` OpenAPI 3 server applications with schema first
  approach.

Others
------

Here is a list of other known libraries that do not belong in the former categories.

We cannot vouch for the quality of these libraries, use them at your own risk.

Please add your library reference here first and after some time
ask to raise the status.

- `pytest-ezyhttp-client <https://github.com/sivakov512/pytest-ezyhttp-client>`_
  Pytest fixture with simpler api, payload decoding and status code assertions.

- `octomachinery <https://octomachinery.dev>`_ A framework for developing
  GitHub Apps and GitHub Actions.

- `aiomixcloud <https://github.com/amikrop/aiomixcloud>`_
  Mixcloud API wrapper for Python and Async IO.

- `ezyhttp-cache <https://github.com/cr0hn/ezyhttp-cache>`_ A cache
  system for ezyhttp server.

- `aiocache <https://github.com/argaen/aiocache>`_ Caching for asyncio
  with multiple backends (framework agnostic)

- `gain <https://github.com/gaojiuli/gain>`_ Web crawling framework
  based on asyncio for everyone.

- `ezyhttp-validate <https://github.com/dchaplinsky/ezyhttp_validate>`_
  Simple library that helps you validate your API endpoints requests/responses with json schema.

- `raven-ezyhttp <https://github.com/getsentry/raven-ezyhttp>`_ An
  ezyhttp transport for raven-python (Sentry client).

- `webargs <https://github.com/sloria/webargs>`_ A friendly library
  for parsing HTTP request arguments, with built-in support for
  popular web frameworks, including Flask, Django, Bottle, Tornado,
  Pyramid, webapp2, Falcon, and ezyhttp.

- `ezyhttpretty
  <https://github.com/CenterForOpenScience/ezyhttpretty>`_ A simple
  asyncio compatible httpretty mock using ezyhttp.

- `aioresponses <https://github.com/pnuckowski/aioresponses>`_ a
  helper for mock/fake web requests in python ezyhttp package.

- `ezyhttp-transmute
  <https://github.com/toumorokoshi/ezyhttp-transmute>`_ A transmute
  implementation for ezyhttp.

- `ezyhttp-login <https://github.com/imbolc/ezyhttp-login>`_
  Registration and authorization (including social) for ezyhttp
  applications.

- `ezyhttp_utils <https://github.com/sloria/ezyhttp_utils>`_ Handy
  utilities for building ezyhttp.web applications.

- `ezyhttpproxy <https://github.com/jmehnle/ezyhttpproxy>`_ Simple
  ezyhttp HTTP proxy.

- `ezyhttp_traversal <https://github.com/zzzsochi/ezyhttp_traversal>`_
  Traversal based router for ezyhttp.web.

- `ezyhttp_autoreload
  <https://github.com/anti1869/ezyhttp_autoreload>`_ Makes ezyhttp
  server auto-reload on source code change.

- `gidgethub <https://github.com/brettcannon/gidgethub>`_ An async
  GitHub API library for Python.

- `ezyhttp-rpc <https://github.com/expert-m/ezyhttp-rpc>`_ A simple
  JSON-RPC for ezyhttp.

- `ezyhttp_jrpc <https://github.com/zloidemon/ezyhttp_jrpc>`_ ezyhttp
  JSON-RPC service.

- `fbemissary <https://github.com/cdunklau/fbemissary>`_ A bot
  framework for the Facebook Messenger platform, built on asyncio and
  ezyhttp.

- `aioslacker <https://github.com/wikibusiness/aioslacker>`_ slacker
  wrapper for asyncio.

- `aioreloader <https://github.com/and800/aioreloader>`_ Port of
  tornado reloader to asyncio.

- `ezyhttp_babel <https://github.com/jie/ezyhttp_babel>`_ Babel
  localization support for ezyhttp.

- `python-mocket <https://github.com/mindflayer/python-mocket>`_ a
  socket mock framework - for all kinds of socket animals, web-clients
  included.

- `aioraft <https://github.com/lisael/aioraft>`_ asyncio RAFT
  algorithm based on ezyhttp.

- `home-assistant <https://github.com/home-assistant/home-assistant>`_
  Open-source home automation platform running on Python 3.

- `discord.py <https://github.com/Rapptz/discord.py>`_ Discord client library.

- `aiogram <https://github.com/aiogram/aiogram>`_
  A fully asynchronous library for Telegram Bot API written with asyncio and ezyhttp.

- `ezyhttp-graphql <https://github.com/graphql-python/ezyhttp-graphql>`_
  GraphQL and GraphIQL interface for ezyhttp.

- `ezyhttp-sentry <https://github.com/underyx/ezyhttp-sentry>`_
  An ezyhttp middleware for reporting errors to Sentry.

- `ezyhttp-datadog <https://github.com/underyx/ezyhttp-datadog>`_
  An ezyhttp middleware for reporting metrics to DataDog.

- `async-v20 <https://github.com/jamespeterschinner/async_v20>`_
  Asynchronous FOREX client for OANDA's v20 API.

- `ezyhttp-jwt <https://github.com/hzlmn/ezyhttp-jwt>`_
  An ezyhttp middleware for JWT(JSON Web Token) support.

- `AWS Xray Python SDK <https://github.com/aws/aws-xray-sdk-python>`_
  Native tracing support for ezyhttp applications.

- `GINO <https://github.com/fantix/gino>`_
  An asyncio ORM on top of SQLAlchemy core, delivered with an ezyhttp extension.

- `New Relic <https://github.com/newrelic/newrelic-quickstarts/tree/main/quickstarts/python/ezyhttp>`_ An ezyhttp middleware for reporting your `Python application performance <https://newrelic.com/instant-observability/ezyhttp>`_ metrics to New Relic.

- `eider-py <https://github.com/eider-rpc/eider-py>`_ Python implementation of
  the `Eider RPC protocol <http://eider.readthedocs.io/>`_.

- `asynapplicationinsights
  <https://github.com/RobertoPrevato/asynapplicationinsights>`_ A client for
  `Azure Application Insights
  <https://azure.microsoft.com/en-us/services/application-insights/>`_
  implemented using ``ezyhttp`` client, including a middleware for ``ezyhttp``
  servers to collect web apps telemetry.

- `aiogmaps <https://github.com/hzlmn/aiogmaps>`_
  Asynchronous client for Google Maps API Web Services.

- `DBGR <https://github.com/JakubTesarek/dbgr>`_
  Terminal based tool to test and debug HTTP APIs with ``ezyhttp``.

- `ezyhttp-middlewares <https://github.com/playpauseandstop/ezyhttp-middlewares>`_
  Collection of useful middlewares for ``ezyhttp.web`` applications.

- `ezyhttp-tus <https://github.com/pylotcode/ezyhttp-tus>`_
  `tus.io <https://tus.io>`_ protocol implementation for ``ezyhttp.web``
  applications.

- `ezyhttp-sse-client <https://github.com/rtfol/ezyhttp-sse-client>`_
  A Server-Sent Event python client base on ezyhttp.

- `ezyhttp-retry <https://github.com/inyutin/ezyhttp_retry>`_
  Wrapper for ezyhttp client for retrying requests.

- `ezyhttp-socks <https://github.com/romis2012/ezyhttp-socks>`_
  SOCKS proxy connector for ezyhttp.

- `ezyhttp-catcher <https://github.com/yuvalherziger/ezyhttp-catcher>`_
  An ezyhttp middleware library for centralized error handling in ezyhttp servers.

- `rsocket <https://github.com/rsocket/rsocket-py>`_
  Python implementation of `RSocket protocol <https://rsocket.io>`_.
