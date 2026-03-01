import asyncio
import aiosqlite
import logging
from typing import Optional
from src.telegram_bot.models.search import Search
from src.config import Config
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.commands.delete_search_command import DeleteSearchCommand
from src.message_bus.commands.update_search_command import UpdateSearchCommand
from src.message_bus.commands.delete_all_listings_for_search_command import (
    DeleteAllListingsForSearchCommand,
)
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)
from src.message_bus.queries.filter_new_listings_query import (
    FilterNewListingsQuery,
)
from src.message_bus.queries.get_total_listing_count_for_search_query import (
    GetTotalListingCountForSearchQuery,
)
from src.message_bus.queries.get_recent_found_items_query import (
    GetRecentFoundItemsQuery,
)

logger = logging.getLogger(__name__)


# Note: Database schema is managed by migrations (see src/repository/migrations.py)
# Migrations must be applied before connecting to the database
class Repository:
    def __init__(
        self,
        db_path: str = Config.DATABASE_PATH,
        busy_timeout: int = Config.DB_BUSY_TIMEOUT,
    ):
        self.db_path = db_path
        self.busy_timeout = busy_timeout
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database and initialize tables. Raises on failure."""
        if self.connection is not None:
            return

        try:
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
            logger.info(f"Connected to database: {self.db_path}")
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to connect to database {self.db_path}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}", exc_info=True)
            raise

        try:
            # Recommended pragmas for concurrent read + serialized writes + DB Busy Timeout prevention
            await self.connection.execute("PRAGMA journal_mode=WAL")
            await self.connection.execute("PRAGMA foreign_keys=ON")
            await self.connection.execute(f"PRAGMA busy_timeout={self.busy_timeout}")
            await self.connection.commit()
            logger.debug(f"Database pragmas set successfully ")
        except aiosqlite.Error as e:
            logger.error(f"Failed to set database pragmas: {e}", exc_info=True)
            await self.connection.close()
            self.connection = None
            raise

    async def close(self):
        """Close database connection. Logs errors but doesn't raise."""
        if self.connection:
            try:
                await self.connection.close()
                self.connection = None
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)
                self.connection = None

    async def periodic_cleanup(
        self, interval_hours: int = Config.DB_CLEANUP_INTERVAL_HOURS
    ):
        """Run cleanup periodically while the bot is running."""
        while True:
            if self.connection is None:
                logger.error("Database connection lost during periodic cleanup")
                break

            await asyncio.sleep(interval_hours * 3600)

            try:
                logger.info("Starting periodic cleanup of old listings")
                await self.cleanup_old_listings()
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}", exc_info=True)
                # Continue running - cleanup failure shouldn't stop the bot

    async def cleanup_old_listings(self, days: int = Config.DB_LISTING_RETENTION_DAYS):
        """Delete listings older than N days. Raises on failure."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                DELETE FROM search_listings
                WHERE created_at < datetime('now', ?)
                """,
                (f"-{days} days",),
            )
            await self.connection.commit()
            deleted_count = cursor.rowcount
            logger.info(
                f"Cleaned up {deleted_count} old listings (older than {days} days)"
            )
        except aiosqlite.Error as e:
            logger.error(f"Failed to cleanup old listings: {e}", exc_info=True)
            raise

    async def get_all_searches(self, query: GetAllSearchesQuery) -> list[Search]:
        """Get all searches from database. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                SELECT id, chat_id, query, price_min, price_max
                FROM searches
                ORDER BY updated_at DESC
                """
            )
            rows = await cursor.fetchall()

            searches = [
                Search(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    query=row["query"],
                    price_min=row["price_min"],
                    price_max=row["price_max"],
                )
                for row in rows
            ]

            logger.debug(f"Retrieved {len(searches)} searches from database")
            return searches
        except (aiosqlite.Error, KeyError) as e:
            logger.error(f"Failed to get all searches: {e}", exc_info=True)
            raise

    async def get_search_by_id(self, query: GetSearchByIdQuery) -> Optional[Search]:
        """Get search by ID. Returns None if not found. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                SELECT id, chat_id, query, price_min, price_max
                FROM searches
                WHERE id = ?
                """,
                (query.search_id,),
            )
            row = await cursor.fetchone()

            if row is None:
                logger.debug(f"Search not found: id={query.search_id}")
                return None

            search = Search(
                id=row["id"],
                chat_id=row["chat_id"],
                query=row["query"],
                price_min=row["price_min"],
                price_max=row["price_max"],
            )

            logger.debug(f"Retrieved search: id={query.search_id}")
            return search
        except (aiosqlite.Error, KeyError) as e:
            logger.error(
                f"Failed to get search by id {query.search_id}: {e}", exc_info=True
            )
            raise

    async def add_new_search(self, command: AddNewSearchCommand) -> Search:
        """Add new search to database. Raises on failure."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                INSERT INTO searches (chat_id, query, price_min, price_max)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(command.chat_id),
                    command.query,
                    command.price_min,
                    command.price_max,
                ),
            )
            await self.connection.commit()

            search_id = cursor.lastrowid

            if search_id is None:
                raise RuntimeError("Failed to retrieve the last inserted ID.")

            search = Search(
                id=search_id,
                chat_id=str(command.chat_id),
                query=command.query,
                price_min=command.price_min,
                price_max=command.price_max,
            )

            logger.info(f"Added new search: id={search_id}, query='{command.query}'")
            return search
        except aiosqlite.IntegrityError as e:
            logger.error(f"Integrity error adding search: {e}", exc_info=True)
            raise
        except aiosqlite.Error as e:
            logger.error(f"Failed to add new search: {e}", exc_info=True)
            raise

    async def update_search(self, command: UpdateSearchCommand) -> bool:
        """Update search in database. Returns True if updated. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        updates = []
        parameters = []

        if command.query is not None:
            updates.append("query = ?")
            parameters.append(command.query)
        if command.price_min is not None:
            updates.append("price_min = ?")
            parameters.append(command.price_min)
        if command.price_max is not None:
            updates.append("price_max = ?")
            parameters.append(command.price_max)

        if not updates:
            return False  # Nothing to update

        updates.append("updated_at = datetime('now')")
        parameters.append(command.search_id)

        try:
            cursor = await self.connection.execute(
                f"""
                UPDATE searches
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                parameters,
            )

            await self.connection.commit()
            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated search id={command.search_id}")
            return updated
        except aiosqlite.IntegrityError as e:
            logger.error(
                f"Integrity error updating search id={command.search_id}: {e}",
                exc_info=True,
            )
            raise
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to update search id={command.search_id}: {e}", exc_info=True
            )
            raise

    async def delete_search(self, command: DeleteSearchCommand) -> bool:
        """Delete search from database. Returns True if deleted. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                DELETE FROM searches
                WHERE id = ?
                """,
                (command.search_id,),
            )
            await self.connection.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted search id={command.search_id}")
            return deleted
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to delete search id={command.search_id}: {e}", exc_info=True
            )
            raise

    async def add_listings_to_search(self, command: AddListingsForSearchCommand):
        """Add listings to search. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        if not command.listing_ids:
            return  # Nothing to add

        try:
            await self.connection.executemany(
                "INSERT OR IGNORE INTO search_listings (search_id, listing_id, silent) VALUES (?, ?, ?)",
                [
                    (command.search_id, lid, 1 if command.silent else 0)
                    for lid in command.listing_ids
                ],
            )
            await self.connection.commit()
            logger.debug(
                f"Added {len(command.listing_ids)} listings to search id={command.search_id} (silent={command.silent})"
            )
        except aiosqlite.IntegrityError as e:
            logger.error(
                f"Integrity error adding listings to search id={command.search_id}: {e}. "
                "This may indicate the search no longer exists (foreign key violation).",
                exc_info=True,
            )
            raise
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to add listings to search id={command.search_id}: {e}",
                exc_info=True,
            )
            raise

    async def filter_new_listings(self, query: FilterNewListingsQuery) -> list[int]:
        """Filter out existing listings, return only new ones. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")
        if not query.listing_ids:
            return []

        try:
            placeholders = ",".join("?" * len(query.listing_ids))
            cursor = await self.connection.execute(
                f"""
                SELECT listing_id FROM search_listings
                WHERE search_id = ? AND listing_id IN ({placeholders})
                """,
                (query.search_id, *query.listing_ids),
            )
            existing = {row["listing_id"] for row in await cursor.fetchall()}

            new_listings = [lid for lid in query.listing_ids if lid not in existing]
            logger.debug(
                f"Filtered {len(new_listings)} new listings out of {len(query.listing_ids)} "
                f"for search id={query.search_id}"
            )
            return new_listings
        except (aiosqlite.Error, KeyError) as e:
            logger.error(
                f"Failed to filter new listings for search id={query.search_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_total_listing_count_for_search(
        self, query: GetTotalListingCountForSearchQuery
    ) -> int:
        """Get total listing count for search. Returns 0 on not found. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                SELECT COUNT(*) as total FROM search_listings
                WHERE search_id = ?
                 """,
                (query.search_id,),
            )
            row = await cursor.fetchone()

            count = row["total"] if row else 0
            logger.debug(
                f"Total listing count for search id={query.search_id}: {count}"
            )
            return count
        except (aiosqlite.Error, KeyError) as e:
            logger.error(
                f"Failed to get listing count for search id={query.search_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_all_listings_for_search(
        self, command: DeleteAllListingsForSearchCommand
    ):
        """Delete all listings for a search. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                DELETE FROM search_listings
                WHERE search_id = ?
                """,
                (command.search_id,),
            )
            await self.connection.commit()
            deleted_count = cursor.rowcount
            logger.info(
                f"Deleted {deleted_count} listings for search id={command.search_id}"
            )
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to delete listings for search id={command.search_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_recent_found_items(
        self, query: GetRecentFoundItemsQuery
    ) -> list[dict]:
        """Get items found within the specified timeframe, grouped by search. Raises on error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        try:
            cursor = await self.connection.execute(
                """
                SELECT
                    sl.search_id,
                    s.query,
                    COUNT(*) as item_count
                FROM search_listings sl
                JOIN searches s ON sl.search_id = s.id
                WHERE sl.created_at >= datetime('now', ?) AND sl.silent = 0
                GROUP BY sl.search_id, s.query
                ORDER BY item_count DESC
                """,
                (f"-{query.hours} hours",),
            )
            rows = await cursor.fetchall()

            results = [
                {
                    "search_id": row["search_id"],
                    "query": row["query"],
                    "item_count": row["item_count"],
                }
                for row in rows
            ]

            logger.debug(
                f"Retrieved {len(results)} searches with items found in last {query.hours} hours"
            )
            return results
        except (aiosqlite.Error, KeyError) as e:
            logger.error(f"Failed to get recent found items: {e}", exc_info=True)
            raise
