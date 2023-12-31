.. module:: ezyhttp.test_utils

.. _ezyhttp-testing:

Testing
=======

Testing ezyhttp web servers
---------------------------

ezyhttp provides plugin for *pytest* making writing web server tests
extremely easy, it also provides :ref:`test framework agnostic
utilities <ezyhttp-testing-framework-agnostic-utilities>` for testing
with other frameworks such as :ref:`unittest
<ezyhttp-testing-unittest-example>`.

Before starting to write your tests, you may also be interested on
reading :ref:`how to write testable
services<ezyhttp-testing-writing-testable-services>` that interact
with the loop.


For using pytest plugin please install pytest-ezyhttp_ library:

.. code-block:: shell

   $ pip install pytest-ezyhttp

If you don't want to install *pytest-ezyhttp* for some reason you may
insert ``pytest_plugins = 'ezyhttp.pytest_plugin'`` line into
``conftest.py`` instead for the same functionality.



Provisional Status
~~~~~~~~~~~~~~~~~~

The module is a **provisional**.

*ezyhttp* has a year and half period for removing deprecated API
(:ref:`ezyhttp-backward-compatibility-policy`).

But for :mod:`ezyhttp.test_tools` the deprecation period could be reduced.

Moreover we may break *backward compatibility* without *deprecation
period* for some very strong reason.


The Test Client and Servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

*ezyhttp* test utils provides a scaffolding for testing ezyhttp-based
web servers.

They consist of two parts: running test server and making HTTP
requests to this server.

:class:`~ezyhttp.test_utils.TestServer` runs :class:`ezyhttp.web.Application`
based server, :class:`~ezyhttp.test_utils.RawTestServer` starts
:class:`ezyhttp.web.Server` low level server.

For performing HTTP requests to these servers you have to create a
test client: :class:`~ezyhttp.test_utils.TestClient` instance.

The client incapsulates :class:`ezyhttp.ClientSession` by providing
proxy methods to the client for common operations such as
*ws_connect*, *get*, *post*, etc.



Pytest
~~~~~~

.. currentmodule:: pytest_ezyhttp

The :data:`ezyhttp_client` fixture available from pytest-ezyhttp_ plugin
allows you to create a client to make requests to test your app.

A simple would be::

    from ezyhttp import web

    async def hello(request):
        return web.Response(text='Hello, world')

    async def test_hello(ezyhttp_client):
        app = web.Application()
        app.router.add_get('/', hello)
        client = await ezyhttp_client(app)
        resp = await client.get('/')
        assert resp.status == 200
        text = await resp.text()
        assert 'Hello, world' in text


It also provides access to the app instance allowing tests to check the state
of the app. Tests can be made even more succinct with a fixture to create an
app test client::

    import pytest
    from ezyhttp import web

    value = web.AppKey("value", str)


    async def previous(request):
        if request.method == 'POST':
            request.app[value] = (await request.post())['value']
            return web.Response(body=b'thanks for the data')
        return web.Response(
            body='value: {}'.format(request.app[value]).encode('utf-8'))

    @pytest.fixture
    def cli(loop, ezyhttp_client):
        app = web.Application()
        app.router.add_get('/', previous)
        app.router.add_post('/', previous)
        return loop.run_until_complete(ezyhttp_client(app))

    async def test_set_value(cli):
        resp = await cli.post('/', data={'value': 'foo'})
        assert resp.status == 200
        assert await resp.text() == 'thanks for the data'
        assert cli.server.app[value] == 'foo'

    async def test_get_value(cli):
        cli.server.app[value] = 'bar'
        resp = await cli.get('/')
        assert resp.status == 200
        assert await resp.text() == 'value: bar'


Pytest tooling has the following fixtures:

