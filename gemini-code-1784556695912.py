# Add this import at the top
import irc.client_aiox

class PokeBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        connect_params = {}
        if config.USE_TLS:
            ssl_ctx = ssl.create_default_context()
            ssl_factory = irc.connection.Factory(
                wrapper=lambda sock: ssl_ctx.wrap_socket(sock, server_hostname=config.SERVER)
            )
            connect_params["connect_factory"] = ssl_factory
            
        # Add SASL authentication here
        if config.NICKSERV_PASSWORD:
            connect_params["sasl_login"] = config.NICK
            connect_params["sasl_password"] = config.NICKSERV_PASSWORD

        server_list = [(config.SERVER, config.PORT, config.PASSWORD)] if config.PASSWORD \
            else [(config.SERVER, config.PORT)]

        super().__init__(server_list, config.NICK, config.NICK, **connect_params)
        self.target_channel = config.CHANNEL