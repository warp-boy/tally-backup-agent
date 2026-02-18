from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

import base64


def derive_key_from_password(password: bytes, salt: bytes, iterations: int = 200_000) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password)


def encrypt_file(in_path: Path, out_path: Path, password: Optional[bytes] = None) -> None:
    """Encrypts file using AES-256-GCM. The file format:
    [salt(16)][nonce(12)][ciphertext]
    Password should be provided as bytes. If not provided, raise.
    """
    if password is None:
        raise ValueError("Encryption password/key must be provided")

    salt = os.urandom(16)
    key = derive_key_from_password(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)

    with open(in_path, "rb") as f:
        plaintext = f.read()

    ct = aesgcm.encrypt(nonce, plaintext, None)

    with open(out_path, "wb") as f:
        f.write(salt + nonce + ct)


def decrypt_file(enc_path: Path, out_path: Path, password: bytes) -> None:
    data = enc_path.read_bytes()
    salt = data[:16]
    nonce = data[16:28]
    ct = data[28:]
    key = derive_key_from_password(password, salt)
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct, None)
    out_path.write_bytes(pt)
