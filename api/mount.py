"""Serve the FastAPI REST API from the same WSGI process as the Dash app.

Heroku runs a single web process (``gunicorn app:server``), so the FastAPI
application would otherwise sit on the dyno unused. This module mounts it
under the API-ish URL prefixes; everything else falls through to Dash.

See docs/api-deployment.md for the full design.
"""

from a2wsgi import ASGIMiddleware

from api.main import app as fastapi_app

# URL prefixes served by the REST API. Kept as an explicit tuple so the
# router and docs/api-deployment.md describe the same contract.
API_PREFIXES = ("/api", "/health", "/docs", "/openapi.json", "/redoc")


class PrefixRouter:
    """WSGI middleware routing API-ish paths to the FastAPI app.

    Unlike ``werkzeug.middleware.dispatcher.DispatcherMiddleware``, the
    request path is passed through untouched (no SCRIPT_NAME stripping),
    so FastAPI keeps seeing its full routes (``/api/v1/stations``, …).
    """

    def __init__(self, default_app, api_app=None, prefixes=API_PREFIXES):
        self._default_app = default_app
        self._api_app = api_app if api_app is not None else ASGIMiddleware(fastapi_app)
        self._prefixes = tuple(prefixes)

    def _is_api_path(self, path: str) -> bool:
        return any(path == prefix or path.startswith(prefix + "/") for prefix in self._prefixes)

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or ""
        app = self._api_app if self._is_api_path(path) else self._default_app
        return app(environ, start_response)


def mount_api(wsgi_app):
    """Wrap a WSGI app so the REST API is served alongside it."""
    return PrefixRouter(wsgi_app)
