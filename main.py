import trakt
from dotenv import load_dotenv
import os
import trakt.core
from trakt import init

load_dotenv()


def get_trakt_token():
    trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
    init(
        os.getenv("TRAKT_USERNAME"),
        store=True,
        client_id=os.getenv("TRAKT_CLIENT_ID"),
        client_secret=os.getenv("TRAKT_CLIENT_SECRET"),
    )


if __name__ == "__main__":
    get_trakt_token()
