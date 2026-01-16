import os
from trakt import init
import trakt.core
from dotenv import load_dotenv


load_dotenv()


def setup_trakt():
    trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
    trakt.core.BASE_URL = "https://api.trakt.tv"
    trakt.core.CONFIG_PATH = "./pytrakt.json"
    init(
        "karelka",
        client_id=os.getenv("TRAKT_CLIENT_ID"),
        client_secret=os.getenv("TRAKT_CLIENT_SECRET"),
        store=True,
    )


if __name__ == "__main__":
    setup_trakt()
