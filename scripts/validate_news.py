#!/usr/bin/env python3
"""Validate APEX F1 editorial data before it can be merged or published."""
import json
import sys
from pathlib import Path

path = Path("data/news.json")
try:
    news = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: data/news.json is not valid JSON: {exc}")
    sys.exit(1)

if not isinstance(news, list):
    print("ERROR: top-level JSON value must be an array.")
    sys.exit(1)

errors = []
seen_ids = set()
seen_urls = set()

for index, item in enumerate(news, start=1):
    where = f"item #{index}"
    if not isinstance(item, dict):
        errors.append(f"{where}: must be an object")
        continue

    for field in ("id", "title_en", "source_name", "source_url", "status"):
        if not str(item.get(field, "")).strip():
            errors.append(f"{where}: missing {field}")

    item_id = str(item.get("id", "")).strip()
    if item_id:
        if item_id in seen_ids:
            errors.append(f"{where}: duplicate id {item_id}")
        seen_ids.add(item_id)

    url = str(item.get("source_url", "")).strip()
    if url:
        if not url.startswith("https://"):
            errors.append(f"{where}: source_url must use HTTPS")
        if url in seen_urls:
            errors.append(f"{where}: duplicate source_url")
        seen_urls.add(url)

    status = item.get("status")
    if status not in ("draft", "published"):
        errors.append(f"{where}: status must be draft or published")

    if status == "published":
        for field in ("title_tr", "title_en", "summary_tr", "summary_en"):
            if not str(item.get(field, "")).strip():
                errors.append(f"{where}: published item is missing {field}")

if errors:
    print("APEX F1 editorial validation FAILED:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

drafts = sum(1 for item in news if item.get("status") == "draft")
published = len(news) - drafts
print(f"APEX F1 editorial validation passed: {len(news)} items, {drafts} drafts, {published} published.")
