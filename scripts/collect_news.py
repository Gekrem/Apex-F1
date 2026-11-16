#!/usr/bin/env python3
"""Collect Formula 1 RSS headlines as unpublished editorial drafts."""
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS_FILE = ROOT / "data" / "news.json"
FEEDS = [
    ("Formula 1", "https://www.formula1.com/content/fom-website/en/latest/all.xml", False),
    ("Formula1.com Latest", "https://www.formula1.com/rss/news/latest.rss", False),
    ("BBC Sport F1", "https://feeds.bbci.co.uk/sport/formula1/rss.xml", False),
    ("Autosport", "https://www.autosport.com/rss/f1/news/", False),
    ("Autosport F1", "https://www.autosport.com/rss/feed/f1", False),
    ("FIA", "https://www.fia.com/rss/news", True),
]
F1_TERMS = re.compile(
    r"formula\\s*1|\\bf1\\b|grand prix|fia|paddock|pit stop|pole position|"
    r"sprint race|drivers'? championship|constructors'? championship|"
    r"formula one|racing bulls|mclaren|ferrari|mercedes|red bull|aston martin|williams|alpine|haas|audi",
    re.I,
)


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unescape(value)
    return re.sub(r"\\s+", " ", value).strip()[:500]


def parse_date(value: str) -> str:
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        except Exception:
            return ""


def fetch_feed(name: str, url: str, f1_only: bool):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; APEX-F1-NewsBot/1.1; +https://gekrem.github.io/Apex-F1/)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(3_000_000)
    root = ET.fromstring(raw)
    found = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() not in ("item", "entry"):
            continue
        fields = {}
        for child in list(node):
            key = child.tag.rsplit("}", 1)[-1].lower()
            if key == "link":
                href = child.attrib.get("href", "").strip()
                rel = child.attrib.get("rel", "alternate")
                text_value = (child.text or "").strip()
                if rel == "alternate" or not fields.get("link"):
                    fields["link"] = href or text_value
            elif key in (
                "title", "description", "summary", "content", "encoded",
                "pubdate", "published", "updated", "date", "issued",
            ):
                fields[key] = "".join(child.itertext()).strip()
        title = clean_html(fields.get("title", ""))
        link = fields.get("link", "").strip()
        summary = clean_html(
            fields.get("description") or fields.get("summary") or
            fields.get("encoded") or fields.get("content") or ""
        )
        if not title or not link or not link.startswith("https://"):
            continue
        if f1_only and not F1_TERMS.search(title + " " + summary):
            continue
        published = parse_date(
            fields.get("pubdate") or fields.get("published") or
            fields.get("updated") or fields.get("date") or fields.get("issued") or ""
        )
        key = hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]
        found.append({
            "id": key,
            "status": "draft",
            "category": "F1 NEWS",
            "title_en": title,
            "summary_en": summary,
            "title_tr": "",
            "summary_tr": "",
            "source_name": name,
            "source_url": link,
            "published_at": published,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        })
    return found


def main():
    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        original_text = NEWS_FILE.read_text(encoding="utf-8")
        existing = json.loads(original_text)
    except (FileNotFoundError, json.JSONDecodeError):
        original_text = ""
        existing = []
    if not isinstance(existing, list):
        raise ValueError("data/news.json must contain a JSON array.")

    by_url = {item.get("source_url"): item for item in existing if item.get("source_url")}
    total = 0
    successful_feeds = 0
    errors = []
    for name, url, f1_only in FEEDS:
        try:
            items = fetch_feed(name, url, f1_only)
            successful_feeds += 1
            added = 0
            for item in items:
                if item["source_url"] not in by_url:
                    by_url[item["source_url"]] = item
                    total += 1
                    added += 1
            print(f"[OK] {name}: {len(items)} entries read, {added} new drafts.")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"[WARN] {name}: {type(exc).__name__}: {exc}")

    if successful_feeds == 0:
        raise RuntimeError("All RSS feeds failed. No news file was changed.")

    combined = list(by_url.values())
    combined.sort(
        key=lambda item: item.get("published_at") or item.get("collected_at") or "",
        reverse=True,
    )
    published = [item for item in combined if item.get("status") == "published"]
    drafts = [item for item in combined if item.get("status") != "published"][:80]
    output = json.dumps(published + drafts, ensure_ascii=False, indent=2) + "\\n"

    if output != original_text:
        NEWS_FILE.write_text(output, encoding="utf-8")
        print("data/news.json updated.")
    else:
        print("No file changes: every discovered story was already present.")

    print(
        f"SUMMARY: {total} new drafts; {successful_feeds}/{len(FEEDS)} feeds successful; "
        f"{len(published)} published; {len(drafts)} drafts retained."
    )
    if errors:
        print("Feed warnings:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
