# type: ignore
import pathlib
from typing import Any

import pytest
from yarl import URL

from ezyhttp import web
from ezyhttp.web_urldispatcher import UrlDispatcher


@pytest.fixture
def router():
    return UrlDispatcher()


def test_get(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.get("/", handler)])
    assert len(router.routes()) == 2  # GET and HEAD

    route = list(router.routes())[1]
    assert route.handler is handler
    assert route.method == "GET"
    assert str(route.url_for()) == "/"

    route2 = list(router.routes())[0]
    assert route2.handler is handler
    assert route2.method == "HEAD"


def test_head(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.head("/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "HEAD"
    assert str(route.url_for()) == "/"


def test_options(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.options("/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "OPTIONS"
    assert str(route.url_for()) == "/"


def test_post(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.post("/", handler)])

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "POST"
    assert str(route.url_for()) == "/"


def test_put(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.put("/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "PUT"
    assert str(route.url_for()) == "/"


def test_patch(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.patch("/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "PATCH"
    assert str(route.url_for()) == "/"


def test_delete(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.delete("/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "DELETE"
    assert str(route.url_for()) == "/"


def test_route(router: Any) -> None:
    async def handler(request):
        pass

    router.add_routes([web.route("OTHER", "/", handler)])
    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.handler is handler
    assert route.method == "OTHER"
    assert str(route.url_for()) == "/"


def test_static(router: Any) -> None:
    folder = pathlib.Path(__file__).parent
    router.add_routes([web.static("/prefix", folder)])
    assert len(router.resources()) == 1  # 2 routes: for HEAD and GET

    resource = list(router.resources())[0]
    info = resource.get_info()
    assert info["prefix"] == "/prefix"
    assert info["directory"] == folder
    url = resource.url_for(filename="ezyhttp.png")
    assert url == URL("/prefix/ezyhttp.png")


def test_head_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.head("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "HEAD"
    assert str(route.url_for()) == "/path"


def test_get_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.get("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 2

    route1 = list(router.routes())[0]
    assert route1.method == "HEAD"
    assert str(route1.url_for()) == "/path"

    route2 = list(router.routes())[1]
    assert route2.method == "GET"
    assert str(route2.url_for()) == "/path"


def test_post_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.post("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "POST"
    assert str(route.url_for()) == "/path"


def test_put_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.put("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "PUT"
    assert str(route.url_for()) == "/path"


def test_patch_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.patch("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "PATCH"
    assert str(route.url_for()) == "/path"


def test_delete_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.delete("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "DELETE"
    assert str(route.url_for()) == "/path"


def test_options_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.options("/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "OPTIONS"
    assert str(route.url_for()) == "/path"


def test_route_deco(router: Any) -> None:
    routes = web.RouteTableDef()

    @routes.route("OTHER", "/path")
    async def handler(request):
        pass

    router.add_routes(routes)

    assert len(router.routes()) == 1

    route = list(router.routes())[0]
    assert route.method == "OTHER"
    assert str(route.url_for()) == "/path"


def test_routedef_sequence_protocol() -> None:
    routes = web.RouteTableDef()

    @routes.delete("/path")
    async def handler(request):
        pass

    assert len(routes) == 1

    info = routes[0]
    assert isinstance(info, web.RouteDef)
    assert info in routes
    assert list(routes)[0] is info


def test_repr_route_def() -> None:
    routes = web.RouteTableDef()

    @routes.get("/path")
    async def handler(request):
        pass

    rd = routes[0]
    assert repr(rd) == "<RouteDef GET /path -> 'handler'>"


def test_repr_route_def_with_extra_info() -> None:
    routes = web.RouteTableDef()

    @routes.get("/path", extra="info")
    async def handler(request):
        pass

    rd = routes[0]
    assert repr(rd) == "<RouteDef GET /path -> 'handler', extra='info'>"


def test_repr_static_def() -> None:
    routes = web.RouteTableDef()

    routes.static("/prefix", "/path", name="name")

    rd = routes[0]
    assert repr(rd) == "<StaticDef /prefix -> /path, name='name'>"


def test_repr_route_table_def() -> None:
    routes = web.RouteTableDef()

    @routes.get("/path")
    async def handler(request):
        pass

    assert repr(routes) == "<RouteTableDef count=1>"
