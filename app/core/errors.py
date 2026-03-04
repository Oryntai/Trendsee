from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def error_response(status_code: int, code: str, message: str, details: Any | None = None) -> JSONResponse:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        return error_response(500, "internal_error", "Internal server error", str(exc))


def unauthorized(message: str = "Unauthorized") -> ApiError:
    return ApiError(status_code=401, code="unauthorized", message=message)


def forbidden(message: str = "Forbidden") -> ApiError:
    return ApiError(status_code=403, code="forbidden", message=message)


def not_found(message: str = "Not found") -> ApiError:
    return ApiError(status_code=404, code="not_found", message=message)


def conflict(message: str = "Conflict") -> ApiError:
    return ApiError(status_code=409, code="conflict", message=message)


def payment_required(message: str = "Insufficient tokens") -> ApiError:
    return ApiError(status_code=402, code="payment_required", message=message)


def bad_request(message: str = "Bad request", details: Any | None = None) -> ApiError:
    return ApiError(status_code=400, code="bad_request", message=message, details=details)
