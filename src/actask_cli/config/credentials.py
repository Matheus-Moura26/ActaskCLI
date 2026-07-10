"""Secure OS-keyring credential storage."""

from typing import Protocol

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from actask_cli.config.profiles import ServerProfile


class CredentialStoreError(RuntimeError):
    """Raised without exposing keyring details or credentials."""


class KeyringBackend(Protocol):
    """The small keyring surface used by the CLI."""

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class CredentialStore:
    """Store sessions in the OS keyring, scoped to server and user."""

    def __init__(self, backend: KeyringBackend = keyring) -> None:
        self._backend = backend

    def get(self, profile: ServerProfile) -> str | None:
        try:
            return self._backend.get_password(*_key(profile))
        except KeyringError as error:
            raise CredentialStoreError("Secure credential store is unavailable.") from error

    def set(self, profile: ServerProfile, session_token: str) -> None:
        try:
            self._backend.set_password(*_key(profile), session_token)
        except KeyringError as error:
            raise CredentialStoreError("Secure credential store is unavailable.") from error

    def delete(self, profile: ServerProfile) -> None:
        try:
            self._backend.delete_password(*_key(profile))
        except PasswordDeleteError:
            return
        except KeyringError as error:
            raise CredentialStoreError("Secure credential store is unavailable.") from error


def _key(profile: ServerProfile) -> tuple[str, str]:
    return (f"actask-cli:{profile.server_url}", profile.email)
