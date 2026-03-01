import asyncio
import pytest
import aiosqlite
from src.repository.repository import Repository
from src.telegram_bot.models.search import Search
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.commands.delete_search_command import DeleteSearchCommand
from src.message_bus.commands.update_search_command import UpdateSearchCommand
from src.message_bus.commands.delete_all_listings_for_search_command import (
    DeleteAllListingsForSearchCommand,
)
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.message_bus.queries.filter_new_listings_query import FilterNewListingsQuery
from src.message_bus.queries.get_total_listing_count_for_search_query import (
    GetTotalListingCountForSearchQuery,
)
from src.message_bus.queries.get_recent_found_items_query import (
    GetRecentFoundItemsQuery,
)


# ============================================================================
# connect() tests
# ============================================================================


async def test_connect_creates_connection():
    """connection is not None after connect."""
    repo = Repository(db_path=":memory:")
    await repo.connect()
    try:
        assert repo.connection is not None
        assert repo.connection.row_factory is aiosqlite.Row
    finally:
        await repo.close()


async def test_connect_called_twice(mocker):
    """Calling connect() twice does not raise an error."""
    mock_connection = mocker.patch(
        "src.repository.repository.aiosqlite.connect", side_effect=aiosqlite.connect
    )
    repo = Repository(db_path=":memory:")

    try:
        await repo.connect()
        await repo.connect()
        mock_connection.assert_called_once()  # connect should only be called once
    finally:
        await repo.close()


# Dont use in memory database for this test since journal_mode=wal is not supported there
async def test_connect_sets_pragmas(file_repository):
    """All pragmas (journal_mode, foreign_keys, busy_timeout) are set after connect."""
    assert file_repository.connection is not None

    cursor = await file_repository.connection.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "wal"

    cursor = await file_repository.connection.execute("PRAGMA foreign_keys")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1

    cursor = await file_repository.connection.execute("PRAGMA busy_timeout")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == file_repository.busy_timeout


async def test_connect_raises_on_aiosqlite_error(mocker):
    """aiosqlite.Error during connect is re-raised."""
    mocker.patch(
        "src.repository.repository.aiosqlite.connect",
        side_effect=aiosqlite.Error("connection failed"),
    )
    repo = Repository(db_path=":memory:")

    with pytest.raises(aiosqlite.Error, match="connection failed"):
        await repo.connect()

    assert repo.connection is None


async def test_connect_raises_on_unexpected_error(mocker):
    """Unexpected exception during connect is re-raised."""
    mocker.patch(
        "src.repository.repository.aiosqlite.connect",
        side_effect=OSError("disk error"),
    )
    repo = Repository(db_path=":memory:")

    with pytest.raises(OSError, match="disk error"):
        await repo.connect()

    assert repo.connection is None


async def test_connect_pragma_failure_closes_connection(mocker):
    """aiosqlite.Error during pragma commit closes connection and sets it to None."""
    mocker.patch(
        "src.repository.repository.aiosqlite.Connection.commit",
        side_effect=aiosqlite.Error("commit failed"),
    )
    repo = Repository(db_path=":memory:")

    with pytest.raises(aiosqlite.Error, match="commit failed"):
        await repo.connect()

    assert repo.connection is None


# ============================================================================
# close() tests
# ============================================================================


async def test_close_sets_connection_to_none():
    """connection is None after close."""
    repo = Repository(db_path=":memory:")
    await repo.connect()
    await repo.close()
    assert repo.connection is None


async def test_close_when_not_connected():
    """No error when closing a never-connected repository."""
    repo = Repository(db_path=":memory:")
    assert repo.connection is None
    await repo.close()  # should not raise
    assert repo.connection is None


async def test_close_called_twice(mocker):
    """Calling close() twice only closes the connection once."""
    mock_close = mocker.patch(
        "src.repository.repository.aiosqlite.Connection.close",
        side_effect=aiosqlite.Connection.close,
    )
    repo = Repository(db_path=":memory:")
    await repo.connect()
    await repo.close()
    await repo.close()
    mock_close.assert_called_once()
    assert repo.connection is None


