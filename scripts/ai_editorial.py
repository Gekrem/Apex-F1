#!/usr/bin/env python3
"""Prepare bilingual APEX F1 editorial drafts from RSS-provided source excerpts.

The script deliberately does not scrape or republish full publisher articles.
It uses only the English headline and short RSS excerpt already stored in news.json.
Every AI-generated item remains a draft and requires human source verification.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
NEWS_FILE = ROOT / "data" / "news.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
MAX_ITEMS = max(1, min(int(os.getenv("AI_MAX_ITEMS", "15")), 30))


def generate(client, item):
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title_en": {"type": "string"},
            "summary_en": {"type": "string"},
            "title_tr": {"type": "string"},
            "summary_tr": {"type": "string"},
            "editorial_notes": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["title_en", "summary_en", "title_tr", "summary_tr", "editorial_notes"]
    }
    instructions = (
        "You are the bilingual Formula 1 desk editor for APEX F1. "
        "Write original, concise editorial headlines and summaries in natural Turkish and English. "
        "Use ONLY the supplied headline and RSS excerpt as factual evidence. "
        "Do not browse, infer missing facts, invent quotes, dates, results, causes, statistics, or context. "
        "Preserve exact driver, team, circuit and series names. If the source excerpt is too thin or ambiguous, "
        "keep the copy cautious and add a clear verification note. Do not translate proper names. "
        "Each summary should be 2-3 sentences, roughly 45-75 words, and must not reproduce source wording. "
        "Return only the requested structured fields. The story will remain unpublished for human review."
    )
    source = {
        "source_name": item.get("source_name", ""),
        "source_headline": item.get("title_en", ""),
        "source_rss_excerpt": item.get("summary_en", ""),
        "source_url": item.get("source_url", "")
    }
    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input="Prepare a bilingual editorial draft from this source data:\n" + json.dumps(source, ensure_ascii=False),
        text={
            "format": {
                "type": "json_schema",
                "name": "apex_f1_bilingual_editorial",
                "strict": True,
                "schema": schema
            }
        },
        max_output_tokens=1200
    )
    result = json.loads(response.output_text)
    for key in ("title_en", "summary_en", "title_tr", "summary_tr"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise ValueError(f"Model returned an empty {key}")
    return result


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY secret is missing.")
    items = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("data/news.json must contain a JSON array.")

    client = OpenAI()
    processed = 0
    skipped = 0
    failures = []

    for item in items:
        if item.get("status") != "draft":
            continue
        # Avoid fabricating copy from a headline alone; require a meaningful RSS excerpt.
        excerpt = (item.get("summary_en") or "").strip()
        headline = (item.get("title_en") or "").strip()
        missing_copy = not all((item.get("title_tr"), item.get("summary_tr"), item.get("title_en"), item.get("summary_en")))
        if not missing_copy:
            continue
        if len(headline) < 12 or len(excerpt) < 45:
            skipped += 1
            continue
        if processed >= MAX_ITEMS:
            break
        try:
            generated = generate(client, item)
            item["title_en"] = generated["title_en"].strip()
            item["summary_en"] = generated["summary_en"].strip()
            item["title_tr"] = generated["title_tr"].strip()
            item["summary_tr"] = generated["summary_tr"].strip()
            item["ai_editorial_status"] = "ready_for_human_review"
            item["ai_editorial_notes"] = generated["editorial_notes"]
            item["ai_model"] = MODEL
            item["ai_generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            # AI never publishes a story.
            item["status"] = "draft"
            processed += 1
            print(f"Prepared bilingual draft: {item.get('id', 'unknown')}")
        except Exception as exc:
            failures.append(f"{item.get('id', 'unknown')}: {type(exc).__name__}: {exc}")
            print(f"FAILED {item.get('id', 'unknown')}: {type(exc).__name__}: {exc}")

    NEWS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"AI drafts prepared: {processed}; skipped for insufficient source excerpt: {skipped}; failures: {len(failures)}")
    if failures:
        print("\n".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
