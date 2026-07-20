"""
The Art of Pokemon (artofpkm.com) illustrator lookups.

This is a small fan-run passion project (one person's database of Japanese
Pokemon TCG artists, cards, and artwork) - no public API. Unlike serebii.py,
this module doesn't scrape per-query. Instead it fetches the *entire*
illustrator directory (a single page listing all ~500 artists) once, caches
it for a long time, and does all searching locally against that cached copy.
This means a busy channel doing dozens of artist lookups a day still only
hits artofpkm.com once per cache window (default 24h) rather than once per
lookup - about as light a footprint as a scraper can have.

Given this is a solo/indie project (unlike, say, a corporate site), consider
reaching out to the creator (linked from the site, active on X as @pkm_jp)
to let them know about the bot before relying on this in a busy channel.

Page structure (as of this writing): each illustrator is an <a class="link">
linking to /illustrators/{id}, containing an <h3> (name) and <h4 class="ja">
(Japanese name), with a sibling card-count <span> and bio <div> in the same
container. If artofpkm.com redesigns the page, _parse_directory() below is
the only place that needs updating.
"""
import re

import requests
from bs4 import BeautifulSoup

import cache
import config
from ratelimit import RateLimiter

BASE_URL = "https://www.artofpkm.com"
DIRECTORY_PATH = "/illustrators"
TIMEOUT = 15
DIRECTORY_CACHE_KEY = "artofpkm:directory"

_limiter = RateLimiter(config.ARTOFPKM_MIN_INTERVAL_SECONDS)


def _parse_directory(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for a in soup.find_all("a", class_="link", href=True):
        href = a["href"]
        if not href.startswith("/illustrators/"):
            continue
        h3 = a.find("h3")
        if not h3:
            continue
        name = h3.get_text(strip=True)
        h4 = a.find("h4")
        local_name = h4.get_text(strip=True) if h4 else ""

        container = a.parent
        card_count = ""
        span = container.find("span")
        if span:
            card_count = span.get_text(strip=True)

        bio = ""
        for div in container.find_all("div", recursive=False):
            text = div.get_text(strip=True)
            if not text or re.fullmatch(r"\d+\s+Cards?", text) or text.startswith("http"):
                continue
            bio = text

        entries.append({
            "name": name,
            "local_name": local_name,
            "url": BASE_URL + href,
            "cards": card_count,
            "bio": bio,
        })
    return entries


def _get_directory() -> list:
    cached = cache.get(DIRECTORY_CACHE_KEY)
    if cached is not None:
        return cached

    _limiter.wait()
    headers = {"User-Agent": config.ARTOFPKM_USER_AGENT}
    resp = requests.get(BASE_URL + DIRECTORY_PATH, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    entries = _parse_directory(resp.text)

    cache.set(DIRECTORY_CACHE_KEY, entries)
    return entries


def _format_entry(entry: dict) -> str:
    name = entry["name"]
    if entry["local_name"]:
        name += f" ({entry['local_name']})"
    bits = [name]
    if entry["cards"]:
        bits.append(entry["cards"])
    line = " — ".join(bits)
    if entry["bio"]:
        bio = entry["bio"]
        if len(bio) > 200:
            bio = bio[:197].rstrip() + "..."
        line += f" — {bio}"
    line += f" {entry['url']}"
    return line


def search(query: str) -> str:
    query_norm = query.strip().lower()
    if not query_norm:
        return "Usage: !artist <name>"

    try:
        directory = _get_directory()
    except requests.RequestException as e:
        return f"Art of Pokemon lookup failed ({e.__class__.__name__}). Try again shortly."

    if not directory:
        return "Couldn't load the Art of Pokemon illustrator directory right now."

    # Exact (case-insensitive) match first, then substring matches.
    exact = [e for e in directory if e["name"].lower() == query_norm]
    if exact:
        return _format_entry(exact[0])

    matches = [e for e in directory if query_norm in e["name"].lower()
               or (e["local_name"] and query_norm in e["local_name"].lower())]
    if not matches:
        return f"No Art of Pokemon illustrator found matching '{query}'."

    # Prefer the artist with the most cards among ambiguous matches - usually
    # the one people mean (e.g. "yamamoto" matching several people).
    def _card_num(e):
        m = re.search(r"\d+", e["cards"])
        return int(m.group()) if m else 0

    matches.sort(key=_card_num, reverse=True)
    result = _format_entry(matches[0])
    if len(matches) > 1:
        result += f"  (+{len(matches) - 1} more match{'es' if len(matches) - 1 != 1 else ''}, refine your search for a different one)"
    return result