async def test_close_sets_connection_to_none_on_error(mocker):
    """Connection is set to None even when close() raises."""
    mocker.patch(
        "src.repository.repository.aiosqlite.Connection.close",
        side_effect=Exception("close failed"),
    )
    repo = Repository(db_path=":memory:")
    await repo.connect()
    await repo.close()  # should not raise
    assert repo.connection is None


# ============================================================================
# periodic_cleanup() tests
# ============================================================================


async def test_periodic_cleanup_breaks_when_connection_none(mocker, repository):
    """Exits loop without calling cleanup when connection is None."""
    mock_cleanup = mocker.patch.object(repository, "cleanup_old_listings")

    repository.connection = None
    await repository.periodic_cleanup(interval_hours=1)  # should return without error

    mock_cleanup.assert_not_called()


async def test_periodic_cleanup_passes_correct_sleep_duration(mocker, repository):
    """sleep is called with interval_hours * 3600."""
    captured_seconds = None

    async def mock_sleep(seconds):
        nonlocal captured_seconds
        captured_seconds = seconds
        raise asyncio.CancelledError()  # cancel immediately to exit the loop

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)
    mocker.patch.object(repository, "cleanup_old_listings")

    with pytest.raises(asyncio.CancelledError):
        await repository.periodic_cleanup(interval_hours=6)

    assert captured_seconds == 6 * 3600


async def test_periodic_cleanup_calls_cleanup_old_listings(mocker, repository):
    """Verifies cleanup_old_listings is called during periodic_cleanup."""
    cancel_on_next_call = False

    # Dont remove _seconds parameter since it's needed for the side_effect signature, even if we ignore it here
    async def mock_sleep(_seconds):
        nonlocal cancel_on_next_call
        if cancel_on_next_call:
            raise asyncio.CancelledError()
        cancel_on_next_call = True

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)
    mock_cleanup = mocker.patch.object(repository, "cleanup_old_listings")

    with pytest.raises(asyncio.CancelledError):
        await repository.periodic_cleanup(interval_hours=1)

    mock_cleanup.assert_called_once()


async def test_periodic_cleanup_continues_on_cleanup_exception(mocker, repository):
    """Loop continues after a cleanup error."""
    call_count = 0

    # Dont remove _seconds parameter since it's needed for the side_effect signature, even if we ignore it here
    async def mock_sleep(_seconds):
        nonlocal call_count
        call_count += 1
        # Let two sleeps pass (so cleanup runs twice), cancel on the third
        if call_count >= 3:
            raise asyncio.CancelledError()

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)

    # First call raises, second call succeeds
    mock_cleanup = mocker.patch.object(
        repository,
        "cleanup_old_listings",
        side_effect=[RuntimeError("db error"), None],
    )

    with pytest.raises(asyncio.CancelledError):
        await repository.periodic_cleanup(interval_hours=1)

    assert mock_cleanup.call_count == 2


# ============================================================================
# cleanup_old_listings() tests
# ============================================================================


async def test_cleanup_old_listings_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.cleanup_old_listings()


async def test_cleanup_old_listings_deletes_old_records(
    repository, search_with_listings_factory
):
    """Backdated listings are removed."""
    search = await search_with_listings_factory(listing_ids=[1, 2])

    # Backdate all listings to 10 days ago
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-10 days') WHERE search_id = ?",
        (search.id,),
    )
    await repository.connection.commit()

    await repository.cleanup_old_listings(days=7)

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_cleanup_old_listings_preserves_recent_records(
    repository, search_with_listings_factory
):
    """Recent listings are kept."""
    search = await search_with_listings_factory(listing_ids=[1, 2])

    # These are fresh — should survive a 7-day cleanup
    await repository.cleanup_old_listings(days=7)

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 2


async def test_cleanup_old_listings_custom_days_parameter(
    repository, search_with_listings_factory
):
    """Respects the days argument — only listings older than threshold are deleted."""
    search = await search_with_listings_factory(listing_ids=[1, 2, 3])

    # Backdate listing 1 to 10 days ago, listing 2 to 3 days ago, leave listing 3 fresh
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-10 days') "
        "WHERE search_id = ? AND listing_id = 1",
        (search.id,),
    )
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-3 days') "
        "WHERE search_id = ? AND listing_id = 2",
        (search.id,),
    )
    await repository.connection.commit()

    # Cleanup with 5-day threshold — only listing 1 should be deleted
    await repository.cleanup_old_listings(days=5)
    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 2


