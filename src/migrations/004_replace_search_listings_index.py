"""
Replace composite index (search_id, created_at) with created_at only index.

The old index was not useful for any current query because:
- Queries filtering by search_id are already covered by the composite PK.
- Queries filtering by created_at (cleanup, recent found items) couldn't use it
  since search_id was the leading column.

The new index on created_at supports:
- cleanup_old_listings: DELETE WHERE created_at < datetime('now', ?)
- get_recent_found_items: WHERE created_at >= datetime('now', ?) AND silent = 0
"""
from yoyo import step

steps = [
    step(
        """
        DROP INDEX idx_search_listings_search_created_at
        """,
        """
        CREATE INDEX idx_search_listings_search_created_at
            ON search_listings(search_id, created_at DESC)
        """
    ),
    step(
        """
        CREATE INDEX idx_search_listings_created_at
            ON search_listings(created_at)
        """,
        "DROP INDEX idx_search_listings_created_at"
    )
]
