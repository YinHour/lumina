import asyncio
from dotenv import load_dotenv
load_dotenv()
from open_notebook.database.repository import repo_query
import json

async def main():
    await repo_query("""
    CREATE notebook:X SET name="X";
    CREATE notebook:Y SET name="Y";
    RELATE notebook:X->aggregates->notebook:Y;
    """)
    res = await repo_query("""SELECT in, out FROM aggregates WHERE in = notebook:X;""")
    print("X->aggregates->Y:", json.dumps(res, indent=2))
    await repo_query("""DELETE notebook:X; DELETE notebook:Y;""")

if __name__ == "__main__":
    asyncio.run(main())