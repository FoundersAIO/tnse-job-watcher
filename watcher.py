"""
TNSE Job Watcher (GitHub Actions version)
Checks https://www.tnse.com/join-our-team/ and sends a Discord alert when the
"Full-Time Employment Opportunities" section changes.

Runs on a schedule via .github/workflows/watch.yml. The last-seen version of
the page is kept in state.json, which the workflow commits back to the repo.

Secrets (repo Settings > Secrets and variables > Actions):
    DISCORD_WEBHOOK   required, Discord webhook URL for alerts
Variables (same page, "Variables" tab), optional:
    WATCH_ALL         set to "true" to watch every section, not just full-time
"""

import hashlib
import re
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.tnse.com/join-our-team/"
SECTION_HEADING = "Full-Time Employment Opportunities"
NEXT_SECTION_HINTS = ("casual employment", "hargrave", "student placement")
STATE_FILE = Path(__file__).with_name("state.json")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
WATCH_ALL = os.environ.get("WATCH_ALL", "").strip().lower() == "true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def log(msg):
    print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC] {msg}", flush=True)


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def clean_lines(text):
    return [norm(ln) for ln in text.splitlines() if ln.strip()]


def extract_section(html, watch_all=False):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    if watch_all:
        anchor = soup.find(lambda t: t.name in ("h1", "h2", "h3")
                           and "join our team" in t.get_text(" ", strip=True).lower())
        root = anchor.find_parent(["main", "article", "section", "div"]) if anchor else None
        root = root or soup.body or soup
        text = "\n".join(clean_lines(root.get_text("\n")))
        links = sorted({a["href"] for a in root.find_all("a", href=True)})
        return text, links

    heading = soup.find(lambda t: t.name in ("h1", "h2", "h3", "h4", "h5", "strong", "p")
                        and SECTION_HEADING.lower() in t.get_text(" ", strip=True).lower())
    if not heading:
        return None, []

    parts, links = [norm(heading.get_text(" ", strip=True))], set()
    for el in heading.find_all_next():
        if el.name in ("h1", "h2", "h3", "h4"):
            t = el.get_text(" ", strip=True).lower()
            if any(h in t for h in NEXT_SECTION_HINTS):
                break
        if el.name == "a" and el.get("href"):
            links.add(el["href"])
        if el.name in ("p", "li", "h3", "h4", "h5", "h6", "a", "span") and not el.find(
                ["p", "li", "div"]):
            t = norm(el.get_text(" ", strip=True))
            if t and t not in parts:
                parts.append(t)
    return "\n".join(parts), sorted(links)


def notify(title, body):
    log(f"ALERT: {title}\n{body}")
    if not DISCORD_WEBHOOK:
        log("DISCORD_WEBHOOK secret not set, so no alert was sent.")
        return
    r = requests.post(DISCORD_WEBHOOK, json={
        "content": f"@everyone **{title}**\n{body[:1700]}\n<{URL}>",
        "allowed_mentions": {"parse": ["everyone"]},
    }, timeout=15)
    log(f"Discord responded {r.status_code}")


def main():
    if "--test-alert" in sys.argv:
        notify("TNSE Watcher test", "Alerts are working 👍")
        return

    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        # Don't spam alerts for a blip; the workflow log shows the error.
        log(f"Couldn't load page: {e}")
        return

    text, links = extract_section(r.text, WATCH_ALL)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    key = "all" if WATCH_ALL else "full_time"

    if text is None:
        if not state.get("missing_alerted"):
            notify("TNSE Watcher: section not found",
                   f"Couldn't find '{SECTION_HEADING}' on the page. The layout may have changed. Check it manually.")
            state["missing_alerted"] = True
            STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
        return
    state.pop("missing_alerted", None)

    digest = hashlib.sha256((text + "\n".join(links)).encode()).hexdigest()
    prev = state.get(key)

    if prev is None:
        log("First run. Saved the current version as the baseline:\n" + text)
    elif prev["hash"] != digest:
        still_empty = "no full-time employment opportunities" in text.lower()
        title = ("🚨 TNSE full-time job posted!" if not WATCH_ALL and not still_empty
                 else "🚨 TNSE careers page changed")
        new_links = [l for l in links if l not in prev.get("links", [])]
        body = text + ("\n\nNew links:\n" + "\n".join(new_links) if new_links else "")
        notify(title, body)
    else:
        log("No change.")
        return

    # No timestamps in here, so the file (and a commit) only changes when the page does.
    state[key] = {"hash": digest, "text": text, "links": links}
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    main()
