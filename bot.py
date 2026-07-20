#!/usr/bin/env python3
"""
PokeBot - a small IRC bot for Pokemon TCG / Pokedex lookups.

Commands (in-channel, prefix configurable, default "!"):
    !dex <name>        -> Pokedex summary pulled from Bulbapedia's API
    !pokemon <name>    -> Pokedex stats page pulled from Serebii (scraped, cached)
    !serebii <path>    -> Fetch + summarize an arbitrary Serebii page, e.g.
                           !serebii /card/hgss/1.shtml
    !help              -> List commands

Design notes:
    - Bulbapedia is queried through its official MediaWiki API (no scraping,
      no ToS concerns).
    - Serebii has no public API, so those lookups scrape HTML. To be a good
      citizen on a site run largely by one person, every Serebii fetch is
      rate-limited and cached (see cache.py / ratelimit.py). Do NOT lower the
      rate limit without good reason.
"""
import logging
import ssl
import time

import irc.bot
import irc.strings
from jaraco.stream import buffer

import config
from sources import bulbapedia, serebii, pikaqian, psacert, artofpkm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("pokebot")


class PokeBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        # Be tolerant of any encoding weirdness from IRC rather than crashing.
        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        connect_params = {}
        if config.USE_TLS:
            ssl_ctx = ssl.create_default_context()
            ssl_factory = irc.connection.Factory(
                wrapper=lambda sock: ssl_ctx.wrap_socket(sock, server_hostname=config.SERVER)
            )
            connect_params["connect_factory"] = ssl_factory

        server_list = [(config.SERVER, config.PORT, config.PASSWORD)] if config.PASSWORD \
            else [(config.SERVER, config.PORT)]

        super().__init__(server_list, config.NICK, config.NICK, **connect_params)
        self.target_channel = config.CHANNEL

    def on_welcome(self, connection, event):
        if config.NICKSERV_PASSWORD:
            log.info("Identifying with NickServ")
            connection.privmsg("NickServ", f"IDENTIFY {config.NICKSERV_PASSWORD}")
            # Give NickServ a moment before joining, otherwise some networks
            # apply your registered channel modes/cloak a beat late.
            time.sleep(2)
        log.info("Connected. Joining %s", self.target_channel)
        connection.join(self.target_channel)

    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + "_")

    def on_join(self, connection, event):
        log.info("Joined %s", event.target)

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0].strip()
        if not msg.startswith(config.PREFIX):
            return

        nick = event.source.nick
        parts = msg[len(config.PREFIX):].strip().split(None, 1)
        if not parts:
            return
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        try:
            if cmd == "dex":
                self.cmd_dex(connection, event.target, nick, arg)
            elif cmd == "pokemon":
                self.cmd_pokemon(connection, event.target, nick, arg)
            elif cmd == "serebii":
                self.cmd_serebii(connection, event.target, nick, arg)
            elif cmd in ("cncard", "cnc"):
                self.cmd_cncard(connection, event.target, nick, arg)
            elif cmd in ("psacert", "psa"):
                self.cmd_psacert(connection, event.target, nick, arg)
            elif cmd in ("artist", "illustrator"):
                self.cmd_artist(connection, event.target, nick, arg)
            elif cmd in ("help", "commands"):
                self.cmd_help(connection, event.target, nick)
        except Exception:
            log.exception("Error handling command %r from %s", msg, nick)
            self.reply(connection, event.target, nick, "Something went wrong handling that — try again in a bit.")

    # ---- commands ----------------------------------------------------

    def cmd_help(self, connection, target, nick):
        self.reply(connection, target, nick,
                    f"Commands: {config.PREFIX}dex <name>  |  "
                    f"{config.PREFIX}pokemon <name>  |  "
                    f"{config.PREFIX}serebii <path>  |  "
                    f"{config.PREFIX}cncard <name> (Chinese TCG cards, alias {config.PREFIX}cnc)  |  "
                    f"{config.PREFIX}psacert <cert#> (alias {config.PREFIX}psa)  |  "
                    f"{config.PREFIX}artist <name> (Japanese TCG illustrators)")

    def cmd_dex(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}dex <pokemon or card name>")
            return
        result = bulbapedia.lookup(arg)
        self.send_multiline(connection, target, nick, result)

    def cmd_pokemon(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}pokemon <name>")
            return
        result = serebii.lookup_pokemon(arg)
        self.send_multiline(connection, target, nick, result)

    def cmd_serebii(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}serebii /path/to/page.shtml")
            return
        result = serebii.lookup_path(arg)
        self.send_multiline(connection, target, nick, result)

    def cmd_cncard(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}cncard <name> (Simplified Chinese TCG cards)")
            return
        result = pikaqian.search(arg)
        self.send_multiline(connection, target, nick, result)

    def cmd_psacert(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}psacert <cert number>")
            return
        result = psacert.lookup(arg)
        self.send_multiline(connection, target, nick, result)

    def cmd_artist(self, connection, target, nick, arg):
        if not arg:
            self.reply(connection, target, nick, f"Usage: {config.PREFIX}artist <name> (Art of Pokemon illustrator database)")
            return
        result = artofpkm.search(arg)
        self.send_multiline(connection, target, nick, result)

    # ---- helpers --------------------------------------------------------

    def reply(self, connection, target, nick, text):
        connection.privmsg(target, f"{nick}: {text}")

    def send_multiline(self, connection, target, nick, text, max_lines=4):
        lines = text.splitlines() or [text]
        for i, line in enumerate(lines[:max_lines]):
            prefix = f"{nick}: " if i == 0 else ""
            connection.privmsg(target, f"{prefix}{line}")
            time.sleep(0.4)  # avoid flooding off the server


def main():
    bot = PokeBot()
    bot.start()


if __name__ == "__main__":
    main()
