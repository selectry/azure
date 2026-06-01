#!/usr/bin/env python3
"""Split Azure AI Search upload JSON into smaller /docs/index batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--prefix", default="batch")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    docs = payload["value"]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for index in range(0, len(docs), args.batch_size):
        batch = {"value": docs[index : index + args.batch_size]}
        number = index // args.batch_size + 1
        output = args.output_dir / f"{args.prefix}-{number:03d}.json"
        output.write_text(json.dumps(batch, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {(len(docs) + args.batch_size - 1) // args.batch_size} batches")


if __name__ == "__main__":
    main()
