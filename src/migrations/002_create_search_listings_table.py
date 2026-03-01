"""
Create search_listings table for tracking listings associated with searches.
"""
from yoyo import step

steps = [
    step(
        """
        CREATE TABLE search_listings (
            search_id INTEGER NOT NULL,
            listing_id INTEGER NOT NULL,
            silent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (search_id, listing_id),
            FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
        )
        """,
        "DROP TABLE search_listings"
    )
]
