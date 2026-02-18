from __future__ import annotations

import threading
import time
import sys
from pathlib import Path
from typing import Optional

from .logging_config import setup_logging
from .detector import locate_tally_ini, find_tally_install_path
from .config_reader import read_tally_ini
from .validator import validate_data_dir
from .watcher import Watcher
from .backup_engine import create_encrypted_backup
from .uploader import upload_file_multipart

logger = setup_logging()


class AgentService:
    def __init__(self, s3_bucket: str, client_id: str, encryption_password: bytes, debounce_seconds: int = 120, region: Optional[str] = None):
        self.s3_bucket = s3_bucket
        self.client_id = client_id
        self.encryption_password = encryption_password
        self.debounce_seconds = debounce_seconds
        self.region = region
        self._watcher: Optional[Watcher] = None
        self._running = False

    def _backup_and_upload(self, company_dir: Path):
        try:
            # Local temp backup dir
            dest = Path.home() / "tally_backups" / self.client_id
            enc = create_encrypted_backup(company_dir, self.encryption_password, dest)

            # Build S3 key: client-id/company-name/YYYY/MM/
            ts = time.gmtime()
            y = time.strftime("%Y", ts)
            m = time.strftime("%m", ts)
            key = f"{self.client_id}/{company_dir.name}/{y}/{m}/{enc.name}"
            upload_file_multipart(enc, self.s3_bucket, key, region=self.region)
        except Exception as e:
            logger.exception("Failed backup/upload for %s: %s", company_dir, e)

    def start(self):
        self._running = True
        try:
            install = find_tally_install_path()
            ini = locate_tally_ini(install)
            cfg = read_tally_ini(ini)
            data_path = Path(cfg["data_path"])
            companies = validate_data_dir(data_path)
        except Exception as e:
            logger.exception("Startup validation failed: %s", e)
            raise

        self._watcher = Watcher(data_path, backup_callback=self._backup_and_upload, debounce_seconds=self.debounce_seconds)
        self._watcher.start()
        logger.info("Agent service started")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received; stopping")
            self.stop()

    def stop(self):
        self._running = False
        if self._watcher:
            self._watcher.stop()
        logger.info("Agent service stopped")


def run_console(s3_bucket: str, client_id: str, password: bytes, debounce_seconds: int = 120, region: Optional[str] = None):
    svc = AgentService(s3_bucket, client_id, password, debounce_seconds=debounce_seconds, region=region)
    svc.start()


if __name__ == "__main__":
    # Simple CLI entry for debugging
    import argparse

    parser = argparse.ArgumentParser(description="Tally Backup Agent (console)")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--client", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--debounce", type=int, default=120)
    parser.add_argument("--region", default=None)
    args = parser.parse_args()
    run_console(args.bucket, args.client, args.password.encode(), debounce_seconds=args.debounce, region=args.region)
