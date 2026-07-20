# Copy this file to config.py and fill in your details.
# config.py is gitignored / not tracked so your settings stay local.

SERVER = "irc.libera.chat"
PORT = 6697
USE_TLS = True
PASSWORD = None          # server password, if any (NickServ login is handled separately, see README)

NICK = "PokeBot"
CHANNEL = "#pokemon"
PREFIX = "!"             # command prefix, e.g. "!dex pikachu"

# Optional NickServ auth (recommended so your bot's nick is reserved/identified)
NICKSERV_PASSWORD = None  # e.g. "hunter2" - leave None to skip

# Serebii etiquette settings - do not lower without good reason, see README
SEREBII_MIN_INTERVAL_SECONDS = 5   # minimum gap between any two requests to serebii.net
SEREBII_USER_AGENT = "PokeBotForIRC/1.0 (contact: youremail@example.com; small IRC channel bot)"

CACHE_TTL_SECONDS = 60 * 60 * 6   # 6 hours - how long fetched pages are cached before re-fetching

# PikaQian API - Simplified Chinese Pokemon TCG card data & pricing.
# Get your key from https://pikaqian.com — do NOT commit config.py (with a
# real key filled in) to any public repo or paste it in the channel.
# Current tier note: on the "free" tier, card metadata works but pricing
# fields come back null - you need "hobby" (raw prices) or "pro" (raw +
# graded + sales) for price data to actually show up in !cncard results.
PIKAQIAN_API_KEY = "pk_live_YOUR_KEY_HERE"

# PSA Public API - certificate verification by cert number.
# Register/sign in at https://www.psacard.com/publicapi to get a bearer token
# (free). Cert data essentially never changes once graded, so results are
# cached like everything else (see CACHE_TTL_SECONDS above).
# PSA Public API - certificate verification by cert number.
# Register/sign in at https://www.psacard.com/publicapi to get a bearer token
# (free). WARNING: observed quota on a fresh token was just 1 call/day - see
# the big comment at the top of sources/psacert.py before relying on this.
# Email collectors-apis@collectors.com if you need a higher limit.
PSA_API_TOKEN = "YOUR_PSA_TOKEN_HERE"
PSA_CERT_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days - cert data never changes; don't waste your daily quota re-fetching

# Art of Pokemon (artofpkm.com) - a solo/indie illustrator database, no API.
# This module fetches the whole illustrator directory once and caches it
# (see CACHE_TTL_SECONDS) rather than scraping per-search, so footprint stays
# minimal regardless of how often !artist gets used in the channel.
ARTOFPKM_MIN_INTERVAL_SECONDS = 5
ARTOFPKM_USER_AGENT = "PokeBotForIRC/1.0 (contact: youremail@example.com; small IRC channel bot)"
