"""
Database migration manager using yoyo-migrations.

This module handles applying and rolling back database schema migrations.
Migrations run synchronously at application startup before the async event loop.
"""

import logging
from pathlib import Path
from yoyo import read_migrations, get_backend

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database schema migrations using yoyo-migrations.

    Note: Migrations are synchronous and should be run at application startup
    before the async event loop is active.
    """

    def __init__(self, database_path: str, migrations_dir: str = "src/migrations"):
        """
        Initialize migration manager.

        Args:
            database_path: Path to SQLite database file
            migrations_dir: Directory containing migration files (default: "src/migrations")
        """
        self.database_path = database_path
        self.migrations_dir = Path(migrations_dir)

    def apply_migrations(self) -> bool:
        """
        Apply all pending migrations to the database.

        This runs synchronously and should be called before connecting with aiosqlite.
        Uses database locking to prevent concurrent migration issues.

        Returns:
            bool: True if successful, False on error
        """
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return False

        try:
            # For SQLite, use format: sqlite:///path/to/database.db
            backend = get_backend(f"sqlite:///{self.database_path}")
            migrations = read_migrations(str(self.migrations_dir))

            # Use lock to prevent concurrent migration execution
            with backend.lock():
                # Get list of migrations to apply
                to_apply = backend.to_apply(migrations)

                if to_apply:
                    logger.info(f"Applying {len(to_apply)} migration(s)...")
                    backend.apply_migrations(to_apply)
                    logger.info(f"Successfully applied {len(to_apply)} migration(s)")
                else:
                    logger.info("No new migrations to apply - database is up to date")

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False

    def rollback_migrations(self, count: int = 1) -> bool:
        """
        Rollback the last N migrations.

        Use with caution - this can result in data loss!

        Args:
            count: Number of migrations to rollback (default: 1)

        Returns:
            bool: True if successful, False on error
        """
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return False

        try:
            backend = get_backend(f"sqlite:///{self.database_path}")
            migrations = read_migrations(str(self.migrations_dir))

            with backend.lock():
                to_rollback = backend.to_rollback(migrations, count)

                if to_rollback:
                    logger.warning(f"Rolling back {len(to_rollback)} migration(s)...")
                    backend.rollback_migrations(to_rollback)
                    logger.info(
                        f"Successfully rolled back {len(to_rollback)} migration(s)"
                    )
                else:
                    logger.info("No migrations to rollback")

            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return False
