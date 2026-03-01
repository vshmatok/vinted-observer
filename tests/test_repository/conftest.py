import pytest
from unittest.mock import MagicMock

from src.repository.repository import Repository
from src.repository.migrations import MigrationManager
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)


SCHEMA = """
CREATE TABLE searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    query TEXT NOT NULL,
    price_min REAL NOT NULL,
    price_max REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE search_listings (
    search_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    silent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (search_id, listing_id),
    FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
);

CREATE INDEX idx_search_listings_search_created_at
    ON search_listings(search_id, created_at DESC);
"""


@pytest.fixture
async def file_repository(tmp_path):
    """File-based Repository for testing pragmas like WAL that don't work with :memory:."""
    db_path = str(tmp_path / "test.db")
    repo = Repository(db_path=db_path)
    await repo.connect()
    await repo.connection.executescript(  # pyright: ignore[reportOptionalMemberAccess]
        SCHEMA
    )
    yield repo
    await repo.close()


@pytest.fixture
async def repository():
    """In-memory Repository with schema applied. Yields and closes on teardown."""
    repo = Repository(db_path=":memory:")
    await repo.connect()  # dont check if connection is None since we know it will be connected here
    await repo.connection.executescript(  # pyright: ignore[reportOptionalMemberAccess]
        SCHEMA
    )
    yield repo
    await repo.close()


@pytest.fixture
def disconnected_repository():
    """Repository that has NOT been connected (connection is None)."""
    return Repository(db_path=":memory:")


@pytest.fixture
def search_factory(repository):
    """Returns an async callable to quickly create searches with defaults."""

    async def _create(
        chat_id="123456",
        query="nike shoes",
        price_min=10.0,
        price_max=100.0,
    ):
        command = AddNewSearchCommand(
            chat_id=chat_id,
            query=query,
            price_min=price_min,
            price_max=price_max,
        )
        return await repository.add_new_search(command)

    return _create


@pytest.fixture
def search_with_listings_factory(repository, search_factory):
    """Returns an async callable to create a search with listings attached."""

    async def _create(
        listing_ids=None,
        silent=False,
        **search_kwargs,
    ):
        if listing_ids is None:
            listing_ids = [1, 2, 3]
        search = await search_factory(**search_kwargs)
        await repository.add_listings_to_search(
            AddListingsForSearchCommand(
                search_id=search.id,
                listing_ids=listing_ids,
                silent=silent,
            )
        )
        return search

    return _create


@pytest.fixture
def mock_backend():
    """MagicMock yoyo backend with lock/apply/rollback methods."""
    backend = MagicMock()
    backend.lock.return_value.__enter__ = MagicMock()
    backend.lock.return_value.__exit__ = MagicMock(return_value=False)
    return backend


@pytest.fixture
def mock_migrations():
    """List of 2 MagicMock migration objects."""
    return [MagicMock(name="migration_001"), MagicMock(name="migration_002")]


@pytest.fixture
def migration_manager(tmp_path):
    """MigrationManager with real tmp_path directories."""
    db_path = tmp_path / "test.db"
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    return MigrationManager(
        database_path=str(db_path), migrations_dir=str(migrations_dir)
    )


@pytest.fixture
def patch_get_backend(mocker, mock_backend):
    """Patches get_backend to return mock_backend."""
    mocker.patch("src.repository.migrations.get_backend", return_value=mock_backend)


@pytest.fixture
def patch_read_migrations(mocker, mock_migrations):
    """Patches read_migrations to return mock_migrations."""
    mocker.patch(
        "src.repository.migrations.read_migrations", return_value=mock_migrations
    )


@pytest.fixture
def patch_yoyo(patch_get_backend, patch_read_migrations):
    """Patches both get_backend and read_migrations."""
    pass
