import asyncio
from dotenv import load_dotenv

load_dotenv(".env")
from open_notebook.database.repository import repo_query, db_connection

async def patch():
    async with db_connection():
        await repo_query("DELETE open_notebook:content_settings", {})
        print("已清理数据库中缓存的旧设置。")

if __name__ == "__main__":
    asyncio.run(patch())
