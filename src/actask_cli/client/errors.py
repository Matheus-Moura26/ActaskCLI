"""Public API client errors and stable exit codes."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Stable command exit codes defined by the CLI specification."""

    SUCCESS = 0
    INVALID_INPUT = 2
    NOT_AUTHENTICATED = 3
    FORBIDDEN = 4
    NOT_FOUND = 5
    CONFLICT = 6
    NETWORK_OR_SERVER = 7


class ApiError(RuntimeError):
    """A non-sensitive error returned by the Actask API client."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.status_code = status_code
        self.request_id = request_id


class InvalidInputError(ApiError):
    def __init__(self, status_code: int, request_id: str | None) -> None:
        super().__init__(
            "Request input is invalid.", ExitCode.INVALID_INPUT, status_code, request_id
        )


class UnauthenticatedError(ApiError):
    def __init__(self, request_id: str | None) -> None:
        super().__init__(
            "Session is invalid or expired. Run 'actask login'.",
            ExitCode.NOT_AUTHENTICATED,
            401,
            request_id,
        )


class ForbiddenError(ApiError):
    def __init__(self, request_id: str | None) -> None:
        super().__init__(
            "You do not have permission to perform this action.",
            ExitCode.FORBIDDEN,
            403,
            request_id,
        )


class NotFoundError(ApiError):
    def __init__(self, request_id: str | None) -> None:
        super().__init__("Requested resource was not found.", ExitCode.NOT_FOUND, 404, request_id)


class ConflictError(ApiError):
    def __init__(self, request_id: str | None) -> None:
        super().__init__(
            "Request conflicts with current Actask state.", ExitCode.CONFLICT, 409, request_id
        )


class MethodNotAllowedError(ApiError):
    def __init__(self, request_id: str | None) -> None:
        super().__init__(
            "Actask API contract error: this CLI command is not supported by the server endpoint.",
            ExitCode.NETWORK_OR_SERVER,
            405,
            request_id,
        )


class NetworkError(ApiError):
    def __init__(self) -> None:
        super().__init__("Unable to reach Actask server.", ExitCode.NETWORK_OR_SERVER)


class ServerError(ApiError):
    def __init__(self, status_code: int | None = None, request_id: str | None = None) -> None:
        super().__init__(
            "Actask server failed to process the request.",
            ExitCode.NETWORK_OR_SERVER,
            status_code,
            request_id,
        )
