# PokeBot - IRC bot for ##pokemon on Libera.Chat

Small IRC bot with two commands:

- `!dex <name>` — Pokedex summary from **Bulbapedia's official API** (safe, no scraping)
- `!pokemon <name>` — Pokedex stats page from **Serebii** (scraped, cached, rate-limited)
- `!serebii <path>` — fetch any Serebii page by path, e.g. `!serebii /card/hgss/1.shtml`
- `!cncard <name>` (alias `!cnc`) — Simplified Chinese TCG card data from the **PikaQian API**
- `!psacert <cert number>` (alias `!psa`) — PSA graded-card certificate lookup via the **PSA Public API**
- `!artist <name>` (alias `!illustrator`) — Japanese TCG illustrator lookup from **The Art of Pokemon** (artofpkm.com)

## 1. Files in this project

```text
bot.py              main bot / IRC event loop
config.example.py   copy to config.py and edit
cache.py            simple on-disk TTL cache
ratelimit.py        shared rate limiter (used for Serebii requests)
Dockerfile          container configuration for Fly.io
sources/
  bulbapedia.py      Bulbapedia API client
  serebii.py         Serebii scraper
  pikaqian.py        PikaQian API client (Chinese TCG cards)
  psacert.py         PSA Public API client (cert verification)
  artofpkm.py        Art of Pokemon illustrator directory (scraped, cached)
requirements.txt
```

## 2. Local Configuration

Before deploying, configure the bot locally:

```bash
cp config.example.py config.py
```

Edit `config.py` and set:
- `NICK` — the bot's IRC nickname
- `CHANNEL` — your channel, e.g. `##pokemon`
- `SEREBII_USER_AGENT` — put a real contact email in here; it's good practice when scraping a small site
- `PIKAQIAN_API_KEY` — get one at https://pikaqian.com. Note: the free tier only returns card metadata, not pricing.
- `PSA_API_TOKEN` — register at https://www.psacard.com/publicapi to get a free bearer token.
- `ARTOFPKM_USER_AGENT` — same idea as `SEREBII_USER_AGENT`: put a real contact email in here.

**🚨 CRITICAL LIBERA.CHAT NOTE FOR FLY.IO:** 
Because Fly.io utilizes shared cloud IPs, Libera.Chat restricts these connections to **SASL-only**. Standard NickServ messaging on connect will result in an immediate ban/disconnect. You *must* register the bot's nickname from your local home IP first, and then configure `bot.py` to use SASL PLAIN authentication with your `NICKSERV_PASSWORD` during the connection handshake. Ensure your code injects `sasl_login` and `sasl_password` into the `connect_params`.

## 3. Create a Dockerfile

Fly.io uses Docker containers to run applications. If you haven't already, create a file named `Dockerfile` in the root of your project with the following contents:

```dockerfile
FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./bot.py" ]
```

## 4. Deploying to Fly.io

1. **Install the Fly CLI:** Follow the instructions at [fly.io/docs/hands-on/install-flyctl/](https://fly.io/docs/hands-on/install-flyctl/).
2. **Authenticate:** Run `fly auth login` in your terminal.
3. **Initialize the App:** In your project directory, run:
   ```bash
   fly launch
   ```
   * Follow the prompts to name your app and select a region. 
   * When asked if you want to deploy now, select **No**. We need to ensure configuration and secrets are passed properly without hardcoding them if `config.py` is ignored.
   * *Tip: If you do not push `config.py`, you must set your configuration variables as Fly Secrets (`fly secrets set NICK="YourBotNick" ...`) and update `config.py` or `bot.py` to read from environment variables to prevent crashing.*
4. **Deploy:** Once your `fly.toml` is generated and your configuration is ready, push the bot to the cloud:
   ```bash
   fly deploy
   ```

Check your bot's status and logs via the Fly dashboard or by running:
```bash
fly logs
```
The bot will now run persistently in the cloud and automatically restart if it crashes.

## 5. A note on Serebii etiquette

Serebii has no official API and is largely run by one person. The scraper in `sources/serebii.py`:
- rate-limits itself (default: min 5 seconds between any two Serebii requests, process-wide — configurable via `SEREBII_MIN_INTERVAL_SECONDS`)
- caches every page for several hours (`CACHE_TTL_SECONDS`) so repeat lookups in the channel don't cause repeat fetches
- sends an honest `User-Agent` with contact info

Consider emailing Serebii to mention the bot exists — small, clearly-labeled, low-volume fan bots are usually fine, but asking first is the courteous move and gives them a chance to say if there's anything they'd rather you avoid.

The included `!pokemon` command only covers the Scarlet/Violet Pokedex pages (`/pokedex-sv/<name>/`). If you want TCG set/card data from Serebii, extend `sources/serebii.py` with a dedicated parser for those specific URL structures.

## 6. A note on artofpkm.com etiquette

The Art of Pokemon (artofpkm.com) is a solo passion project — one person's database of Japanese TCG illustrators and artwork, built over hundreds of hours on nights and weekends. It has no public API, so `sources/artofpkm.py` takes a different approach than the Serebii scraper: instead of hitting the site once per `!artist` lookup, it fetches the *entire* illustrator directory (a single page listing all ~500 artists) once and caches it for the full `CACHE_TTL_SECONDS` window, then answers every search locally against that cached copy. 

Given how small and personal this project is, it's worth reaching out to the creator (active on X/Twitter as @pkm_jp, linked from the site) before relying on this in a busy channel. If the site's page structure ever changes, `_parse_directory()` in `sources/artofpkm.py` is the one place that needs updating.

## 7. Extending the bot

- Add new commands in `bot.py` (`on_pubmsg`) following the existing pattern.
- Add new data sources as new files under `sources/`, using `cache.py` and (if scraping a small/unofficial site) `ratelimit.py` the same way `serebii.py` does.