async def test_cleanup_old_listings_noop_on_empty_table(repository):
    """No error when no listings exist at all."""
    await repository.cleanup_old_listings(days=7)  # should not raise

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings"
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_cleanup_old_listings_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during cleanup is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.cleanup_old_listings()


# ============================================================================
# get_all_searches() tests
# ============================================================================


async def test_get_all_searches_empty(repository):
    """Empty list when no searches exist."""
    result = await repository.get_all_searches(GetAllSearchesQuery())
    assert result == []


async def test_get_all_searches_returns_all(repository, search_factory):
    """Returns all inserted searches."""
    await search_factory(query="first")
    await search_factory(query="second")
    await search_factory(query="third")

    result = await repository.get_all_searches(GetAllSearchesQuery())
    assert len(result) == 3


async def test_get_all_searches_ordered_by_updated_at_desc(repository, search_factory):
    """Most recently updated search comes first due to ORDER BY updated_at DESC."""
    older = await search_factory(query="older")
    newer = await search_factory(query="newer")

    # Backdate the older search so it sorts last
    await repository.connection.execute(
        "UPDATE searches SET updated_at = datetime('now', '-1 day') WHERE id = ?",
        (older.id,),
    )
    await repository.connection.commit()

    result = await repository.get_all_searches(GetAllSearchesQuery())
    assert result[0].id == newer.id
    assert result[1].id == older.id


async def test_get_all_searches_returns_search_objects(repository, search_factory):
    """All returned items are Search instances."""
    await search_factory()
    result = await repository.get_all_searches(GetAllSearchesQuery())
    assert all(isinstance(s, Search) for s in result)


async def test_get_all_searches_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.get_all_searches(GetAllSearchesQuery())


async def test_get_all_searches_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during query is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.get_all_searches(GetAllSearchesQuery())


async def test_get_all_searches_raises_on_key_error(mocker, repository, search_factory):
    """KeyError from malformed row is re-raised."""
    await search_factory()
    mock_cursor = mocker.AsyncMock()
    mock_cursor.fetchall.return_value = [{"bad_key": "value"}]
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )

    with pytest.raises(KeyError):
        await repository.get_all_searches(GetAllSearchesQuery())


# ============================================================================
# get_search_by_id() tests
# ============================================================================


async def test_get_search_by_id_found(repository, search_factory):
    """Returns correct search."""
    created = await search_factory(query="find me")
    result = await repository.get_search_by_id(GetSearchByIdQuery(search_id=created.id))
    assert result is not None
    assert result.id == created.id
    assert result.query == "find me"


async def test_get_search_by_id_not_found(repository):
    """Returns None for nonexistent id."""
    result = await repository.get_search_by_id(GetSearchByIdQuery(search_id=99999))
    assert result is None


async def test_get_search_by_id_returns_correct_one(repository, search_factory):
    """Returns the right search among multiple."""
    await search_factory(query="first")
    target = await search_factory(query="target")
    await search_factory(query="third")

    result = await repository.get_search_by_id(GetSearchByIdQuery(search_id=target.id))
    assert result.query == "target"


async def test_get_search_by_id_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.get_search_by_id(GetSearchByIdQuery(search_id=1))


async def test_get_search_by_id_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during query is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.get_search_by_id(GetSearchByIdQuery(search_id=1))


async def test_get_search_by_id_raises_on_key_error(mocker, repository, search_factory):
    """KeyError from malformed row is re-raised."""
    await search_factory()
    mock_cursor = mocker.AsyncMock()
    mock_cursor.fetchone.return_value = {"bad_key": "value"}
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )

    with pytest.raises(KeyError):
        await repository.get_search_by_id(GetSearchByIdQuery(search_id=1))


# ============================================================================
# add_new_search() tests
# ============================================================================


async def test_add_new_search_returns_search_with_id(repository):
    """Returned Search has valid id and matching fields."""
    command = AddNewSearchCommand(
        chat_id="12345", query="nike shoes", price_min=10.0, price_max=100.0
    )
    search = await repository.add_new_search(command)

    assert isinstance(search, Search)
    assert search.id is not None
    assert search.id > 0
    assert search.query == "nike shoes"
    assert search.price_min == 10.0
    assert search.price_max == 100.0


