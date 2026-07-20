"""
Serebii.net lookups. Serebii has no public API, so this module scrapes HTML -
which means it needs to be extra polite:

  * every request goes through a shared rate limiter (see ratelimit.py)
  * every response is cached (see cache.py) so repeat lookups don't re-hit
    the site
  * requests send an honest User-Agent identifying the bot

IMPORTANT: this module currently supports:
  - lookup_pokemon(name): fetches the Scarlet/Violet Pokedex page for a
    Pokemon, e.g. https://www.serebii.net/pokedex-sv/pikachu/
  - lookup_path(path): fetches an arbitrary Serebii page by path, for cases
    like TCG set/card pages whose URLs vary by set and aren't easily guessed
    (e.g. !serebii /card/hgss/1.shtml). Extend this with set-specific URL
    builders once you know the exact structure of the sets you care about.

Before relying on this for a public channel, consider emailing Serebii to
let them know about the bot - see the README for more on this.
"""
import re

import requests
from bs4 import BeautifulSoup

import cache
import config
from ratelimit import RateLimiter

BASE_URL = "https://www.serebii.net"
TIMEOUT = 10

_limiter = RateLimiter(config.SEREBII_MIN_INTERVAL_SECONDS)


def _fetch(path: str) -> str | None:
    """Rate-limited, cached GET of a Serebii path. Returns HTML or None."""
    cache_key = f"serebii:{path}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    _limiter.wait()
    url = BASE_URL + path if path.startswith("/") else f"{BASE_URL}/{path}"
    headers = {"User-Agent": config.SEREBII_USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    if resp.status_code != 200:
        cache.set(cache_key, None)
        return None

    html = resp.text
    cache.set(cache_key, html)
    return html


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def lookup_pokemon(name: str) -> str:
    slug = _clean_name(name)
    path = f"/pokedex-sv/{slug}/"

    try:
        html = _fetch(path)
    except requests.RequestException as e:
        return f"Serebii lookup failed ({e.__class__.__name__}). Try again shortly."

    if html is None:
        return f"Couldn't find a Serebii Pokedex page for '{name}'."

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else name.title()

    # Serebii's dex pages are table-heavy rather than semantic HTML, so pull
    # the page description meta tag for a clean one-line summary rather than
    # trying to parse the layout tables (fragile across page redesigns).
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    url = BASE_URL + path
    if description:
        return f"{title}: {description} {url}"
    return f"{title}: {url}"


def lookup_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path

    try:
        html = _fetch(path)
    except requests.RequestException as e:
        return f"Serebii lookup failed ({e.__class__.__name__}). Try again shortly."

    if html is None:
        return f"Couldn't fetch {BASE_URL}{path} (page may not exist)."

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else path

    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    url = BASE_URL + path
    if description:
        return f"{title}: {description} {url}"
    return f"{title}: {url}"
