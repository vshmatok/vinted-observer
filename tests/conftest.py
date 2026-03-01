import pytest
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from src.search_processor.search_task import SearchTask
from src.search_processor.search_processor import SearchProcessor
from src.message_bus.message_bus import MessageBus
from src.monitoring.error_parser import ErrorParser
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.monitoring.monitor import Monitor
from src.repository.migrations import MigrationManager
from src.repository.repository import Repository
from src.telegram_bot.models.search import Search
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)


@pytest.fixture
def message_bus():
    """Create message bus instance."""
    return MessageBus()


@pytest.fixture
def mock_message_bus():
    bus = AsyncMock(spec=MessageBus)
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_vinted_client():
    client = AsyncMock(spec=VintedNetworkClient)
    client.search_items.return_value = []
    return client


@pytest.fixture
def sample_nike_search():
    return Search(
        id=1, chat_id="12345", query="nike shoes", price_min=10.0, price_max=100.0
    )


@pytest.fixture
def updated_search():
    return Search(id=2, chat_id="99999", query="adidas", price_min=5.0, price_max=50.0)


@pytest.fixture
async def search_task(mock_vinted_client, mock_message_bus, sample_nike_search):
    task = SearchTask(
        client=mock_vinted_client,
        message_bus=mock_message_bus,
        search=sample_nike_search,
        search_sleep_time=0,
    )
    yield task
    await task.stop()


@pytest.fixture
def mock_error_parser():
    parser = AsyncMock(spec=ErrorParser)
    parser.get_recent_errors.return_value = []
    return parser


@pytest.fixture
def mock_proxy_manager():
    pm = MagicMock(spec=ProxyManager)
    pm.proxies = []
    pm.healthy_proxies = []
    pm.failed_proxies = []
    return pm


@pytest.fixture
def monitor(mock_message_bus, mock_error_parser):
    return Monitor(
        message_bus=mock_message_bus,
        proxy_manager=None,
        startup_time=datetime(2026, 2, 21, 10, 0, 0),
        error_parser=mock_error_parser,
        status_items_timeframe_hours=1,
    )


@pytest.fixture
def monitor_with_proxy(mock_message_bus, mock_error_parser, mock_proxy_manager):
    return Monitor(
        message_bus=mock_message_bus,
        proxy_manager=mock_proxy_manager,
        startup_time=datetime(2026, 2, 21, 10, 0, 0),
        error_parser=mock_error_parser,
        status_items_timeframe_hours=1,
    )


@pytest.fixture
def valid_log_file(tmp_path):
    """Well-formed log lines matching the default format."""
    content = (
        "2026-02-19 10:00:01 - myapp - INFO - App started\n"
        "2026-02-19 10:00:02 - myapp - ERROR - Something broke\n"
        "2026-02-19 10:00:03 - myapp - CRITICAL - Fatal\n"
    )
    file = tmp_path / "valid.log"
    file.write_text(content)
    return file


@pytest.fixture
def malformed_log_file(tmp_path):
    """Lines that won't match the expected format."""
    content = (
        "not a log line at all\n"
        "ERROR without timestamp\n"
        "2026-02-19 - missing fields\n"
        "2026-02-19 10:00:01 - myapp - ERROR - Valid line among garbage\n"
    )
    file = tmp_path / "malformed.log"
    file.write_text(content)
    return file


@pytest.fixture
def empty_log_file(tmp_path):
    """An empty log file."""
    file = tmp_path / "empty.log"
    file.write_text("")
    return file


@pytest.fixture
def permission_denied_log_file(tmp_path):
    """A log file that exists but cannot be read due to permissions."""
    file = tmp_path / "noperm.log"
    file.write_text("2026-02-19 10:00:00 - app - ERROR - fail\n")
    os.chmod(file, 0o000)
    yield file
    os.chmod(file, 0o644)  # restore for cleanup


@pytest.fixture
def large_log_file(tmp_path):
    """A log file larger than 65KB to test tail reading."""
    file = tmp_path / "large.log"

    # Create a line that will be cut off at the 65KB boundary
    padding_line = "2026-02-19 09:00:00 - myapp - INFO - " + "x" * 200 + "\n"
    error_line = "2026-02-19 10:00:00 - myapp - ERROR - should be found\n"

    # Fill file beyond 65536 bytes: padding + one error at the end
    lines_needed = (65536 // len(padding_line)) + 10
    content = padding_line * lines_needed + error_line
    file.write_text(content)

    return file


@pytest.fixture
def special_chars_log_file(tmp_path):
    """Log file with special characters to ensure encoding is handled."""
    content = (
        "2026-02-19 10:00:00 - app - ERROR - failed - retry in 5s\n"
        "2026-02-19 10:00:01 - app - ERROR - regex [a-z]+ and (group) failed\n"
        "2026-02-19 10:00:02 - app - ERROR - connection to München failed\n"
    )
    file = tmp_path / "special.log"
    file.write_text(content)
    return file


@pytest.fixture
def all_errors_log_file(tmp_path):
    """Log file where all lines are errors"""
    content = (
        "2026-02-19 10:00:00 - app - ERROR - first\n"
        "2026-02-19 10:00:01 - app - CRITICAL - second\n"
        "2026-02-19 10:00:02 - app - ERROR - third\n"
    )
    file = tmp_path / "all_errors.log"
    file.write_text(content)
    return file


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
def mock_vinted_client_class(mocker, mock_vinted_client):
    """Patches VintedNetworkClient.create to return mock_vinted_client."""
    return mocker.patch.object(
        VintedNetworkClient,
        "create",
        new_callable=AsyncMock,
        return_value=mock_vinted_client,
    )


@pytest.fixture
async def search_processor(
    mock_message_bus, mock_proxy_manager, mock_vinted_client_class
):
    """SearchProcessor with mocked dependencies, setup and torn down."""
    processor = SearchProcessor(
        message_bus=mock_message_bus,
        user_agents=[{"ua": "TestAgent"}],
        proxy_manager=mock_proxy_manager,
        domain=VintedDomain.PL,
    )
    await processor.setup()
    yield processor
    await processor.close()
