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
    ("FIA", "https://www.fia.com/rss/news", True),
    ("Autosport", "https://www.autosport.com/rss/f1/news/", False),
]
F1_TERMS = re.compile(r"formula\s*1|\bf1\b|grand prix|grand prix|fia|paddock|pit stop|pole position|sprint race|drivers'? championship|constructors'? championship", re.I)


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()[:500]


def parse_date(value: str) -> str:
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        return ""


def fetch_feed(name: str, url: str, f1_only: bool):
    request = urllib.request.Request(url, headers={"User-Agent": "APEX-F1-NewsBot/1.0 (editorial draft collector)"})
    with urllib.request.urlopen(request, timeout=25) as response:
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
                fields[key] = child.attrib.get("href") or (child.text or "").strip()
            elif key in ("title", "description", "summary", "content", "pubdate", "published", "updated"):
                fields[key] = "".join(child.itertext()).strip()
        title = clean_html(fields.get("title", ""))
        link = fields.get("link", "").strip()
        summary = clean_html(fields.get("description") or fields.get("summary") or fields.get("content") or "")
        if not title or not link or not link.startswith("https://"):
            continue
        if f1_only and not F1_TERMS.search(title + " " + summary):
            continue
        published = parse_date(fields.get("pubdate") or fields.get("published") or fields.get("updated") or "")
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
        existing = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    by_url = {item.get("source_url"): item for item in existing if item.get("source_url")}
    total = 0
    errors = []
    for name, url, f1_only in FEEDS:
        try:
            for item in fetch_feed(name, url, f1_only):
                if item["source_url"] not in by_url:
                    by_url[item["source_url"]] = item
                    total += 1
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    combined = list(by_url.values())
    combined.sort(key=lambda item: item.get("published_at") or item.get("collected_at") or "", reverse=True)
    # Retain all published stories and the 80 newest drafts.
    published = [item for item in combined if item.get("status") == "published"]
    drafts = [item for item in combined if item.get("status") != "published"][:80]
    NEWS_FILE.write_text(json.dumps(published + drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"New drafts collected: {total}; total published: {len(published)}; drafts retained: {len(drafts)}")
    if errors:
        print("Feed warnings (other feeds were still processed):")
        for error in errors:
            print(f"- {error}")

if __name__ == "__main__":
    main()