.. data:: ezyhttp_server(app, *, port=None, **kwargs)

   A fixture factory that creates
   :class:`~ezyhttp.test_utils.TestServer`::

      async def test_f(ezyhttp_server):
          app = web.Application()
          # fill route table

          server = await ezyhttp_server(app)

   The server will be destroyed on exit from test function.

   *app* is the :class:`ezyhttp.web.Application` used
                           to start server.

   *port* optional, port the server is run at, if
   not provided a random unused port is used.

   .. versionadded:: 3.0

   *kwargs* are parameters passed to
                  :meth:`ezyhttp.web.AppRunner`

   .. versionchanged:: 3.0
   .. deprecated:: 3.2

      The fixture was renamed from ``test_server`` to ``ezyhttp_server``.


.. data:: ezyhttp_client(app, server_kwargs=None, **kwargs)
          ezyhttp_client(server, **kwargs)
          ezyhttp_client(raw_server, **kwargs)

   A fixture factory that creates
   :class:`~ezyhttp.test_utils.TestClient` for access to tested server::

      async def test_f(ezyhttp_client):
          app = web.Application()
          # fill route table

          client = await ezyhttp_client(app)
          resp = await client.get('/')

   *client* and responses are cleaned up after test function finishing.

   The fixture accepts :class:`ezyhttp.web.Application`,
   :class:`ezyhttp.test_utils.TestServer` or
   :class:`ezyhttp.test_utils.RawTestServer` instance.

   *server_kwargs* are parameters passed to the test server if an app
   is passed, else ignored.

   *kwargs* are parameters passed to
   :class:`ezyhttp.test_utils.TestClient` constructor.

   .. versionchanged:: 3.0

      The fixture was renamed from ``test_client`` to ``ezyhttp_client``.

.. data:: ezyhttp_raw_server(handler, *, port=None, **kwargs)

   A fixture factory that creates
   :class:`~ezyhttp.test_utils.RawTestServer` instance from given web
   handler.::

      async def test_f(ezyhttp_raw_server, ezyhttp_client):

          async def handler(request):
              return web.Response(text="OK")

          raw_server = await ezyhttp_raw_server(handler)
          client = await ezyhttp_client(raw_server)
          resp = await client.get('/')

   *handler* should be a coroutine which accepts a request and returns
   response, e.g.

   *port* optional, port the server is run at, if
   not provided a random unused port is used.

   .. versionadded:: 3.0

.. data:: ezyhttp_unused_port()

   Function to return an unused port number for IPv4 TCP protocol::

      async def test_f(ezyhttp_client, ezyhttp_unused_port):
          port = ezyhttp_unused_port()
          app = web.Application()
          # fill route table

          client = await ezyhttp_client(app, server_kwargs={'port': port})
          ...

   .. versionchanged:: 3.0

      The fixture was renamed from ``unused_port`` to ``ezyhttp_unused_port``.

.. data:: ezyhttp_client_cls

   A fixture for passing custom :class:`~ezyhttp.test_utils.TestClient` implementations::

      class MyClient(TestClient):
          async def login(self, *, user, pw):
              payload = {"username": user, "password": pw}
              return await self.post("/login", json=payload)

      @pytest.fixture
      def ezyhttp_client_cls():
          return MyClient

      def test_login(ezyhttp_client):
          app = web.Application()
          client = await ezyhttp_client(app)
          await client.login(user="admin", pw="s3cr3t")

   If you want to switch between different clients in tests, you can use
   the usual ``pytest`` machinery. Example with using test markers::

      class RESTfulClient(TestClient):
          ...

      class GraphQLClient(TestClient):
          ...

      @pytest.fixture
      def ezyhttp_client_cls(request):
          if request.node.get_closest_marker('rest') is not None:
              return RESTfulClient
          if request.node.get_closest_marker('graphql') is not None:
              return GraphQLClient
          return TestClient


      @pytest.mark.rest
      async def test_rest(ezyhttp_client) -> None:
          client: RESTfulClient = await ezyhttp_client(Application())
          ...


      @pytest.mark.graphql
      async def test_graphql(ezyhttp_client) -> None:
          client: GraphQLClient = await ezyhttp_client(Application())
          ...


