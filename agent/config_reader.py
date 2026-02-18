from __future__ import annotations

import configparser
from pathlib import Path
from typing import Optional

from .logging_config import setup_logging

logger = setup_logging()


class ConfigError(Exception):
    pass


def read_tally_ini(ini_path: Path) -> dict:
    """Parse tally.ini and return keys as dict. Ensures 'Data' path extraction."""
    if not ini_path.exists():
        raise ConfigError(f"INI file not found: {ini_path}")

    parser = configparser.RawConfigParser()
    parser.read(ini_path, encoding="utf-8", )

    # tally.ini often uses no section; fall back to parsing manually
    data_path = None
    try:
        # Try standard parsing
        for section in parser.sections():
            if parser.has_option(section, "Data"):
                data_path = parser.get(section, "Data")
                break
    except Exception:
        pass

    if data_path is None:
        # Fallback: raw search
        text = ini_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.strip().startswith("Data="):
                _, v = line.split("=", 1)
                data_path = v.strip()
                break

    if not data_path:
        raise ConfigError("Data path not found in tally.ini")

    # Normalize path
    data_path = data_path.replace('\\\\', '\\')
    data_path = data_path.replace('/', '\\')
    return {"data_path": data_path}
