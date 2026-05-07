import asyncio
from surrealdb import Surreal

async def main():
    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("open_notebook", "open_notebook")
        res = await db.query("RELATE person:1->likes->person:2;")
        print("RELATE result:", res)
        edge = await db.query("SELECT * FROM likes;")
        print("Edge:", edge)

asyncio.run(main())