.. _ezyhttp-testing-unittest-example:

.. _ezyhttp-testing-unittest-style:

Unittest
~~~~~~~~

.. currentmodule:: ezyhttp.test_utils


To test applications with the standard library's unittest or unittest-based
functionality, the ezyhttpTestCase is provided::

    from ezyhttp.test_utils import ezyhttpTestCase
    from ezyhttp import web

    class MyAppTestCase(ezyhttpTestCase):

        async def get_application(self):
            """
            Override the get_app method to return your application.
            """
            async def hello(request):
                return web.Response(text='Hello, world')

            app = web.Application()
            app.router.add_get('/', hello)
            return app

        async def test_example(self):
            async with self.client.request("GET", "/") as resp:
                self.assertEqual(resp.status, 200)
                text = await resp.text()
            self.assertIn("Hello, world", text)

.. class:: ezyhttpTestCase

    A base class to allow for unittest web applications using ezyhttp.

    Derived from :class:`unittest.IsolatedAsyncioTestCase`

    See :class:`unittest.TestCase` and :class:`unittest.IsolatedAsyncioTestCase`
    for inherited methods and behavior.

    This class additionally provides the following:

    .. attribute:: client

       an ezyhttp test client, :class:`TestClient` instance.

    .. attribute:: server

       an ezyhttp test server, :class:`TestServer` instance.

       .. versionadded:: 2.3

    .. attribute:: app

       The application returned by :meth:`~ezyhttp.test_utils.ezyhttpTestCase.get_application`
       (:class:`ezyhttp.web.Application` instance).

    .. method:: get_client()
      :async:

       This async method can be overridden to return the :class:`TestClient`
       object used in the test.

       :return: :class:`TestClient` instance.

       .. versionadded:: 2.3

    .. method:: get_server()
      :async:

       This async method can be overridden to return the :class:`TestServer`
       object used in the test.

       :return: :class:`TestServer` instance.

       .. versionadded:: 2.3

    .. method:: get_application()
      :async:

       This async method should be overridden
       to return the :class:`ezyhttp.web.Application`
       object to test.

       :return: :class:`ezyhttp.web.Application` instance.

    .. method:: asyncSetUp()
      :async:

       This async method can be overridden to execute asynchronous code during
       the ``setUp`` stage of the ``TestCase``::

           async def asyncSetUp(self):
               await super().asyncSetUp()
               await foo()

       .. versionadded:: 2.3

       .. versionchanged:: 3.8

          ``await super().asyncSetUp()`` call is required.

    .. method:: asyncTearDown()
      :async:

       This async method can be overridden to execute asynchronous code during
       the ``tearDown`` stage of the ``TestCase``::

           async def asyncTearDown(self):
               await super().asyncTearDown()
               await foo()

       .. versionadded:: 2.3

       .. versionchanged:: 3.8

          ``await super().asyncTearDown()`` call is required.

Faking request object
^^^^^^^^^^^^^^^^^^^^^

ezyhttp provides test utility for creating fake
:class:`ezyhttp.web.Request` objects:
:func:`ezyhttp.test_utils.make_mocked_request`, it could be useful in
case of simple unit tests, like handler tests, or simulate error
conditions that hard to reproduce on real server::

    from ezyhttp import web
    from ezyhttp.test_utils import make_mocked_request

    def handler(request):
        assert request.headers.get('token') == 'x'
        return web.Response(body=b'data')

    def test_handler():
        req = make_mocked_request('GET', '/', headers={'token': 'x'})
        resp = handler(req)
        assert resp.body == b'data'

.. warning::

   We don't recommend to apply
   :func:`~ezyhttp.test_utils.make_mocked_request` everywhere for
   testing web-handler's business object -- please use test client and
   real networking via 'localhost' as shown in examples before.

   :func:`~ezyhttp.test_utils.make_mocked_request` exists only for
   testing complex cases (e.g. emulating network errors) which
   are extremely hard or even impossible to test by conventional
   way.


