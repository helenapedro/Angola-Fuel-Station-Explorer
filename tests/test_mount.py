"""Tests for the WSGI prefix router serving the FastAPI API from the Dash process."""

import unittest

from api.mount import API_PREFIXES, PrefixRouter


def _stub_app(body, content_type="text/plain"):
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", content_type)])
        return [body]

    return app


def _call(wsgi_app, path):
    info = {}

    def start_response(status, headers):
        info["status"] = status
        info["headers"] = dict(headers)

    body = b"".join(wsgi_app({"PATH_INFO": path, "REQUEST_METHOD": "GET"}, start_response))
    return info["status"], body


class PrefixRouterTest(unittest.TestCase):
    def setUp(self):
        self.router = PrefixRouter(
            _stub_app(b"dash"), api_app=_stub_app(b"api", "application/json")
        )

    def test_api_prefixes_route_to_api(self):
        for path in [
            "/api",
            "/api/v1",
            "/api/v1/stations",
            "/api/v1/stations/123",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]:
            _status, body = _call(self.router, path)
            self.assertEqual(body, b"api", path)

    def test_other_paths_fall_through_to_dash(self):
        for path in ["/", "/_dash-layout", "/_dash-component-suites", "/pages/map"]:
            _status, body = _call(self.router, path)
            self.assertEqual(body, b"dash", path)

    def test_near_miss_paths_do_not_match(self):
        # Prefix matching must not catch longer path segments.
        for path in ["/apiary", "/apiv1/x", "/healthy", "/healthz", "/document"]:
            _status, body = _call(self.router, path)
            self.assertEqual(body, b"dash", path)

    def test_path_info_preserved_for_api_app(self):
        seen = {}

        def spy(environ, start_response):
            seen["path"] = environ["PATH_INFO"]
            start_response("200 OK", [])
            return [b""]

        router = PrefixRouter(_stub_app(b"dash"), api_app=spy)
        _call(router, "/api/v1/stations")
        self.assertEqual(seen["path"], "/api/v1/stations")

    def test_prefixes_match_design_doc_contract(self):
        self.assertEqual(
            set(API_PREFIXES), {"/api", "/health", "/docs", "/openapi.json", "/redoc"}
        )


if __name__ == "__main__":
    unittest.main()
