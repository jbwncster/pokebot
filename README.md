# PokeBot - IRC bot for #pokemon on Libera.Chat

Small IRC bot with two commands:

- `!dex <name>` — Pokedex summary from **Bulbapedia's official API** (safe, no scraping)
- `!pokemon <name>` — Pokedex stats page from **Serebii** (scraped, cached, rate-limited)
- `!serebii <path>` — fetch any Serebii page by path, e.g. `!serebii /card/hgss/1.shtml`
- `!cncard <name>` (alias `!cnc`) — Simplified Chinese TCG card data from the **PikaQian API**
- `!psacert <cert number>` (alias `!psa`) — PSA graded-card certificate lookup via the **PSA Public API**
- `!artist <name>` (alias `!illustrator`) — Japanese TCG illustrator lookup from **The Art of Pokemon** (artofpkm.com)

## 1. Files in this project

```
bot.py              main bot / IRC event loop
config.example.py   copy to config.py and edit
cache.py            simple on-disk TTL cache
ratelimit.py         shared rate limiter (used for Serebii requests)
sources/
  bulbapedia.py      Bulbapedia API client
  serebii.py         Serebii scraper
  pikaqian.py        PikaQian API client (Chinese TCG cards)
  psacert.py         PSA Public API client (cert verification)
  artofpkm.py        Art of Pokemon illustrator directory (scraped, cached)
requirements.txt
pokebot.service      systemd unit file
```

## 2. Create the Oracle Cloud "Always Free" VM

1. In the Oracle Cloud console: **Compute → Instances → Create Instance**.
2. Choose an **Always Free eligible shape** — either the Ampere A1 (ARM, up to 4 OCPU / 24GB free) or a VM.Standard.E2.1.Micro (AMD, always free).
3. Choose an **Ubuntu** image (22.04 or 24.04 LTS is simplest for these instructions).
4. When creating the instance, either upload your SSH public key or let Oracle generate a key pair for you (download the private key — you'll need it to log in).
5. Once running, note the instance's **public IP address**.

**Networking note:** Oracle's default security list only opens SSH (port 22) inbound. This bot only makes *outbound* connections (to Libera, Bulbapedia, and Serebii), so you don't need to open any inbound ports for it to work — just make sure outbound traffic isn't restricted (it isn't, by default).

## 3. Log into the VM and install prerequisites

```bash
ssh -i /path/to/your/private_key.pem ubuntu@<your-vm-public-ip>

sudo apt update
sudo apt install -y python3-venv python3-pip
```

## 4. Get the bot code onto the VM

From your own machine, copy the project directory to the VM (adjust the path to wherever you saved these files):

```bash
scp -i /path/to/your/private_key.pem -r ./pokebot ubuntu@<your-vm-public-ip>:/tmp/pokebot
```

Then on the VM:

```bash
sudo mkdir -p /opt/pokebot
sudo mv /tmp/pokebot/* /opt/pokebot/
sudo useradd -r -s /usr/sbin/nologin pokebot || true
sudo chown -R pokebot:pokebot /opt/pokebot
```

## 5. Set up the Python environment

```bash
cd /opt/pokebot
sudo -u pokebot python3 -m venv venv
sudo -u pokebot ./venv/bin/pip install -r requirements.txt
```

## 6. Configure the bot

```bash
sudo -u pokebot cp config.example.py config.py
sudo -u pokebot nano config.py
```

At minimum, set:
- `NICK` — the bot's IRC nickname
- `CHANNEL` — your channel, e.g. `#pokemon`
- `SEREBII_USER_AGENT` — put a real contact email in here; it's good practice
  when scraping a small site
- `PIKAQIAN_API_KEY` — get one at https://pikaqian.com. Note: the free tier
  only returns card metadata, not pricing — see the comment in
  `config.example.py`.
- `PSA_API_TOKEN` — register at https://www.psacard.com/publicapi to get a
  free bearer token, then set it here. Without it, `!psacert` will reply that
  it isn't configured rather than erroring.
- `ARTOFPKM_USER_AGENT` — same idea as `SEREBII_USER_AGENT`: put a real
  contact email in here. artofpkm.com is a one-person passion project (see
  the etiquette note below), so being identifiable matters even more here
  than for Serebii.

If you want the bot's nick registered/identified with NickServ, register the
nick manually first (`/msg NickServ REGISTER ...` from your own client, or
via `/msg NickServ HELP REGISTER`), then set `NICKSERV_PASSWORD` in
`config.py` — the bot will identify automatically on connect.

## 7. Test it interactively first

```bash
sudo -u pokebot /opt/pokebot/venv/bin/python /opt/pokebot/bot.py
```

You should see it connect and join the channel. Try `!dex pikachu` and
`!pokemon pikachu` from another client. Ctrl+C to stop once you've confirmed
it works.

## 8. Run it as a persistent systemd service

```bash
sudo cp /opt/pokebot/pokebot.service /etc/systemd/system/pokebot.service
sudo systemctl daemon-reload
sudo systemctl enable pokebot
sudo systemctl start pokebot
```

Check status / logs:

```bash
sudo systemctl status pokebot
sudo journalctl -u pokebot -f
```

The bot will now start automatically on boot and restart automatically if it
crashes.

## 9. A note on Serebii etiquette

Serebii has no official API and is largely run by one person. The scraper in
`sources/serebii.py`:

- rate-limits itself (default: min 5 seconds between any two Serebii requests,
  process-wide — configurable via `SEREBII_MIN_INTERVAL_SECONDS`)
- caches every page for several hours (`CACHE_TTL_SECONDS`) so repeat lookups
  in the channel don't cause repeat fetches
- sends an honest `User-Agent` with contact info

Consider emailing Serebii to mention the bot exists — small, clearly-labeled,
low-volume fan bots are usually fine, but asking first is the courteous move
and gives them a chance to say if there's anything they'd rather you avoid.

The included `!pokemon` command only covers the Scarlet/Violet Pokedex pages
(`/pokedex-sv/<name>/`). If you want TCG set/card data from Serebii, its page
structure varies by set, so the cleanest path is to send me (or figure out)
a couple of example URLs for the specific sets you care about and extend
`sources/serebii.py` with a dedicated parser for them — the generic
`!serebii <path>` command in the meantime lets you fetch any known page by
path and get back its title + meta description.

## 9b. A note on artofpkm.com etiquette

The Art of Pokemon (artofpkm.com) is a solo passion project — one person's
database of Japanese TCG illustrators and artwork, built over hundreds of
hours on nights and weekends. It has no public API, so `sources/artofpkm.py`
takes a different approach than the Serebii scraper: instead of hitting the
site once per `!artist` lookup, it fetches the *entire* illustrator directory
(a single page listing all ~500 artists) once and caches it for the full
`CACHE_TTL_SECONDS` window, then answers every search locally against that
cached copy. A busy channel doing many lookups a day still only touches
artofpkm.com about once per cache window.

Given how small and personal this project is, it's worth reaching out to the
creator (active on X/Twitter as @pkm_jp, linked from the site) before relying
on this in a busy channel — more so than with Serebii. If the site's page
structure ever changes, `_parse_directory()` in `sources/artofpkm.py` is the
one place that needs updating.

## 10. Extending the bot

- Add new commands in `bot.py` (`on_pubmsg`) following the existing pattern.
- Add new data sources as new files under `sources/`, using `cache.py` and
  (if scraping a small/unofficial site) `ratelimit.py` the same way
  `serebii.py` does.
