import asyncio
from open_notebook.database.repository import repo_query

async def main():
    res = await repo_query("SELECT NONE OR '2024-01-01' AS result, [][0] OR 'fallback' AS result2 FROM notebook LIMIT 1;")
    print("res:", res)

asyncio.run(main())
