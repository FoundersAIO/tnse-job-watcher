"""
TNSE Job Watcher (GitHub Actions version)
Checks https://www.tnse.com/join-our-team/ and sends a Discord alert whenever
the page's content changes (any section, any wording, any link), showing what
was added and removed.

Runs on a schedule via .github/workflows/watch.yml. The last-seen version of
the page is kept in state.json, which the workflow commits back to the repo.

Secrets (repo Settings > Secrets and variables > Actions):
    DISCORD_WEBHOOK   required, Discord webhook URL for alerts
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
FT_EMPTY = "no full-time employment opportunities"
STATE_FILE = Path(__file__).with_name("state.json")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()

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


def extract_page(html):
    """All meaningful content on the page as normalized lines, plus its links.
    Site-wide header/footer/nav and scripts are dropped so only real page changes count."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav",
                     "iframe", "svg"]):
        tag.decompose()
    root = soup.find("main") or soup.find(id="content") or soup.body or soup
    lines = []
    for ln in clean_lines(root.get_text("\n")):
        if not lines or lines[-1] != ln:
            lines.append(ln)
    links = sorted({a["href"].strip() for a in root.find_all("a", href=True)
                    if a["href"].strip() and not a["href"].startswith(("#", "javascript:"))})
    return lines, links


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

    lines, links = extract_page(r.text)
    if len(lines) < 5:
        log("Page came back nearly empty (likely a blip or bot check), so this run is skipped.")
        return

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    digest = hashlib.sha256(("\n".join(lines) + "\n" + "\n".join(links)).encode()).hexdigest()
    prev = state.get("page")

    if prev is None:
        log("First run. Saved the current page as the baseline:\n" + "\n".join(lines))
    elif prev["hash"] != digest:
        old_lines, old_links = prev["lines"], prev.get("links", [])
        added = [l for l in lines if l not in old_lines]
        removed = [l for l in old_lines if l not in lines]
        new_links = [l for l in links if l not in old_links]
        gone_links = [l for l in old_links if l not in links]

        ft_gone = (any(FT_EMPTY in l.lower() for l in old_lines)
                   and not any(FT_EMPTY in l.lower() for l in lines))
        title = "🚨 TNSE: full-time openings may be posted!" if ft_gone else "🔔 TNSE careers page changed"

        body = []
        if added:
            body.append("**Added:**\n" + "\n".join(f"+ {l}" for l in added))
        if removed:
            body.append("**Removed:**\n" + "\n".join(f"- {l}" for l in removed))
        if new_links:
            body.append("**New links:**\n" + "\n".join(f"<{l}>" for l in new_links))
        if gone_links:
            body.append("**Links removed:**\n" + "\n".join(f"<{l}>" for l in gone_links))
        if not body:
            body.append("Content was reordered (nothing added or removed).")
        notify(title, "\n\n".join(body))
    else:
        log("No change.")
        return

    # No timestamps in here, so the file (and a commit) only changes when the page does.
    state = {"page": {"hash": digest, "lines": lines, "links": links}}
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    main()
