"""Password hashing helpers (pbkdf2_hmac)."""
from __future__ import annotations

import hashlib
import secrets
from typing import Tuple


def hash_password(password: str, salt: str | None = None, iterations: int = 100_000) -> Tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return dk.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str, iterations: int = 100_000) -> bool:
    dk, _ = hash_password(password, salt=salt, iterations=iterations)
    return secrets.compare_digest(dk, stored_hash)