async def test_add_new_search_auto_increments_id(repository, search_factory):
    """Second search gets a higher id."""
    first = await search_factory(query="first")
    second = await search_factory(query="second")
    assert second.id > first.id


async def test_add_new_search_persists_to_db(repository, search_factory):
    """Search is persisted in the database."""
    created = await search_factory()
    cursor = await repository.connection.execute(
        "SELECT id, query FROM searches WHERE id = ?",
        (created.id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["id"] == created.id
    assert row["query"] == created.query


async def test_add_new_search_converts_chat_id_to_string(repository):
    """int chat_id is stored as string."""
    command = AddNewSearchCommand(
        chat_id=99999, query="test", price_min=0.0, price_max=50.0
    )
    search = await repository.add_new_search(command)
    assert search.chat_id == "99999"


async def test_add_new_search_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    command = AddNewSearchCommand(
        chat_id="123", query="test", price_min=0.0, price_max=50.0
    )
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.add_new_search(command)


async def test_add_new_search_raises_when_lastrowid_is_none(mocker, repository):
    """RuntimeError when cursor.lastrowid returns None."""

    mock_cursor = mocker.MagicMock()
    mock_cursor.lastrowid = None
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )
    mocker.patch.object(repository.connection, "commit")

    command = AddNewSearchCommand(
        chat_id="123", query="test", price_min=0.0, price_max=50.0
    )
    with pytest.raises(RuntimeError, match="Failed to retrieve the last inserted ID"):
        await repository.add_new_search(command)


async def test_add_new_search_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during insert is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    command = AddNewSearchCommand(
        chat_id="123", query="test", price_min=0.0, price_max=50.0
    )
    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.add_new_search(command)


async def test_add_new_search_raises_on_integrity_error(mocker, repository):
    """aiosqlite.IntegrityError during insert is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.IntegrityError("constraint violation"),
    )

    command = AddNewSearchCommand(
        chat_id="123", query="test", price_min=0.0, price_max=50.0
    )
    with pytest.raises(aiosqlite.IntegrityError, match="constraint violation"):
        await repository.add_new_search(command)


# ============================================================================
# update_search() tests
# ============================================================================


async def test_update_search_query_only(repository, search_factory):
    """Updates only the query field."""
    search = await search_factory(query="old query")
    await repository.update_search(
        UpdateSearchCommand(search_id=search.id, query="new query")
    )

    cursor = await repository.connection.execute(
        "SELECT query, price_min, price_max FROM searches WHERE id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["query"] == "new query"
    assert row["price_min"] == search.price_min
    assert row["price_max"] == search.price_max


async def test_update_search_price_min_only(repository, search_factory):
    """Updates only price_min."""
    search = await search_factory(price_min=10.0)
    await repository.update_search(
        UpdateSearchCommand(search_id=search.id, price_min=25.0)
    )

    cursor = await repository.connection.execute(
        "SELECT query, price_min, price_max FROM searches WHERE id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["price_min"] == 25.0
    assert row["query"] == search.query


async def test_update_search_price_max_only(repository, search_factory):
    """Updates only price_max."""
    search = await search_factory(price_max=100.0)
    await repository.update_search(
        UpdateSearchCommand(search_id=search.id, price_max=200.0)
    )

    cursor = await repository.connection.execute(
        "SELECT query, price_min, price_max FROM searches WHERE id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["price_max"] == 200.0
    assert row["query"] == search.query


async def test_update_search_all_fields(repository, search_factory):
    """Updates all optional fields at once."""
    search = await search_factory()
    await repository.update_search(
        UpdateSearchCommand(
            search_id=search.id,
            query="updated",
            price_min=1.0,
            price_max=999.0,
        )
    )

    cursor = await repository.connection.execute(
        "SELECT query, price_min, price_max FROM searches WHERE id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["query"] == "updated"
    assert row["price_min"] == 1.0
    assert row["price_max"] == 999.0


async def test_update_search_returns_true_on_success(repository, search_factory):
    """Returns True when a row is updated."""
    search = await search_factory()
    result = await repository.update_search(
        UpdateSearchCommand(search_id=search.id, query="changed")
    )
    assert result is True


async def test_update_search_returns_false_for_nonexistent_id(repository):
    """Returns False for a missing id."""
    result = await repository.update_search(
        UpdateSearchCommand(search_id=99999, query="nope")
    )
    assert result is False


async def test_update_search_no_fields_returns_false(repository, search_factory):
    """Returns False when nothing to update."""
    search = await search_factory()
    result = await repository.update_search(UpdateSearchCommand(search_id=search.id))
    assert result is False


async def test_update_search_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.update_search(
            UpdateSearchCommand(search_id=1, query="test")
        )


async def test_update_search_raises_on_integrity_error(mocker, repository, search_factory):
    """aiosqlite.IntegrityError during update is re-raised."""
    search = await search_factory()
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.IntegrityError("constraint violation"),
    )

    with pytest.raises(aiosqlite.IntegrityError, match="constraint violation"):
        await repository.update_search(
            UpdateSearchCommand(search_id=search.id, query="changed")
        )


async def test_update_search_raises_on_db_error(mocker, repository, search_factory):
    """aiosqlite.Error during update is re-raised."""
    search = await search_factory()
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.update_search(
            UpdateSearchCommand(search_id=search.id, query="changed")
        )


async def test_update_search_bumps_updated_at(repository, search_factory):
    """updated_at changes after an update."""
    search = await search_factory()

    # Backdate updated_at so we can detect the change
    await repository.connection.execute(
        "UPDATE searches SET updated_at = datetime('now', '-1 day') WHERE id = ?",
        (search.id,),
    )
    await repository.connection.commit()

    cursor = await repository.connection.execute(
        "SELECT updated_at FROM searches WHERE id = ?", (search.id,)
    )
    before = (await cursor.fetchone())["updated_at"]

    await repository.update_search(
        UpdateSearchCommand(search_id=search.id, query="changed")
    )

    cursor = await repository.connection.execute(
        "SELECT updated_at FROM searches WHERE id = ?", (search.id,)
    )
    after = (await cursor.fetchone())["updated_at"]

    assert after > before


# ============================================================================
# delete_search() tests
# ============================================================================


async def test_delete_search_returns_true(repository, search_factory):
    """Returns True when deleted."""
    search = await search_factory()
    result = await repository.delete_search(DeleteSearchCommand(search_id=search.id))
    assert result is True


async def test_delete_search_returns_false_for_nonexistent(repository):
    """Returns False for a missing id."""
    result = await repository.delete_search(DeleteSearchCommand(search_id=99999))
    assert result is False


async def test_delete_search_removes_from_db(repository, search_factory):
    """Row no longer exists after deletion."""
    search = await search_factory()
    await repository.delete_search(DeleteSearchCommand(search_id=search.id))

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM searches WHERE id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_delete_search_cascades_to_listings(
    repository, search_with_listings_factory
):
    """Foreign key CASCADE deletes associated listings."""
    search = await search_with_listings_factory(listing_ids=[100, 200, 300])

    is_search_removed = await repository.delete_search(DeleteSearchCommand(search_id=search.id))
    assert is_search_removed is True

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_delete_search_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.delete_search(DeleteSearchCommand(search_id=1))


async def test_delete_search_raises_on_db_error(mocker, repository, search_factory):
    """aiosqlite.Error during delete is re-raised."""
    search = await search_factory()
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.delete_search(DeleteSearchCommand(search_id=search.id))


# ============================================================================
# add_listings_to_search() tests
# ============================================================================


async def test_add_listings_inserts_records(repository, search_factory):
    """Count matches after insert."""
    search = await search_factory()
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[1, 2, 3])
    )

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 3


async def test_add_listings_empty_list_is_noop(repository, search_factory):
    """No rows inserted for empty listing_ids."""
    search = await search_factory()

    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[])
    )

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_add_listings_duplicate_ignored(repository, search_factory):
    """INSERT OR IGNORE behavior — duplicates are silently skipped."""
    search = await search_factory()
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[1, 2])
    )
    # Insert again with overlap
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[2, 3])
    )

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 3  # 1, 2, 3 — not 4


async def test_add_listings_silent_flag(repository, search_factory):
    """silent=True sets the silent column to 1."""
    search = await search_factory()
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[42], silent=True)
    )

    cursor = await repository.connection.execute(
        "SELECT silent FROM search_listings WHERE search_id = ? AND listing_id = ?",
        (search.id, 42),
    )
    row = await cursor.fetchone()
    assert row["silent"] == 1


async def test_add_listings_default_silent_stores_zero(repository, search_factory):
    """Default silent=False stores 0 in the silent column."""
    search = await search_factory()
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(search_id=search.id, listing_ids=[42])
    )

    cursor = await repository.connection.execute(
        "SELECT silent FROM search_listings WHERE search_id = ? AND listing_id = ?",
        (search.id, 42),
    )
    row = await cursor.fetchone()
    assert row["silent"] == 0


async def test_add_listings_foreign_key_violation(repository):
    """IntegrityError for non-existent search_id."""
    with pytest.raises(aiosqlite.IntegrityError):
        await repository.add_listings_to_search(
            AddListingsForSearchCommand(search_id=99999, listing_ids=[1, 2])
        )


async def test_add_listings_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.add_listings_to_search(
            AddListingsForSearchCommand(search_id=1, listing_ids=[1])
        )


async def test_add_listings_raises_on_db_error(mocker, repository, search_factory):
    """aiosqlite.Error during executemany is re-raised."""
    search = await search_factory()
    mocker.patch.object(
        repository.connection,
        "executemany",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.add_listings_to_search(
            AddListingsForSearchCommand(search_id=search.id, listing_ids=[1, 2])
        )


# ============================================================================
# filter_new_listings() tests
# ============================================================================


async def test_filter_new_listings_all_new(repository, search_factory):
    """All returned when none exist in DB."""
    search = await search_factory()
    result = await repository.filter_new_listings(
        FilterNewListingsQuery(search_id=search.id, listing_ids=[1, 2, 3])
    )
    assert result == [1, 2, 3]


async def test_filter_new_listings_none_new(repository, search_with_listings_factory):
    """Empty when all already exist."""
    search = await search_with_listings_factory(listing_ids=[1, 2, 3])

    result = await repository.filter_new_listings(
        FilterNewListingsQuery(search_id=search.id, listing_ids=[1, 2, 3])
    )
    assert result == []


async def test_filter_new_listings_mixed(repository, search_with_listings_factory):
    """Only new ones returned."""
    search = await search_with_listings_factory(listing_ids=[1, 2])

    result = await repository.filter_new_listings(
        FilterNewListingsQuery(search_id=search.id, listing_ids=[2, 3, 4])
    )
    assert result == [3, 4]


async def test_filter_new_listings_empty_input(repository, search_factory):
    """Empty in, empty out."""
    search = await search_factory()
    result = await repository.filter_new_listings(
        FilterNewListingsQuery(search_id=search.id, listing_ids=[])
    )
    assert result == []


async def test_filter_new_listings_cross_search_isolation(
    repository, search_with_listings_factory, search_factory
):
    """Listings from search A don't affect filtering for search B."""
    await search_with_listings_factory(query="search a", listing_ids=[1, 2, 3])
    search_b = await search_factory(query="search b")

    # Listing 1 exists in search A but should be "new" for search B
    result = await repository.filter_new_listings(
        FilterNewListingsQuery(search_id=search_b.id, listing_ids=[1, 2, 3])
    )
    assert result == [1, 2, 3]


async def test_filter_new_listings_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.filter_new_listings(
            FilterNewListingsQuery(search_id=1, listing_ids=[1])
        )


async def test_filter_new_listings_raises_on_db_error(mocker, repository, search_factory):
    """aiosqlite.Error during query is re-raised."""
    search = await search_factory()
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.filter_new_listings(
            FilterNewListingsQuery(search_id=search.id, listing_ids=[1, 2])
        )


async def test_filter_new_listings_raises_on_key_error(mocker, repository, search_factory):
    """KeyError from malformed row is re-raised."""
    search = await search_factory()
    mock_cursor = mocker.AsyncMock()
    mock_cursor.fetchall.return_value = [{"bad_key": "value"}]
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )

    with pytest.raises(KeyError):
        await repository.filter_new_listings(
            FilterNewListingsQuery(search_id=search.id, listing_ids=[1, 2])
        )


