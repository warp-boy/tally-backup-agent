from __future__ import annotations

import os
from pathlib import Path
import winreg
from typing import Optional

from .logging_config import setup_logging

logger = setup_logging()


class TallyNotFoundError(Exception):
    pass


def find_tally_install_path() -> Path:
    """Attempt to locate TallyPrime install directory.

    Steps:
    - Check Windows registry for common install keys
    - Fallback to common Program Files locations
    - Raise TallyNotFoundError if not found
    """
    # Registry lookup (HKLM) for TallyPrime
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tally\TallyPrime") as key:
            try:
                install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                if install_dir and Path(install_dir).exists():
                    logger.info("Found Tally install via registry: %s", install_dir)
                    return Path(install_dir)
            except FileNotFoundError:
                pass
    except OSError:
        # Not running on Windows or key missing
        logger.debug("Registry lookup not available or failed")

    # Fallback common locations
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "TallyPrime",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "TallyPrime",
        Path("C:/TallyPrime"),
    ]

    for p in candidates:
        if p.exists():
            logger.info("Found Tally install at %s", p)
            return p

    raise TallyNotFoundError("TallyPrime installation not found in registry or common paths")


def locate_tally_ini(install_path: Optional[Path] = None) -> Path:
    """Locate tally.ini. If install_path provided, search there; otherwise search discovered install."""
    if install_path is None:
        install_path = find_tally_install_path()

    # Common location relative to install
    possible = [install_path / "tally.ini", install_path / "Tally.ini", install_path / "tally\tally.ini"]
    for p in possible:
        if p.exists():
            logger.info("Found tally.ini at %s", p)
            return p

    # Search entire Program Files for tally.ini (last resort)
    for root in [Path("C:/"), Path(os.environ.get("ProgramFiles", "C:\\Program Files"))]:
        for p in root.rglob("tally.ini"):
            logger.info("Found tally.ini via rglob at %s", p)
            return p

    raise FileNotFoundError("tally.ini not found for TallyPrime")
