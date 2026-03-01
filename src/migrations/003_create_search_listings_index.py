"""
Create index on search_listings for optimized queries by search_id and created_at.
"""
from yoyo import step

steps = [
    step(
        """
        CREATE INDEX idx_search_listings_search_created_at
            ON search_listings(search_id, created_at DESC)
        """,
        "DROP INDEX idx_search_listings_search_created_at"
    )
]
