# pstream-trakt-sync

Sync watched movies and TV episodes from a PostgreSQL database to Trakt.tv.

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt` or use `uv`
3. Run: `python main.py`

## Configuration

Required environment variables:

- `TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET` - Trakt API credentials
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL connection

## Output

Results are saved to `syncdata.json`.

## Notes

- This only works rn for single user in db sync which should be fine as this only works with self hosted anyway.
