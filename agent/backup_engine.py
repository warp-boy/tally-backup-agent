from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import tarfile
import time
import hashlib
from typing import Iterable

from .logging_config import setup_logging
from .encryption import encrypt_file

logger = setup_logging()


def _hash_dir(path: Path) -> str:
    h = hashlib.sha256()
    for fp in sorted([p for p in path.rglob("*") if p.is_file()], key=lambda p: str(p)):
        h.update(str(fp.relative_to(path)).encode())
        h.update(str(fp.stat().st_mtime).encode())
        h.update(str(fp.stat().st_size).encode())
    return h.hexdigest()


def safe_copy_company(src: Path, dst_root: Path) -> Path:
    dst = dst_root / src.name
    if dst.exists():
        shutil.rmtree(dst)
    logger.info("Copying %s -> %s", src, dst)
    shutil.copytree(src, dst, symlinks=False)
    return dst


def compress_directory(src: Path, out_file: Path) -> None:
    logger.info("Creating archive %s from %s", out_file, src)
    with tarfile.open(out_file, "w:gz") as tar:
        tar.add(src, arcname=src.name)


def create_encrypted_backup(company_dir: Path, password: bytes, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        copied = safe_copy_company(company_dir, td_path)

        # Basic integrity: hash before compression
        before_hash = _hash_dir(copied)

        archive = dest_dir / f"{company_dir.name}.tar.gz"
        compress_directory(copied, archive)

        # Optional verify by decompressing to temp and hashing (skipped expensive step for big datasets)
        enc_path = dest_dir / f"backup_{time.strftime('%Y-%m-%d_%H-%M')}_{company_dir.name}.enc"
        encrypt_file(archive, enc_path, password)

        logger.info("Created encrypted backup %s (source-hash=%s)", enc_path, before_hash)
        return enc_path
