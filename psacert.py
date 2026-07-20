"""
PSA Public API client - certificate verification by cert number.

Docs: https://www.psacard.com/publicapi/documentation
Swagger spec: https://api.psacard.com/publicapi/swagger.json
Auth: register/sign in at https://www.psacard.com/publicapi to get a bearer
token, then set config.PSA_API_TOKEN.

Endpoint: GET https://api.psacard.com/publicapi/cert/GetByCertNumber/{certNumber}

IMPORTANT - rate limits are aggressive on the default tier: in testing, a
freshly issued token allowed exactly 1 call per day before returning 429
with "API calls quota exceeded! maximum admitted 1 per Day." If you need
more than that, email collectors-apis@collectors.com (PSA's own contact for
this API) and ask about a higher quota - the self-serve dashboard doesn't
appear to expose a way to raise it. Because of this, cert lookups are cached
far longer than everything else (PSA_CERT_CACHE_TTL_SECONDS, default 30
days) - cert data never changes once a card is graded, so long caching costs
nothing in freshness and saves your extremely limited daily calls.

Actual observed response shapes (these differ from PSA's published docs in
places - the docs describe a 200 + {"IsValidRequest": ...} envelope for
"not found", but a malformed/not-found cert number returned an HTTP 404
whose body was a bare JSON string, not an object):
  - Success (200): {"IsValidRequest": true, "ServerMessage": "Request successful", "PSACert": {...}}
  - Not found (404 observed): a bare JSON string, e.g. "Certificate Number Not Found"
  - Rate limited (429 observed): a bare JSON string, e.g.
    "API calls quota exceeded! maximum admitted 1 per Day. Please contact collectors-apis@collectors.com"
  - Invalid credentials: per docs, usually a 500

This module handles both the documented shape and the bare-string shape
defensively.
"""
import re

import requests

import cache
import config

BASE_URL = "https://api.psacard.com/publicapi"
TIMEOUT = 10


def _headers():
    return {"authorization": f"bearer {config.PSA_API_TOKEN}"}


def _format_cert(data: dict) -> str:
    cert = data.get("PSACert") or {}
    subject = cert.get("Subject") or "Unknown card"
    brand = cert.get("Brand") or ""
    year = cert.get("Year") or ""
    card_number = cert.get("CardNumber") or ""
    variety = cert.get("Variety") or ""
    grade = cert.get("CardGrade") or "?"
    grade_desc = cert.get("GradeDescription") or ""
    cert_no = cert.get("CertNumber") or ""
    total_pop = cert.get("TotalPopulation")
    pop_higher = cert.get("PopulationHigher")

    header = " ".join(str(x) for x in (year, brand) if x).strip()
    line = f"PSA {cert_no}: {header} {subject}".strip()
    if card_number:
        line += f" #{card_number}"
    if variety:
        line += f" ({variety})"

    grade_bit = f"Grade: {grade}"
    if grade_desc:
        grade_bit += f" ({grade_desc})"
    line += f" — {grade_bit}"

    if total_pop is not None:
        pop_bit = f"Pop {total_pop}"
        if pop_higher is not None:
            pop_bit += f", {pop_higher} higher"
        line += f" — {pop_bit}"

    url = f"https://www.psacard.com/cert/{cert_no}"
    return f"{line} {url}"


def lookup(cert_number: str) -> str:
    cert_number = re.sub(r"\D", "", cert_number)  # digits only
    if not cert_number:
        return "PSA cert numbers are numeric only, e.g. !psacert 12345678"

    cache_key = f"psacert:{cert_number}"
    cached = cache.get(cache_key, ttl_seconds=config.PSA_CERT_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    if not config.PSA_API_TOKEN or config.PSA_API_TOKEN == "YOUR_PSA_TOKEN_HERE":
        return "PSA cert lookup isn't configured yet (missing PSA_API_TOKEN in config.py)."

    try:
        resp = requests.get(
            f"{BASE_URL}/cert/GetByCertNumber/{cert_number}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        return f"PSA lookup failed ({e.__class__.__name__}). Try again shortly."

    if resp.status_code == 500:
        return "PSA API rejected the request (check PSA_API_TOKEN validity/expiry)."

    try:
        data = resp.json()
    except ValueError:
        return f"PSA API returned an unexpected response (HTTP {resp.status_code})."

    # PSA sometimes returns a bare JSON string instead of the documented
    # {"IsValidRequest": ...} object - notably for 404 (not found/malformed)
    # and 429 (rate limited) responses observed in testing.
    if isinstance(data, str):
        if resp.status_code == 429:
            result = f"PSA API daily quota exceeded: {data}"
            # Don't cache rate-limit responses - they say nothing about the
            # actual cert and would incorrectly "poison" this cert number.
            return result
        result = f"PSA: {data} (cert #{cert_number})"
        cache.set(cache_key, result)
        return result

    if resp.status_code >= 400:
        return f"PSA API error: HTTP {resp.status_code}"

    if not data.get("IsValidRequest"):
        result = f"Invalid PSA cert number: {cert_number}"
    elif data.get("ServerMessage") == "No data found":
        result = f"No PSA record found for cert #{cert_number}."
    else:
        result = _format_cert(data)

    cache.set(cache_key, result)
    return result