# ============================================================================
# get_total_listing_count_for_search() tests
# ============================================================================


async def test_get_total_listing_count_no_listings(repository, search_factory):
    """Returns 0 when no listings exist."""
    search = await search_factory()
    count = await repository.get_total_listing_count_for_search(
        GetTotalListingCountForSearchQuery(search_id=search.id)
    )
    assert count == 0


async def test_get_total_listing_count_with_listings(
    repository, search_with_listings_factory
):
    """Returns correct count."""
    search = await search_with_listings_factory(listing_ids=[10, 20, 30, 40])

    count = await repository.get_total_listing_count_for_search(
        GetTotalListingCountForSearchQuery(search_id=search.id)
    )
    assert count == 4


async def test_get_total_listing_count_nonexistent_search(repository):
    """Returns 0 for nonexistent search."""
    count = await repository.get_total_listing_count_for_search(
        GetTotalListingCountForSearchQuery(search_id=99999)
    )
    assert count == 0


async def test_get_total_listing_count_cross_search_isolation(
    repository, search_with_listings_factory
):
    """Listings from other searches are not counted."""
    target = await search_with_listings_factory(query="target", listing_ids=[1, 2])
    await search_with_listings_factory(query="other", listing_ids=[3, 4, 5])

    count = await repository.get_total_listing_count_for_search(
        GetTotalListingCountForSearchQuery(search_id=target.id)
    )
    assert count == 2


