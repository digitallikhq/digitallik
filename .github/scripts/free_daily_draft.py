import os, json, re
from datetime import datetime, timezone
from dateutil import parser as dtparser
import feedparser

DRAFTS_DIR = "_drafts"
STATE_PATH = "data/daily_state.json"
X_HANDLE = "@DigitallikHQ"

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
]

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_urls": []}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def clean(text):
    return re.sub(r"\s+", " ", (text or "").strip())

def fetch_items():
    items = []
    for feed in RSS_FEEDS:
        parsed = feedparser.parse(feed)
        for e in parsed.entries[:12]:
            url = getattr(e, "link", None)
            title = clean(getattr(e, "title", None))
            summary = clean(getattr(e, "summary", ""))[:240]
            published = getattr(e, "published", None) or getattr(e, "updated", None)
            if not url or not title:
                continue
            try:
                pub_dt = dtparser.parse(published).astimezone(timezone.utc) if published else datetime.now(timezone.utc)
            except Exception:
                pub_dt = datetime.now(timezone.utc)
            items.append({"title": title, "url": url, "summary": summary, "published_utc": pub_dt.isoformat()})
    items.sort(key=lambda x: x["published_utc"], reverse=True)
    return items

def pick_top(items, seen_urls, n=5):
    picked = []
    for it in items:
        if it["url"] in seen_urls:
            continue
        picked.append(it)
        if len(picked) >= n:
            break
    return picked

def build_draft(top_items):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Daily Crypto Brief — {today}"
    path = f"{DRAFTS_DIR}/{today}-daily-crypto-brief.md"

    sources_md = "\n".join([
        f"- **{it['title']}**  \n  {it['url']}\n  _Note:_ {it['summary']}"
        for it in top_items
    ])

    x_line = ""
    if top_items:
        a = top_items[0]["title"]
        b = top_items[1]["title"] if len(top_items) > 1 else ""
        x_line = f"{X_HANDLE} Daily brief: {a}"
        if b:
            x_line += f" | Also: {b}"
        x_line += " #Bitcoin #Crypto"
        x_line = x_line[:260]

    content = f"""---
layout: post
title: "{title}"
description: "Daily brief with the top crypto stories + Digitallik angles."
category: crypto
tags: [daily, brief]
date: {today}
---

## What happened (sources)
{sources_md}

---

## Rewrite in ChatGPT (free)
- Write 1 strong takeaway paragraph
- Add 5 key bullets
- Add “What to watch next (24–72h)”
- Add 1 products block (2 categories)
- End with: Follow @DigitallikHQ

---

## X draft
- {x_line}
"""
    return path, content, [it["url"] for it in top_items]

def main():
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    state = load_state()
    items = fetch_items()
    top = pick_top(items, state.get("last_urls", []), n=5) or items[:5]

    path, content, urls = build_draft(top)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    state["last_urls"] = urls
    state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

if __name__ == "__main__":
    main()