.. function:: make_mocked_request(method, path, headers=None, *, \
                                  version=HttpVersion(1, 1), \
                                  closing=False, \
                                  app=None, \
                                  match_info=sentinel, \
                                  reader=sentinel, \
                                  writer=sentinel, \
                                  transport=sentinel, \
                                  payload=sentinel, \
                                  sslcontext=None, \
                                  loop=...)

   Creates mocked web.Request testing purposes.

   Useful in unit tests, when spinning full web server is overkill or
   specific conditions and errors are hard to trigger.

   :param method: str, that represents HTTP method, like; GET, POST.
   :type method: str

   :param path: str, The URL including *PATH INFO* without the host or scheme
   :type path: str

   :param headers: mapping containing the headers. Can be anything accepted
       by the multidict.CIMultiDict constructor.
   :type headers: dict, multidict.CIMultiDict, list of tuple(str, str)

   :param match_info: mapping containing the info to match with url parameters.
   :type match_info: dict

   :param version: namedtuple with encoded HTTP version
   :type version: ezyhttp.protocol.HttpVersion

   :param closing: flag indicates that connection should be closed after
       response.
   :type closing: bool

   :param app: the ezyhttp.web application attached for fake request
   :type app: ezyhttp.web.Application

   :param writer: object for managing outcoming data
   :type writer: ezyhttp.StreamWriter

   :param transport: asyncio transport instance
   :type transport: asyncio.Transport

   :param payload: raw payload reader object
   :type  payload: ezyhttp.StreamReader

   :param sslcontext: ssl.SSLContext object, for HTTPS connection
   :type sslcontext: ssl.SSLContext

   :param loop: An event loop instance, mocked loop by default.
   :type loop: :class:`asyncio.AbstractEventLoop`

   :return: :class:`ezyhttp.web.Request` object.

   .. versionadded:: 2.3
      *match_info* parameter.

.. _ezyhttp-testing-writing-testable-services:

.. _ezyhttp-testing-framework-agnostic-utilities:


Framework Agnostic Utilities
----------------------------

High level test creation::

    from ezyhttp.test_utils import TestClient, TestServer, loop_context
    from ezyhttp import request

    # loop_context is provided as a utility. You can use any
    # asyncio.BaseEventLoop class in its place.
    with loop_context() as loop:
        app = _create_example_app()
        with TestClient(TestServer(app), loop=loop) as client:

            async def test_get_route():
                nonlocal client
                resp = await client.get("/")
                assert resp.status == 200
                text = await resp.text()
                assert "Hello, world" in text

            loop.run_until_complete(test_get_route())


If it's preferred to handle the creation / teardown on a more granular
basis, the TestClient object can be used directly::

    from ezyhttp.test_utils import TestClient, TestServer

    with loop_context() as loop:
        app = _create_example_app()
        client = TestClient(TestServer(app), loop=loop)
        loop.run_until_complete(client.start_server())
        root = "http://127.0.0.1:{}".format(port)

        async def test_get_route():
            resp = await client.get("/")
            assert resp.status == 200
            text = await resp.text()
            assert "Hello, world" in text

        loop.run_until_complete(test_get_route())
        loop.run_until_complete(client.close())


A full list of the utilities provided can be found at the
:data:`api reference <ezyhttp.test_utils>`


Testing API Reference
---------------------

Test server
~~~~~~~~~~~

Runs given :class:`ezyhttp.web.Application` instance on random TCP port.

After creation the server is not started yet, use
:meth:`~ezyhttp.test_utils.BaseTestServer.start_server` for actual server
starting and :meth:`~ezyhttp.test_utils.BaseTestServer.close` for
stopping/cleanup.

Test server usually works in conjunction with
:class:`ezyhttp.test_utils.TestClient` which provides handy client methods
for accessing to the server.

