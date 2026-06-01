#!/usr/bin/env python3
"""Upload prepared JSON batches to Azure AI Search.

Usage:
  AZURE_SEARCH_ADMIN_KEY=... python3 taxonomy_mvp/upload_to_azure_search.py \
    --index selectry-skills-v2 \
    --input taxonomy_mvp/selectry-local-skills.json

  AZURE_SEARCH_ADMIN_KEY=... python3 taxonomy_mvp/upload_to_azure_search.py \
    --index selectry-skills-v2 \
    --input-dir taxonomy_mvp/out/esco-en-batches
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


SERVICE = "https://azureaisearchselectry.search.windows.net"
API_VERSION = "2024-07-01"


def upload(path: Path, index: str, api_key: str) -> None:
    url = f"{SERVICE}/indexes/{index}/docs/index?api-version={API_VERSION}"
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            print(f"{path.name}: {response.status}")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path.name}: HTTP {error.code}: {body}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-dir", type=Path)
    args = parser.parse_args()

    api_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    if not api_key:
        print("Set AZURE_SEARCH_ADMIN_KEY first.", file=sys.stderr)
        sys.exit(2)

    if bool(args.input) == bool(args.input_dir):
        print("Pass exactly one of --input or --input-dir.", file=sys.stderr)
        sys.exit(2)

    paths = [args.input] if args.input else sorted(args.input_dir.glob("*.json"))
    for path in paths:
        upload(path, args.index, api_key)


if __name__ == "__main__":
    main()
