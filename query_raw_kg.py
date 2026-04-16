import asyncio
from dotenv import load_dotenv

load_dotenv(".env")
from open_notebook.database.repository import repo_query, db_connection

async def get_raw_graph():
    async with db_connection():
        raw_relation = await repo_query("""
            SELECT * FROM kg_relation LIMIT 1
        """, {})
        # 简单打印字典即可，不需要转 JSON，避免 datetime 报错
        for r in raw_relation:
            print(f"id: {r.get('id')}")
            print(f"in: {r.get('in')}")
            print(f"out: {r.get('out')}")
            print(f"type: {r.get('type')}")
            print(f"description: {r.get('description')}")
            print("---")

if __name__ == "__main__":
    asyncio.run(get_raw_graph())
