import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from jarvis import __version__
from jarvis.api.routes import api_router
from jarvis.bootstrap import ApplicationContainer, build_application_container
from jarvis.config import Settings, get_settings
from jarvis.logging_setup import configure_logging, current_request_id

logger = logging.getLogger("jarvis.api")

REQUEST_ID_HEADER = "X-Request-ID"


async def attach_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    context_token = current_request_id.set(request_id)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s in %.1f ms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started_at) * 1000,
        )
        return response
    finally:
        current_request_id.reset(context_token)


def create_app(
    settings: Settings | None = None,
    container_factory: Callable[[Settings], ApplicationContainer] = build_application_container,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level, resolved_settings.log_as_json)

    @asynccontextmanager
    async def manage_lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container_factory(resolved_settings)
        yield
        app.state.container.shutdown()

    app = FastAPI(
        title="Jarvis Truck Configurator API",
        version=__version__,
        lifespan=manage_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.middleware("http")(attach_request_id)
    app.include_router(api_router)
    return app
