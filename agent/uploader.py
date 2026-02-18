from __future__ import annotations

import time
import math
from pathlib import Path
import logging
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.s3.transfer import TransferConfig

from .logging_config import setup_logging

logger = setup_logging()


def upload_file_multipart(file_path: Path, bucket: str, key: str, region: Optional[str] = None, retries: int = 5) -> None:
    s3 = boto3.client("s3", region_name=region)

    config = TransferConfig(multipart_threshold=50 * 1024 * 1024, multipart_chunksize=16 * 1024 * 1024)

    attempt = 0
    while True:
        try:
            logger.info("Uploading %s to s3://%s/%s", file_path, bucket, key)
            s3.upload_file(str(file_path), bucket, key, Config=config)
            logger.info("Upload successful: s3://%s/%s", bucket, key)
            return
        except (BotoCoreError, ClientError) as e:
            attempt += 1
            if attempt > retries:
                logger.exception("Upload failed after %d attempts", attempt)
                raise
            backoff = (2 ** attempt) + (math.sin(attempt) * 0.1)
            logger.warning("Upload failed (attempt %d). Retrying in %.1f seconds: %s", attempt, backoff, e)
            time.sleep(backoff)