async def test_get_total_listing_count_raises_when_disconnected(
    disconnected_repository,
):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.get_total_listing_count_for_search(
            GetTotalListingCountForSearchQuery(search_id=1)
        )


async def test_get_total_listing_count_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during query is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.get_total_listing_count_for_search(
            GetTotalListingCountForSearchQuery(search_id=1)
        )


async def test_get_total_listing_count_raises_on_key_error(mocker, repository):
    """KeyError from malformed row is re-raised."""
    mock_cursor = mocker.AsyncMock()
    mock_cursor.fetchone.return_value = {"bad_key": "value"}
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )

    with pytest.raises(KeyError):
        await repository.get_total_listing_count_for_search(
            GetTotalListingCountForSearchQuery(search_id=1)
        )


# ============================================================================
# delete_all_listings_for_search() tests
# ============================================================================


async def test_delete_all_listings_removes_all(
    repository, search_with_listings_factory
):
    """Count is 0 after delete."""
    search = await search_with_listings_factory(listing_ids=[1, 2, 3])

    await repository.delete_all_listings_for_search(
        DeleteAllListingsForSearchCommand(search_id=search.id)
    )

    cursor = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search.id,),
    )
    row = await cursor.fetchone()
    assert row["total"] == 0


async def test_delete_all_listings_only_affects_target_search(
    repository, search_with_listings_factory
):
    """Other search's listings remain."""
    search_a = await search_with_listings_factory(query="a", listing_ids=[1, 2])
    search_b = await search_with_listings_factory(query="b", listing_ids=[3, 4])

    await repository.delete_all_listings_for_search(
        DeleteAllListingsForSearchCommand(search_id=search_a.id)
    )

    cursor_a = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search_a.id,),
    )
    row_a = await cursor_a.fetchone()
    cursor_b = await repository.connection.execute(
        "SELECT COUNT(*) as total FROM search_listings WHERE search_id = ?",
        (search_b.id,),
    )
    row_b = await cursor_b.fetchone()
    assert row_a["total"] == 0
    assert row_b["total"] == 2


