import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import trakt.core
from trakt.sync import search_by_id, add_to_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configure trakt authentication - must set BASE_URL with trailing slash!
trakt.core.BASE_URL = "https://api.trakt.tv/"
trakt.core.CONFIG_PATH = "./pytrakt.json"
trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH

# Load credentials from config file
with open("./pytrakt.json") as f:
    config = json.load(f)
    trakt.core.CLIENT_ID = config.get("CLIENT_ID")
    trakt.core.CLIENT_SECRET = config.get("CLIENT_SECRET")
    trakt.core.OAUTH_TOKEN = config.get("OAUTH_TOKEN")
    trakt.core.OAUTH_REFRESH = config.get("OAUTH_REFRESH")

# Connect to database
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
cur = conn.cursor()

# Fetch progress items - watched > 0 means some watch progress
# Consider an item "watched" if watched duration is > 80% of total duration
cur.execute("""
    SELECT id, tmdb_id, season_number, episode_number, meta, updated_at, watched, duration
    FROM progress_items 
    WHERE duration > 0 AND watched > (duration * 0.8)
""")
rows = cur.fetchall()

synced_items = []
failed_items = []

logger.info(f"Found {len(rows)} watched items to sync")

for row in rows:
    item_id = row[0]
    tmdb_id = row[1]
    season = row[2]  # season_number (integer)
    episode = row[3]  # episode_number (integer)
    meta = row[4]
    updated_at = row[5]
    watched_duration = row[6]
    total_duration = row[7]

    media_type = meta.get("type") if meta else None
    title = meta.get("title") if meta else "Unknown"

    # Use updated_at as the watched_at timestamp
    watched_at = updated_at

    try:
        if media_type == "movie":
            # Search for movie by TMDB ID
            results = search_by_id(tmdb_id, id_type="tmdb", media_type="movie")
            if results:
                movie = results[0]
                add_to_history(movie, watched_at=watched_at)
                logger.info(f"Synced movie: {title} (TMDB: {tmdb_id})")
                synced_items.append(
                    {
                        "type": "movie",
                        "title": title,
                        "tmdb_id": tmdb_id,
                        "watched_at": str(watched_at),
                    }
                )
            else:
                logger.error(f"Movie not found: {title} (TMDB: {tmdb_id})")
                failed_items.append(
                    {
                        "type": "movie",
                        "title": title,
                        "tmdb_id": tmdb_id,
                        "error": "Not found on Trakt",
                    }
                )

        elif media_type == "show":
            # For shows, we need to find the show and then the specific episode
            if season is None or episode is None:
                logger.error(f"Missing season/episode for show: {title}")
                failed_items.append(
                    {
                        "type": "episode",
                        "show": title,
                        "tmdb_id": tmdb_id,
                        "error": "Missing season or episode number",
                    }
                )
                continue

            # Search for show by TMDB ID
            results = search_by_id(tmdb_id, id_type="tmdb", media_type="show")
            if results:
                show = results[0]
                # Get the episode from the show
                try:
                    from trakt.tv import TVEpisode

                    ep = TVEpisode(show.title, season, episode)
                    add_to_history(ep, watched_at=watched_at)
                    logger.info(f"Synced episode: {title} S{season:02d}E{episode:02d}")
                    synced_items.append(
                        {
                            "type": "episode",
                            "show": title,
                            "season": season,
                            "episode": episode,
                            "tmdb_id": tmdb_id,
                            "watched_at": str(watched_at),
                        }
                    )
                except Exception as e:
                    logger.error(
                        f"Episode not found: {title} S{season:02d}E{episode:02d} - {e}"
                    )
                    failed_items.append(
                        {
                            "type": "episode",
                            "show": title,
                            "season": season,
                            "episode": episode,
                            "tmdb_id": tmdb_id,
                            "error": str(e),
                        }
                    )
            else:
                logger.error(f"Show not found: {title} (TMDB: {tmdb_id})")
                failed_items.append(
                    {
                        "type": "show",
                        "title": title,
                        "tmdb_id": tmdb_id,
                        "error": "Not found on Trakt",
                    }
                )
        else:
            logger.warning(f"Unknown media type for item {item_id}: {media_type}")
            failed_items.append(
                {
                    "type": media_type,
                    "title": title,
                    "tmdb_id": tmdb_id,
                    "error": "Unknown media type",
                }
            )

    except Exception as e:
        logger.error(f"Error syncing {title}: {e}")
        failed_items.append(
            {"type": media_type, "title": title, "tmdb_id": tmdb_id, "error": str(e)}
        )

# Save sync results
sync_data = {
    "synced_count": len(synced_items),
    "failed_count": len(failed_items),
    "synced_items": synced_items,
    "failed_items": failed_items,
}

with open("syncdata.json", "w") as f:
    json.dump(sync_data, indent=4, fp=f)

logger.info("=== Sync Complete ===")
logger.info(f"Synced: {len(synced_items)} items")
if failed_items:
    logger.warning(f"Failed: {len(failed_items)} items")
else:
    logger.info(f"Failed: {len(failed_items)} items")
logger.info("Results saved to syncdata.json")

cur.close()
conn.close()
