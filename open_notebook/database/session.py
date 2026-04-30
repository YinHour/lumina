from contextlib import asynccontextmanager
from typing import AsyncIterator

from surrealdb import AsyncSurreal

from open_notebook.database.repository import db_connection


@asynccontextmanager
async def database_session() -> AsyncIterator[AsyncSurreal]:
    """Yield a configured SurrealDB connection.

    This is a named session entrypoint for new repository code. It currently
    delegates to the existing connection helper so older call sites keep their
    behavior while repositories migrate behind this boundary.
    """
    async with db_connection() as connection:
        yield connection

