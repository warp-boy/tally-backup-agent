from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import List

from .logging_config import setup_logging

logger = setup_logging()


class ValidationError(Exception):
    pass


def normalize_path(p: str) -> Path:
    # Accept UNC paths and Windows drive letters
    return Path(p)


def check_permissions(p: Path) -> bool:
    # Basic read/write check: attempt to list and create a temp file
    try:
        if not p.exists():
            raise ValidationError(f"Path does not exist: {p}")
        testf = p / ".tally_perm_test"
        with open(testf, "w") as f:
            f.write("ok")
        testf.unlink()
        return True
    except PermissionError as e:
        raise ValidationError(f"Permission error on {p}: {e}")
    except Exception:
        # If network paths may block, still allow but warn
        logger.warning("Non-fatal permission check failure for %s", p)
        return True


def validate_data_dir(data_path: Path) -> List[Path]:
    p = Path(data_path)
    if not p.exists():
        raise ValidationError(f"Data directory not found: {p}")

    # If UNC path (starts with \\), warn
    if str(p).startswith("\\\\"):
        logger.warning("Data path appears to be a network share. Agent should preferably run on the server hosting the share.")

    check_permissions(p)

    # Companies in Tally are usually numeric directories
    companies = [d for d in p.iterdir() if d.is_dir() and d.name.isdigit()]
    if not companies:
        raise ValidationError(f"No numeric company folders found under {p}")

    logger.info("Validated data directory %s with %d companies", p, len(companies))
    return companies
