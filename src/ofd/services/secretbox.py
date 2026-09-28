"""Symmetric encryption for third-party credentials the platform must be able to use later (for
example a customer's WhatsApp gateway API key). Keyed from SECRET_KEY, so a database dump alone does
not expose them. Rotating SECRET_KEY makes existing values unreadable (they must be re-entered).
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ofd.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(b"ofd-secretbox:" + settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credential cannot be decrypted (was SECRET_KEY changed?)") from exc
