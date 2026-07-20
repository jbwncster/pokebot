"""
Bulbapedia lookups via its public MediaWiki API. No scraping involved -
this is the same API mechanism Wikipedia and every other MediaWiki site
expose for legitimate programmatic use.

API docs: https://bulbapedia.bulbagarden.net/wiki/Bulbapedia:API
"""
import requests

import cache

API_URL = "https://bulbapedia.bulbagarden.net/w/api.php"
HEADERS = {
    "User-Agent": "PokeBotForIRC/1.0 (small Libera IRC channel bot)"
}
TIMEOUT = 10


def _api_get(params):
    params = {**params, "format": "json"}
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _search_title(query: str) -> str | None:
    """Find the best-matching page title for a free-text query."""
    data = _api_get({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
    })
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def _get_intro(title: str) -> str | None:
    """Fetch the plaintext intro/extract for a given page title."""
    data = _api_get({
        "action": "query",
        "prop": "extracts",
        "exintro": 1,
        "explaintext": 1,
        "redirects": 1,
        "titles": title,
    })
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract")
        if extract:
            return extract
    return None


def lookup(query: str) -> str:
    cache_key = f"bulbapedia:{query.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        title = _search_title(query)
        if not title:
            result = f"No Bulbapedia article found for '{query}'."
        else:
            intro = _get_intro(title)
            if not intro:
                result = f"Found '{title}' on Bulbapedia but couldn't extract a summary."
            else:
                # Trim to a couple of sentences so we don't flood the channel.
                snippet = " ".join(intro.split("\n")[0].split(". ")[:2]).strip()
                if not snippet.endswith("."):
                    snippet += "."
                url = "https://bulbapedia.bulbagarden.net/wiki/" + title.replace(" ", "_")
                result = f"{title}: {snippet} {url}"
    except requests.RequestException as e:
        result = f"Bulbapedia lookup failed ({e.__class__.__name__}). Try again shortly."

    cache.set(cache_key, result)
    return result
