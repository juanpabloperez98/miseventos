import logging
import time

from flask import Flask, Response, g, request

logger = logging.getLogger("app.http")


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def start_timer() -> None:
        g.request_started_at = time.perf_counter()

    @app.after_request
    def log_request(response: Response) -> Response:
        started_at = g.pop("request_started_at", None)
        duration_ms = (
            round((time.perf_counter() - started_at) * 1000, 2) if started_at is not None else None
        )
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