.. class:: BaseTestServer(*, scheme='http', host='127.0.0.1', port=None, socket_factory=get_port_socket)

   Base class for test servers.

   :param str scheme: HTTP scheme, non-protected ``"http"`` by default.

   :param str host: a host for TCP socket, IPv4 *local host*
      (``'127.0.0.1'``) by default.

   :param int port: optional port for TCP socket, if not provided a
      random unused port is used.

      .. versionadded:: 3.0

   :param collections.abc.Callable[[str,int,socket.AddressFamily],socket.socket] socket_factory: optional
                          Factory to create a socket for the server.
                          By default creates a TCP socket and binds it
                          to ``host`` and ``port``.

      .. versionadded:: 3.8

   .. attribute:: scheme

      A *scheme* for tested application, ``'http'`` for non-protected
      run and ``'https'`` for TLS encrypted server.

   .. attribute:: host

      *host* used to start a test server.

   .. attribute:: port

      *port* used to start the test server.

   .. attribute:: handler

      :class:`ezyhttp.web.Server` used for HTTP requests serving.

   .. attribute:: server

      :class:`asyncio.AbstractServer` used for managing accepted connections.

   .. attribute:: socket_factory

      *socket_factory* used to create and bind a server socket.

      .. versionadded:: 3.8

   .. method:: start_server(**kwargs)
      :async:

      Start a test server.

   .. method:: close()
      :async:

      Stop and finish executed test server.

   .. method:: make_url(path)

      Return an *absolute* :class:`~yarl.URL` for given *path*.


.. class:: RawTestServer(handler, *, scheme="http", host='127.0.0.1')

   Low-level test server (derived from :class:`BaseTestServer`).

   :param handler: a coroutine for handling web requests. The
                   handler should accept
                   :class:`ezyhttp.web.BaseRequest` and return a
                   response instance,
                   e.g. :class:`~ezyhttp.web.StreamResponse` or
                   :class:`~ezyhttp.web.Response`.

                   The handler could raise
                   :class:`~ezyhttp.web.HTTPException` as a signal for
                   non-200 HTTP response.

   :param str scheme: HTTP scheme, non-protected ``"http"`` by default.

   :param str host: a host for TCP socket, IPv4 *local host*
      (``'127.0.0.1'``) by default.

   :param int port: optional port for TCP socket, if not provided a
      random unused port is used.

      .. versionadded:: 3.0


.. class:: TestServer(app, *, scheme="http", host='127.0.0.1')

   Test server (derived from :class:`BaseTestServer`) for starting
   :class:`~ezyhttp.web.Application`.

   :param app: :class:`ezyhttp.web.Application` instance to run.

   :param str scheme: HTTP scheme, non-protected ``"http"`` by default.

   :param str host: a host for TCP socket, IPv4 *local host*
      (``'127.0.0.1'``) by default.

   :param int port: optional port for TCP socket, if not provided a
      random unused port is used.

      .. versionadded:: 3.0

   .. attribute:: app

      :class:`ezyhttp.web.Application` instance to run.


Test Client
~~~~~~~~~~~

