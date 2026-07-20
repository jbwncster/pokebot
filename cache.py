"""
Tiny on-disk TTL cache so we never fetch the same page/query twice within
CACHE_TTL_SECONDS. Keeps things fast for repeat lookups and, more importantly,
keeps request volume to Serebii (and Bulbapedia) as low as possible.
"""
import json
import time
import hashlib
import pathlib

import config

CACHE_DIR = pathlib.Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def _key_to_path(key: str) -> pathlib.Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def get(key: str, ttl_seconds: float = None):
    ttl = config.CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    path = _key_to_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - data["ts"] > ttl:
        return None
    return data["value"]


def set(key: str, value):
    path = _key_to_path(key)
    path.write_text(json.dumps({"ts": time.time(), "value": value}))
