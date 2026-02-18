from __future__ import annotations

import os
from pathlib import Path

from .service import run_console


def main():
    # CLI entry used by service or during development
    import argparse

    parser = argparse.ArgumentParser(description="TallyPrime Backup Agent")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--client-id", required=True, help="Client identifier")
    parser.add_argument("--password", required=False, help="Encryption password or key (env preferred)")
    parser.add_argument("--debounce", type=int, default=int(os.environ.get("DEBOUNCE_SECONDS", 120)))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION"))
    args = parser.parse_args()

    pw = args.password.encode() if args.password else os.environ.get("TALLY_AGENT_KEY", "").encode()
    if not pw:
        raise SystemExit("Encryption password must be provided via --password or TALLY_AGENT_KEY environment variable")

    run_console(args.bucket, args.client_id, pw, debounce_seconds=args.debounce, region=args.region)


if __name__ == "__main__":
    main()
