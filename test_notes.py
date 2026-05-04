import asyncio
from dotenv import load_dotenv
load_dotenv()
from open_notebook.database.repository import repo_query
import json
from open_notebook.domain.notebook import Notebook

async def main():
    await repo_query("""
    CREATE notebook:X SET name="X";
    CREATE notebook:Y SET name="Y";
    RELATE notebook:X->aggregates->notebook:Y;
    CREATE source:S1;
    RELATE source:S1->reference->notebook:Y;
    """)
    res = await repo_query("""
    select in as source from reference where out=notebook:X OR out in (SELECT VALUE out FROM aggregates WHERE in = notebook:X)
    """)
    print("Query result:", json.dumps(res, indent=2))
    
    await repo_query("DELETE notebook:X; DELETE notebook:Y; DELETE source:S1;")

if __name__ == "__main__":
    asyncio.run(main())