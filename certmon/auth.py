from __future__ import annotations

import binascii
import os
from hashlib import pbkdf2_hmac


PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16


def generate_salt() -> bytes:
	return os.urandom(SALT_BYTES)


def hash_password(plain_password: str, salt: bytes | None = None) -> tuple[str, str]:
	if salt is None:
		salt = generate_salt()
	dk = pbkdf2_hmac(PBKDF2_ALGORITHM, plain_password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
	return binascii.hexlify(dk).decode("ascii"), binascii.hexlify(salt).decode("ascii")


def verify_password(plain_password: str, password_hex: str, salt_hex: str) -> bool:
	try:
		salt = binascii.unhexlify(salt_hex.encode("ascii"))
		dk = pbkdf2_hmac(PBKDF2_ALGORITHM, plain_password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
		return binascii.hexlify(dk).decode("ascii") == password_hex
	except Exception:
		return False