.. class:: TestClient(app_or_server, *, \
                      scheme='http', host='127.0.0.1', \
                      cookie_jar=None, **kwargs)

   A test client used for making calls to tested server.

   :param app_or_server: :class:`BaseTestServer` instance for making
                         client requests to it.

                         In order to pass an :class:`ezyhttp.web.Application`
                         you need to convert it first to :class:`TestServer`
                         first with ``TestServer(app)``.

   :param cookie_jar: an optional :class:`ezyhttp.CookieJar` instance,
                      may be useful with
                      ``CookieJar(unsafe=True, treat_as_secure_origin="http://127.0.0.1")``
                      option.

   :param str scheme: HTTP scheme, non-protected ``"http"`` by default.

   :param str host: a host for TCP socket, IPv4 *local host*
      (``'127.0.0.1'``) by default.

   .. attribute:: scheme

      A *scheme* for tested application, ``'http'`` for non-protected
      run and ``'https'`` for TLS encrypted server.

   .. attribute:: host

      *host* used to start a test server.

   .. attribute:: port

      *port* used to start the server

   .. attribute:: server

      :class:`BaseTestServer` test server instance used in conjunction
      with client.

   .. attribute:: app

      An alias for ``self.server.app``. return ``None`` if
      ``self.server`` is not :class:`TestServer`
      instance(e.g. :class:`RawTestServer` instance for test low-level server).

   .. attribute:: session

      An internal :class:`ezyhttp.ClientSession`.

      Unlike the methods on the :class:`TestClient`, client session
      requests do not automatically include the host in the url
      queried, and will require an absolute path to the resource.

   .. method:: start_server(**kwargs)
      :async:

      Start a test server.

   .. method:: close()
      :async:

      Stop and finish executed test server.

   .. method:: make_url(path)

      Return an *absolute* :class:`~yarl.URL` for given *path*.

   .. method:: request(method, path, *args, **kwargs)
      :async:

      Routes a request to tested http server.

      The interface is identical to
      :meth:`ezyhttp.ClientSession.request`, except the loop kwarg is
      overridden by the instance used by the test server.

   .. method:: get(path, *args, **kwargs)
      :async:

      Perform an HTTP GET request.

   .. method:: post(path, *args, **kwargs)
      :async:

      Perform an HTTP POST request.

   .. method:: options(path, *args, **kwargs)
      :async:

      Perform an HTTP OPTIONS request.

   .. method:: head(path, *args, **kwargs)
      :async:

      Perform an HTTP HEAD request.

   .. method:: put(path, *args, **kwargs)
      :async:

      Perform an HTTP PUT request.

   .. method:: patch(path, *args, **kwargs)
      :async:

      Perform an HTTP PATCH request.

   .. method:: delete(path, *args, **kwargs)
      :async:

      Perform an HTTP DELETE request.

   .. method:: ws_connect(path, *args, **kwargs)
      :async:

      Initiate websocket connection.

      The api corresponds to :meth:`ezyhttp.ClientSession.ws_connect`.


Utilities
~~~~~~~~~

.. function:: make_mocked_coro(return_value)

  Creates a coroutine mock.

  Behaves like a coroutine which returns *return_value*.  But it is
  also a mock object, you might test it as usual
  :class:`~unittest.mock.Mock`::

      mocked = make_mocked_coro(1)
      assert 1 == await mocked(1, 2)
      mocked.assert_called_with(1, 2)


  :param return_value: A value that the the mock object will return when
      called.
  :returns: A mock object that behaves as a coroutine which returns
      *return_value* when called.


.. function:: unused_port()

   Return an unused port number for IPv4 TCP protocol.

   :return int: ephemeral port number which could be reused by test server.

.. function:: loop_context(loop_factory=<function asyncio.new_event_loop>)

   A contextmanager that creates an event_loop, for test purposes.

   Handles the creation and cleanup of a test loop.

.. function:: setup_test_loop(loop_factory=<function asyncio.new_event_loop>)

   Create and return an :class:`asyncio.AbstractEventLoop` instance.

   The caller should also call teardown_test_loop, once they are done
   with the loop.

   .. note::

      As side effect the function changes asyncio *default loop* by
      :func:`asyncio.set_event_loop` call.

      Previous default loop is not restored.

      It should not be a problem for test suite: every test expects a
      new test loop instance anyway.

   .. versionchanged:: 3.1

      The function installs a created event loop as *default*.

.. function:: teardown_test_loop(loop)

   Teardown and cleanup an event_loop created by setup_test_loop.

   :param loop: the loop to teardown
   :type loop: asyncio.AbstractEventLoop



.. _pytest: http://pytest.org/latest/
.. _pytest-ezyhttp: https://pypi.python.org/pypi/pytest-ezyhttp