async def test_delete_all_listings_noop_when_none_exist(repository, search_factory):
    """No error when no listings exist."""
    search = await search_factory()
    await repository.delete_all_listings_for_search(
        DeleteAllListingsForSearchCommand(search_id=search.id)
    )  # should not raise


async def test_delete_all_listings_raises_when_disconnected(disconnected_repository):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.delete_all_listings_for_search(
            DeleteAllListingsForSearchCommand(search_id=1)
        )


async def test_delete_all_listings_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during delete is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.delete_all_listings_for_search(
            DeleteAllListingsForSearchCommand(search_id=1)
        )


# ============================================================================
# get_recent_found_items() tests
# ============================================================================


async def test_get_recent_found_items_empty(repository):
    """Empty list when no data."""
    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert result == []


async def test_get_recent_found_items_returns_correct_structure(
    repository, search_with_listings_factory
):
    """Dict keys: search_id, query, item_count."""
    search = await search_with_listings_factory(query="nike", listing_ids=[1, 2, 3])

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert len(result) == 1
    item = result[0]
    assert set(item.keys()) == {"search_id", "query", "item_count"}
    assert item["search_id"] == search.id
    assert item["query"] == "nike"
    assert item["item_count"] == 3


async def test_get_recent_found_items_excludes_silent(
    repository, search_with_listings_factory
):
    """Silent listings are not counted."""
    search = await search_with_listings_factory(listing_ids=[1, 2], silent=False)
    # Add 3 silent listings to the same search
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(
            search_id=search.id, listing_ids=[3, 4, 5], silent=True
        )
    )

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert len(result) == 1
    assert result[0]["item_count"] == 2


