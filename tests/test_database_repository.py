import pytest
import pytest_asyncio

from open_notebook.database import repository


class FakeSurreal:
    instances = []

    def __init__(self, url):
        self.url = url
        self.closed = False
        self.signin_payload = None
        self.namespace = None
        self.database = None
        FakeSurreal.instances.append(self)

    async def signin(self, payload):
        self.signin_payload = payload

    async def use(self, namespace, database):
        self.namespace = namespace
        self.database = database

    async def close(self):
        self.closed = True


@pytest_asyncio.fixture(autouse=True)
async def clean_database_pool():
    await repository.close_database_pool()
    FakeSurreal.instances = []
    yield
    await repository.close_database_pool()


def set_pool_env(monkeypatch, *, size="2", acquire_timeout="0.05"):
    monkeypatch.setenv("SURREAL_POOL_SIZE", size)
    monkeypatch.setenv("SURREAL_POOL_ACQUIRE_TIMEOUT", acquire_timeout)
    monkeypatch.setenv("SURREAL_QUERY_TIMEOUT", "0")
    monkeypatch.setenv("SURREAL_URL", "ws://db:8000/rpc")
    monkeypatch.setenv("SURREAL_USER", "root")
    monkeypatch.setenv("SURREAL_PASSWORD", "root")
    monkeypatch.setenv("SURREAL_NAMESPACE", "open_notebook")
    monkeypatch.setenv("SURREAL_DATABASE", "open_notebook")


def test_get_database_url_falls_back_to_legacy_address_and_port(monkeypatch):
    monkeypatch.delenv("SURREAL_URL", raising=False)
    monkeypatch.setenv("SURREAL_ADDRESS", "127.0.0.1")
    monkeypatch.setenv("SURREAL_PORT", "8000")

    assert repository.get_database_url() == "ws://127.0.0.1:8000/rpc"


@pytest.mark.asyncio
async def test_connection_pool_prewarms_and_reuses_connections(monkeypatch):
    set_pool_env(monkeypatch, size="2")
    monkeypatch.setattr(repository, "AsyncSurreal", FakeSurreal)

    await repository.initialize_database_pool()

    assert len(FakeSurreal.instances) == 2
    assert FakeSurreal.instances[0].signin_payload == {
        "username": "root",
        "password": "root",
    }
    assert FakeSurreal.instances[0].namespace == "open_notebook"
    assert FakeSurreal.instances[0].database == "open_notebook"

    async with repository.db_connection() as first:
        async with repository.db_connection() as second:
            assert first is not second

    assert not any(instance.closed for instance in FakeSurreal.instances)


@pytest.mark.asyncio
async def test_connection_pool_times_out_when_exhausted(monkeypatch):
    set_pool_env(monkeypatch, size="1", acquire_timeout="0.01")
    monkeypatch.setattr(repository, "AsyncSurreal", FakeSurreal)

    async with repository.db_connection():
        with pytest.raises(RuntimeError, match="Timed out waiting"):
            async with repository.db_connection():
                pass


@pytest.mark.asyncio
async def test_close_database_pool_closes_all_connections(monkeypatch):
    set_pool_env(monkeypatch, size="3")
    monkeypatch.setattr(repository, "AsyncSurreal", FakeSurreal)

    await repository.initialize_database_pool()
    await repository.close_database_pool()

    assert len(FakeSurreal.instances) == 3
    assert all(instance.closed for instance in FakeSurreal.instances)


@pytest.mark.asyncio
async def test_repo_transaction_retries_transaction_conflicts(monkeypatch):
    calls = 0
    delays = []

    async def fake_repo_query(query, vars=None):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("There was a datastore transaction conflict")
        return [{"ok": True}]

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setenv("SURREAL_TRANSACTION_RETRY_ATTEMPTS", "3")
    monkeypatch.setattr(repository, "repo_query", fake_repo_query)
    monkeypatch.setattr(repository.asyncio, "sleep", fake_sleep)

    result = await repository.repo_transaction("CREATE source SET title = 'x';")

    assert result == [{"ok": True}]
    assert calls == 3
    assert len(delays) == 2


@pytest.mark.asyncio
async def test_repo_transaction_stops_after_retry_limit(monkeypatch):
    calls = 0

    async def fake_repo_query(query, vars=None):
        nonlocal calls
        calls += 1
        raise RuntimeError("write-write conflict")

    async def fake_sleep(delay):
        return None

    monkeypatch.setenv("SURREAL_TRANSACTION_RETRY_ATTEMPTS", "2")
    monkeypatch.setattr(repository, "repo_query", fake_repo_query)
    monkeypatch.setattr(repository.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="write-write conflict"):
        await repository.repo_transaction("DELETE source;")

    assert calls == 2
