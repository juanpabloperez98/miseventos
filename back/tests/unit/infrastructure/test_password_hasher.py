import hashlib

from app.infrastructure.security import Sha256PasswordHasher


def test_hash_is_salted_sha256_and_never_contains_the_password() -> None:
    hasher = Sha256PasswordHasher()

    password_hash = hasher.hash("s3cret-password")
    salt, digest = password_hash.split("$")

    assert "s3cret-password" not in password_hash
    assert digest == hashlib.sha256(f"{salt}s3cret-password".encode()).hexdigest()


def test_same_password_produces_different_hashes() -> None:
    hasher = Sha256PasswordHasher()

    assert hasher.hash("s3cret-password") != hasher.hash("s3cret-password")


def test_verify_accepts_correct_password_only() -> None:
    hasher = Sha256PasswordHasher()
    password_hash = hasher.hash("s3cret-password")

    assert hasher.verify("s3cret-password", password_hash)
    assert not hasher.verify("wrong-password", password_hash)


def test_verify_rejects_malformed_hash() -> None:
    assert not Sha256PasswordHasher().verify("s3cret-password", "no-separator")
