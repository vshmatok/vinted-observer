import pytest
from unittest.mock import MagicMock

from src.repository.migrations import MigrationManager


class TestApplyMigrations:

    def test_returns_false_when_dir_not_found(self, tmp_path):
        """Returns False when migrations_dir doesn't exist."""
        manager = MigrationManager(
            database_path=str(tmp_path / "test.db"),
            migrations_dir=str(tmp_path / "nonexistent"),
        )
        assert manager.apply_migrations() is False

    @pytest.mark.usefixtures("patch_read_migrations")
    def test_uses_correct_connection_string(
        self, mocker, migration_manager, mock_backend
    ):
        """get_backend is called with sqlite:///{path}."""
        mock_backend.to_apply.return_value = []
        mock_get_backend = mocker.patch(
            "src.repository.migrations.get_backend", return_value=mock_backend
        )

        migration_manager.apply_migrations()

        expected = f"sqlite:///{migration_manager.database_path}"
        mock_get_backend.assert_called_once_with(expected)

    @pytest.mark.usefixtures("patch_get_backend")
    def test_reads_correct_directory(
        self, mocker, migration_manager, mock_backend, mock_migrations
    ):
        """read_migrations is called with str(migrations_dir)."""
        mock_backend.to_apply.return_value = []
        mock_read = mocker.patch(
            "src.repository.migrations.read_migrations", return_value=mock_migrations
        )

        migration_manager.apply_migrations()

        mock_read.assert_called_once_with(str(migration_manager.migrations_dir))

    @pytest.mark.usefixtures("patch_yoyo")
    def test_with_pending_migrations(
        self, migration_manager, mock_backend, mock_migrations
    ):
        """Returns True and calls backend.apply_migrations when pending migrations exist."""
        to_apply = [MagicMock()]
        mock_backend.to_apply.return_value = to_apply

        result = migration_manager.apply_migrations()

        mock_backend.lock.assert_called_once()
        mock_backend.to_apply.assert_called_once_with(mock_migrations)
        mock_backend.apply_migrations.assert_called_once_with(to_apply)
        assert result is True

    @pytest.mark.usefixtures("patch_yoyo")
    def test_no_pending_migrations(
        self, migration_manager, mock_backend, mock_migrations
    ):
        """Returns True and does NOT call apply_migrations when nothing pending."""
        mock_backend.to_apply.return_value = []

        result = migration_manager.apply_migrations()

        mock_backend.to_apply.assert_called_once_with(mock_migrations)
        mock_backend.apply_migrations.assert_not_called()
        assert result is True

    def test_exception_returns_false(self, mocker, migration_manager):
        """Returns False when an exception occurs."""
        mocker.patch(
            "src.repository.migrations.get_backend",
            side_effect=RuntimeError("backend error"),
        )

        assert migration_manager.apply_migrations() is False

    @pytest.mark.usefixtures("patch_yoyo")
    def test_returns_false_when_apply_raises(self, migration_manager, mock_backend):
        """Returns False when backend.apply_migrations raises inside the lock."""
        mock_backend.to_apply.return_value = [MagicMock()]
        mock_backend.apply_migrations.side_effect = RuntimeError("db locked")

        assert migration_manager.apply_migrations() is False


class TestRollbackMigrations:

    def test_returns_false_when_dir_not_found(self, tmp_path):
        """Returns False when migrations_dir doesn't exist."""
        manager = MigrationManager(
            database_path=str(tmp_path / "test.db"),
            migrations_dir=str(tmp_path / "nonexistent"),
        )
        assert manager.rollback_migrations() is False

    @pytest.mark.usefixtures("patch_read_migrations")
    def test_uses_correct_connection_string(
        self, mocker, migration_manager, mock_backend
    ):
        """get_backend is called with sqlite:///{path}."""
        mock_backend.to_rollback.return_value = []
        mock_get_backend = mocker.patch(
            "src.repository.migrations.get_backend", return_value=mock_backend
        )

        migration_manager.rollback_migrations()

        expected = f"sqlite:///{migration_manager.database_path}"
        mock_get_backend.assert_called_once_with(expected)

    @pytest.mark.usefixtures("patch_get_backend")
    def test_reads_correct_directory(
        self, mocker, migration_manager, mock_backend, mock_migrations
    ):
        """read_migrations is called with str(migrations_dir)."""
        mock_backend.to_rollback.return_value = []
        mock_read = mocker.patch(
            "src.repository.migrations.read_migrations", return_value=mock_migrations
        )

        migration_manager.rollback_migrations()

        mock_read.assert_called_once_with(str(migration_manager.migrations_dir))

    @pytest.mark.usefixtures("patch_yoyo")
    def test_with_migrations(self, migration_manager, mock_backend, mock_migrations):
        """Returns True and calls backend.rollback_migrations when migrations to rollback."""
        to_rollback = [MagicMock()]
        mock_backend.to_rollback.return_value = to_rollback

        result = migration_manager.rollback_migrations()

        assert result is True
        mock_backend.lock.assert_called_once()
        mock_backend.to_rollback.assert_called_once_with(mock_migrations, 1)
        mock_backend.rollback_migrations.assert_called_once_with(to_rollback)

    @pytest.mark.usefixtures("patch_yoyo")
    def test_no_migrations(self, migration_manager, mock_backend):
        """Returns True and does NOT call rollback_migrations when nothing to rollback."""
        mock_backend.to_rollback.return_value = []

        result = migration_manager.rollback_migrations()

        assert result is True
        mock_backend.rollback_migrations.assert_not_called()

    @pytest.mark.usefixtures("patch_yoyo")
    def test_default_count(self, migration_manager, mock_backend, mock_migrations):
        """to_rollback is called with count=1 by default."""
        mock_backend.to_rollback.return_value = []

        migration_manager.rollback_migrations()

        mock_backend.to_rollback.assert_called_once_with(mock_migrations, 1)

    @pytest.mark.parametrize("count", [2, 3, 5])
    @pytest.mark.usefixtures("patch_yoyo")
    def test_custom_count(
        self, migration_manager, mock_backend, mock_migrations, count
    ):
        """to_rollback is called with the correct custom count."""
        mock_backend.to_rollback.return_value = []

        migration_manager.rollback_migrations(count=count)

        mock_backend.to_rollback.assert_called_once_with(mock_migrations, count)

    def test_exception_returns_false(self, mocker, migration_manager):
        """Returns False when an exception occurs."""
        mocker.patch(
            "src.repository.migrations.get_backend",
            side_effect=RuntimeError("backend error"),
        )

        assert migration_manager.rollback_migrations() is False

    @pytest.mark.usefixtures("patch_yoyo")
    def test_returns_false_when_rollback_raises(self, migration_manager, mock_backend):
        """Returns False when backend.rollback_migrations raises inside the lock."""
        mock_backend.to_rollback.return_value = [MagicMock()]
        mock_backend.rollback_migrations.side_effect = RuntimeError("db locked")

        assert migration_manager.rollback_migrations() is False
