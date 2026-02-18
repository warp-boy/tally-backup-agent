import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str | Path = None, level: int = logging.INFO) -> logging.Logger:
    if log_dir is None:
        log_dir = Path.home() / "tally_backup_agent" / "logs"
    else:
        log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agent.log"

    logger = logging.getLogger("tally_agent")
    logger.setLevel(level)

    if not logger.handlers:
        fh = RotatingFileHandler(str(log_file), maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    return logger
