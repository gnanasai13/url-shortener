from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse

class AppException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_server_error"
    message = "An unexpected error occurred."
    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}

class Unauthorized(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Authentication is required."

class InvalidCredentials(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_credentials"
    message = "Invalid email or password."

class UserAlreadyExists(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = "user_already_exists"
    message = "A user with this username or email already exists."

class URLNotFound(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "url_not_found"
    message = "Short URL was not found."

class ExpiredURL(AppException):
    status_code = status.HTTP_410_GONE
    code = "expired_url"
    message = "This short URL has expired."

class InactiveURL(AppException):
    status_code = status.HTTP_410_GONE
    code = "inactive_url"
    message = "This short URL is inactive."

class LinkPasswordRequired(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "link_password_required"
    message = "Password is required for this short URL."

class InvalidLinkPassword(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_link_password"
    message = "Invalid short URL password."

class AliasAlreadyExists(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = "alias_already_exists"
    message = "This custom alias is already in use."

class InvalidURLUpdate(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_url_update"
    message = "No URL fields were provided for update."

class RateLimitExceeded(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_exceeded"
    message = "Too many requests. Please try again later."

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})
