from open_notebook.database.async_migrate import AsyncMigrationManager


def test_async_migration_manager_includes_migration_17():
    manager = AsyncMigrationManager()

    assert len(manager.up_migrations) >= 17
    assert len(manager.down_migrations) >= 17