async def test_get_recent_found_items_respects_hours_parameter(
    repository, search_with_listings_factory
):
    """Backdated items excluded by hours parameter."""
    search = await search_with_listings_factory(listing_ids=[1, 2])

    # Backdate listings to 48 hours ago
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-48 hours') WHERE search_id = ?",
        (search.id,),
    )
    await repository.connection.commit()

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=1))
    assert result == []


async def test_get_recent_found_items_counts_only_recent(
    repository, search_with_listings_factory
):
    """Only listings within the time range are counted."""
    search = await search_with_listings_factory(listing_ids=[1, 2, 3])

    # Backdate listing 1 beyond the time range
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-48 hours') "
        "WHERE search_id = ? AND listing_id = 1",
        (search.id,),
    )
    await repository.connection.commit()

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert len(result) == 1
    assert result[0]["item_count"] == 2


async def test_get_recent_found_items_counts_only_non_silent_and_recent(
    repository, search_factory
):
    """Only non-silent listings within the time range are counted; silent and old are excluded."""
    search = await search_factory()
    # 2 non-silent recent
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(
            search_id=search.id, listing_ids=[1, 2], silent=False
        )
    )
    # 1 silent recent
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(
            search_id=search.id, listing_ids=[3], silent=True
        )
    )
    # 1 non-silent but old
    await repository.add_listings_to_search(
        AddListingsForSearchCommand(
            search_id=search.id, listing_ids=[4], silent=False
        )
    )
    await repository.connection.execute(
        "UPDATE search_listings SET created_at = datetime('now', '-48 hours') "
        "WHERE search_id = ? AND listing_id = 4",
        (search.id,),
    )
    await repository.connection.commit()

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert len(result) == 1
    assert result[0]["item_count"] == 2


async def test_get_recent_found_items_multiple_searches_ordered_by_count_desc(
    repository, search_with_listings_factory
):
    """Multiple searches returned, ordered by item_count DESC."""
    await search_with_listings_factory(query="few", listing_ids=[1, 2])
    await search_with_listings_factory(query="many", listing_ids=[10, 20, 30, 40, 50])
    await search_with_listings_factory(query="mid", listing_ids=[100, 200, 300])

    result = await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
    assert len(result) == 3
    assert result[0]["query"] == "many"
    assert result[0]["item_count"] == 5
    assert result[1]["query"] == "mid"
    assert result[1]["item_count"] == 3
    assert result[2]["query"] == "few"
    assert result[2]["item_count"] == 2


async def test_get_recent_found_items_raises_when_disconnected(
    disconnected_repository,
):
    """RuntimeError when not connected."""
    with pytest.raises(RuntimeError, match="Database connection is not established"):
        await disconnected_repository.get_recent_found_items(
            GetRecentFoundItemsQuery(hours=24)
        )


async def test_get_recent_found_items_raises_on_db_error(mocker, repository):
    """aiosqlite.Error during query is re-raised."""
    mocker.patch.object(
        repository.connection,
        "execute",
        side_effect=aiosqlite.Error("db error"),
    )

    with pytest.raises(aiosqlite.Error, match="db error"):
        await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))


async def test_get_recent_found_items_raises_on_key_error(mocker, repository):
    """KeyError from malformed row is re-raised."""
    mock_cursor = mocker.AsyncMock()
    mock_cursor.fetchall.return_value = [{"bad_key": "value"}]
    mocker.patch.object(
        repository.connection,
        "execute",
        new=mocker.AsyncMock(return_value=mock_cursor),
    )

    with pytest.raises(KeyError):
        await repository.get_recent_found_items(GetRecentFoundItemsQuery(hours=24))
