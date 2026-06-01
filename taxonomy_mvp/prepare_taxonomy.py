#!/usr/bin/env python3
"""Normalize ESCO/O*NET CSV exports into Azure AI Search upload JSON.

This script is intentionally tolerant of column-name differences between
dataset versions. It maps common ESCO and O*NET columns into the shared
selectry taxonomy schema used by selectry-skills-v2.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


def clean(value: object) -> str:
    return str(value or "").strip()


def split_multi(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s*(?:\||;|,)\s*", value)
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        item = part.strip().strip('"')
        if item and item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result


def first(row: dict[str, str], names: Iterable[str]) -> str:
    lowered = {key.lower().strip(): key for key in row if key is not None}
    for name in names:
        key = lowered.get(name.lower().strip())
        if key is not None and clean(row.get(key)):
            return clean(row.get(key))
    return ""


def stable_id(prefix: str, uri: str, label: str) -> str:
    raw = uri or label
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48]
    return f"{prefix}-{slug or digest}-{digest}"


def normalize_esco(row: dict[str, str]) -> dict[str, object]:
    uri = first(row, ["conceptUri", "concept URI", "URI", "uri"])
    label = first(row, ["preferredLabel", "preferred label", "label", "title"])
    alt_labels = split_multi(first(row, ["altLabels", "alternative labels", "alt labels", "hiddenLabels"]))
    description = first(row, ["description", "scopeNote", "definition"])
    skill_type = first(row, ["skillType", "skill type", "reuseLevel", "conceptType"])
    keywords = split_multi(" ".join([label, first(row, ["broaderConcept", "broader concept", "inScheme"])]))
    return {
        "@search.action": "upload",
        "id": stable_id("esco", uri, label),
        "source": "ESCO",
        "conceptType": "skill",
        "preferredLabel": label,
        "altLabels": alt_labels,
        "description": description,
        "uri": uri,
        "language": "en",
        "skillType": skill_type or "esco_skill",
        "keywords": keywords,
    }


def normalize_onet(row: dict[str, str]) -> dict[str, object]:
    code = first(row, ["Element ID", "element_id", "O*NET-SOC Code", "onetsoc_code", "code"])
    label = first(row, ["Element Name", "Name", "Title", "Commodity Title", "Example", "preferredLabel"])
    description = first(row, ["Description", "Commodity Description", "Task", "description"])
    category = first(row, ["Scale ID", "Category", "Domain Source", "source", "skillType"])
    uri = f"onet://{code}" if code else ""
    return {
        "@search.action": "upload",
        "id": stable_id("onet", uri, label),
        "source": "O*NET",
        "conceptType": "skill",
        "preferredLabel": label,
        "altLabels": [],
        "description": description,
        "uri": uri,
        "language": "en",
        "skillType": category or "onet_skill",
        "keywords": split_multi(label),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(4096)
        file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(file, dialect=dialect))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["ESCO", "ONET"], required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    normalizer = normalize_esco if args.source == "ESCO" else normalize_onet
    docs = []
    for row in read_rows(args.input):
        doc = normalizer(row)
        if doc["preferredLabel"]:
            docs.append(doc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"value": docs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(docs)} documents to {args.output}")


if __name__ == "__main__":
    main()
