import hashlib
import hmac
import secrets

from app.domain.ports import PasswordHasher

_SEPARATOR = "$"


class Sha256PasswordHasher(PasswordHasher):
    """SHA-256 hashing as mandated by the technical test, with a per-user random salt."""

    def __init__(self, salt_bytes: int = 16) -> None:
        self._salt_bytes = salt_bytes

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(self._salt_bytes)
        return f"{salt}{_SEPARATOR}{self._digest(salt, password)}"

    def verify(self, password: str, password_hash: str) -> bool:
        salt, separator, expected_digest = password_hash.partition(_SEPARATOR)
        if not separator:
            return False
        return hmac.compare_digest(self._digest(salt, password), expected_digest)

    @staticmethod
    def _digest(salt: str, password: str) -> str:
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
