"""
Create searches table for storing user search queries.
"""
from yoyo import step

steps = [
    step(
        """
        CREATE TABLE searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            query TEXT NOT NULL,
            price_min REAL NOT NULL,
            price_max REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """,
        "DROP TABLE searches"
    )
]
