#!/usr/bin/env python3
"""
Submit a generated hunt-prediction payload to an HTTP ingestion endpoint.

Examples:
  export PREDICTION_ENGINE_URL="https://your-engine.example.com/ingest"
  export PREDICTION_ENGINE_TOKEN="..."
  python3 submit_to_engine.py --payload data/hunt_engine_ingestion_2024.json

  python3 submit_to_engine.py --engine-url "$PREDICTION_ENGINE_URL" \
      --token "$PREDICTION_ENGINE_TOKEN" \
      --payload hunt_prediction_ingestion_2024.zip \
      --content-type application/zip
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def guess_content_type(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return "application/json"
    if path.suffix.lower() == ".zip":
        return "application/zip"
    if path.suffix.lower() == ".csv":
        return "text/csv"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit hunt prediction ingestion payload to an engine endpoint.")
    parser.add_argument("--engine-url", default=os.environ.get("PREDICTION_ENGINE_URL"),
                        help="Full HTTP endpoint URL for the prediction engine ingestion endpoint.")
    parser.add_argument("--token", default=os.environ.get("PREDICTION_ENGINE_TOKEN"),
                        help="Bearer token or API token. Defaults to PREDICTION_ENGINE_TOKEN.")
    parser.add_argument("--payload", default="data/hunt_engine_ingestion_2024.json",
                        help="Payload file to submit. Default: data/hunt_engine_ingestion_2024.json")
    parser.add_argument("--content-type", default=None,
                        help="Override Content-Type. Defaults based on file extension.")
    parser.add_argument("--header", action="append", default=[],
                        help="Additional HTTP header as Name=Value. May be supplied multiple times.")
    parser.add_argument("--dry-run", action="store_true", help="Validate request inputs without sending.")
    args = parser.parse_args()

    if not args.engine_url:
        print("ERROR: missing --engine-url or PREDICTION_ENGINE_URL", file=sys.stderr)
        return 2

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"ERROR: payload not found: {payload_path}", file=sys.stderr)
        return 2

    data = payload_path.read_bytes()
    content_type = args.content_type or guess_content_type(payload_path)
    headers = {
        "Content-Type": content_type,
        "X-Dataset-Name": "utah_hunt_prediction_ingestion_2024",
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    for header in args.header:
        if "=" not in header:
            print(f"ERROR: --header must be Name=Value, got: {header}", file=sys.stderr)
            return 2
        name, value = header.split("=", 1)
        headers[name.strip()] = value.strip()

    if args.dry_run:
        print(json.dumps({
            "engine_url": args.engine_url,
            "payload": str(payload_path),
            "bytes": len(data),
            "content_type": content_type,
            "headers": sorted(headers.keys()),
        }, indent=2))
        return 0

    req = urllib.request.Request(args.engine_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(json.dumps({
                "status": resp.status,
                "reason": resp.reason,
                "response": body[:5000],
            }, indent=2))
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({
            "status": e.code,
            "reason": e.reason,
            "response": body[:5000],
        }, indent=2), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
