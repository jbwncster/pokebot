"""
PikaQian API client - Simplified Chinese Pokemon TCG card data, pricing
(tier-gated), and images. Official REST API, no scraping involved.

Docs: https://pikaqian.com/docs
Auth: X-API-Key header, required on every data request.

Note: pricing fields on the card object come back null unless the API key
is on the "hobby" (raw prices) or "pro" (raw + graded + sales) tier. Free
tier (the default) only gets metadata. Check config.PIKAQIAN_API_KEY's tier
on the PikaQian dashboard if prices are always showing as unavailable.
"""
import requests

import cache
import config

BASE_URL = "https://api.pikaqian.com/v1"
TIMEOUT = 10


def _headers():
    return {"X-API-Key": config.PIKAQIAN_API_KEY}


def _get(path, params=None):
    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params or {}, timeout=TIMEOUT)
    if resp.status_code == 401:
        return None, "PikaQian API key rejected (check config.PIKAQIAN_API_KEY)."
    if resp.status_code == 429:
        return None, "PikaQian API rate limit hit, try again shortly."
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", {})
            return None, f"PikaQian API error: {err.get('message', resp.status_code)}"
        except ValueError:
            return None, f"PikaQian API error: HTTP {resp.status_code}"
    return resp.json(), None


def _format_price_cents(cents):
    if cents is None:
        return None
    return f"${cents / 100:.2f}"


def _format_card(card: dict) -> str:
    name = card.get("name", "?")
    local_name = card.get("local_name", "")
    set_id = card.get("card_set_id", "?")
    number = card.get("card_number", "?")
    rarity = card.get("rarity_label") or card.get("rarity") or "?"
    element = card.get("element")

    label = f"{name} ({local_name})" if local_name else name
    bits = [f"{label} — {set_id} #{number}, {rarity}"]
    if element:
        bits[0] += f", {element}"

    prices = card.get("prices")
    if prices:
        raw = _format_price_cents(prices.get("raw"))
        psa10 = _format_price_cents(prices.get("psa_10") or prices.get("psa10"))
        price_bits = []
        if raw:
            price_bits.append(f"raw {raw}")
        if psa10:
            price_bits.append(f"PSA10 {psa10}")
        if price_bits:
            bits.append(" | ".join(price_bits))
    else:
        bits.append("(pricing not available on this API tier)")

    image = card.get("image_url")
    if image:
        bits.append(image)

    return " — ".join(bits)


def search(query: str) -> str:
    cache_key = f"pikaqian:search:{query.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data, err = _get("/search", params={"q": query})
    if err:
        return err

    cards = (data or {}).get("cards", [])
    if not cards:
        result = f"No Chinese TCG cards found on PikaQian for '{query}'."
    else:
        # Show the best match plus a count of how many others matched.
        result = _format_card(cards[0])
        if len(cards) > 1:
            result += f"  (+{len(cards) - 1} more match{'es' if len(cards) - 1 != 1 else ''}, refine your search for a different one)"

    cache.set(cache_key, result)
    return result


def get_card(card_id: str) -> str:
    cache_key = f"pikaqian:card:{card_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data, err = _get(f"/cards/{card_id}")
    if err:
        return err
    if not data:
        return f"No PikaQian card found with id '{card_id}'."

    result = _format_card(data)
    cache.set(cache_key, result)
    return result
