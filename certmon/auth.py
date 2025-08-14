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
from __future__ import annotations

import os
import hmac
import hashlib
from typing import Tuple


def hash_password(password: str, iterations: int = 200_000) -> Tuple[str, int, str, str]:
	"""Hash password using PBKDF2-HMAC-SHA256.

	Returns (algo, iterations, salt_hex, hash_hex)
	"""
	salt = os.urandom(16)
	dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
	return ("pbkdf2_sha256", iterations, salt.hex(), dk.hex())


def verify_password(password: str, algo: str, iterations: int, salt_hex: str, hash_hex: str) -> bool:
	if algo != "pbkdf2_sha256":
		return False
	salt = bytes.fromhex(salt_hex)
	expected = bytes.fromhex(hash_hex)
	dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
	return hmac.compare_digest(dk, expected)


