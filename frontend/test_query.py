import asyncio
from open_notebook.database.connection import SurrealConnection

async def main():
    async with SurrealConnection() as db:
        await db.connect()
        result = await db.client.query("""
            SELECT 
                id, 
                title,
                (SELECT VALUE id FROM kg_entity WHERE source_id = type::string($parent.id) LIMIT 1) != [] AS kg_extracted,
                (SELECT VALUE id FROM kg_entity WHERE source_id = $parent.id LIMIT 1) != [] AS kg_extracted_raw
            FROM source
            LIMIT 1;
        """)
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
