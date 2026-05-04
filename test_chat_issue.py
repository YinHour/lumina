import asyncio
from dotenv import load_dotenv
load_dotenv()
from open_notebook.database.repository import repo_query
import json

async def main():
    await repo_query("""
    CREATE notebook:orig SET name="Original";
    CREATE notebook:agg SET name="Aggregated", is_aggregated=true;
    RELATE notebook:agg->aggregates->notebook:orig;
    
    CREATE chat_session:orig_chat SET title="Orig Chat";
    RELATE chat_session:orig_chat->refers_to->notebook:orig;
    
    CREATE chat_session:agg_chat SET title="Agg Chat";
    RELATE chat_session:agg_chat->refers_to->notebook:agg;
    """)
    
    res_orig = await repo_query("""
        select * from (
            select
            <- chat_session as chat_session
            from refers_to
            where out=notebook:orig OR out in (SELECT VALUE out FROM aggregates WHERE in = notebook:orig)
            fetch chat_session
        )
    """)
    print("Orig chats:", json.dumps(res_orig, indent=2))
    
    res_agg = await repo_query("""
        select * from (
            select
            <- chat_session as chat_session
            from refers_to
            where out=notebook:agg OR out in (SELECT VALUE out FROM aggregates WHERE in = notebook:agg)
            fetch chat_session
        )
    """)
    print("Agg chats:", json.dumps(res_agg, indent=2))
    
    await repo_query("DELETE notebook:orig; DELETE notebook:agg; DELETE chat_session:orig_chat; DELETE chat_session:agg_chat;")

if __name__ == "__main__":
    asyncio.run(main())