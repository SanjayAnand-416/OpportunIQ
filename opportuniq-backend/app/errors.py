"""Safe, structured errors for optional service integrations."""

from dataclasses import dataclass
from typing import Any


@dataclass(eq=False)
class IntegrationError(Exception):
    """Base exception carrying only client-safe integration metadata."""

    service: str
    message: str
    fallback: str | None = None

    code = "INTEGRATION_ERROR"
    status_code = 502

    def __post_init__(self) -> None:
        super().__init__(self.message)


class ExternalServiceUnavailableError(IntegrationError):
    code = "SERVICE_UNAVAILABLE"
    status_code = 503


class ExternalServiceTimeoutError(IntegrationError):
    code = "SERVICE_TIMEOUT"
    status_code = 504


class ExternalServiceResponseError(IntegrationError):
    code = "INVALID_UPSTREAM_RESPONSE"
    status_code = 502


class IntegrationContractError(IntegrationError):
    code = "INVALID_EXTERNAL_RESULT"
    status_code = 422


def service_error_detail(error: IntegrationError) -> dict[str, Any]:
    """Build the stable error detail retained inside FastAPI's envelope."""
    payload: dict[str, Any] = {
        "code": error.code,
        "message": error.message,
        "service": error.service,
    }
    if error.fallback:
        payload["fallback"] = error.fallback
    return {"error": payload}
