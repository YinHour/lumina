import asyncio
from dotenv import load_dotenv
load_dotenv()

from open_notebook.database.repository import repo_query

async def main():
    print("Checking DB directly:")
    result = await repo_query("SELECT * FROM open_notebook:content_settings")
    print(result)

asyncio.run(main())
