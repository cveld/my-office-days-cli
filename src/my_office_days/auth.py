from __future__ import annotations

import os

import keyring

SERVICE = "my-office-days-cli"
TOKEN_ACCOUNT = "default"
ENCRYPTION_KEY_ACCOUNT = "encryption-key"


def get_token() -> str | None:
    return os.environ.get("MOD_TOKEN") or keyring.get_password(SERVICE, TOKEN_ACCOUNT)


def set_token(token: str) -> None:
    keyring.set_password(SERVICE, TOKEN_ACCOUNT, token)


def delete_token() -> bool:
    try:
        keyring.delete_password(SERVICE, TOKEN_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        return False
    return True


def get_encryption_key() -> str | None:
    return keyring.get_password(SERVICE, ENCRYPTION_KEY_ACCOUNT)


def set_encryption_key(encryption_key: str) -> None:
    keyring.set_password(SERVICE, ENCRYPTION_KEY_ACCOUNT, encryption_key)


def delete_encryption_key() -> bool:
    try:
        keyring.delete_password(SERVICE, ENCRYPTION_KEY_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        return False
    return True
