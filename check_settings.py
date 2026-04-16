from dotenv import load_dotenv
load_dotenv()
import asyncio
import os
from open_notebook.database.repository import repo_query, repo_update
from open_notebook.domain.content_settings import ContentSettings

async def main():
    ContentSettings.clear_instance()
    settings = await ContentSettings.get_instance()
    print("Old Database values:")
    print(f"default_content_processing_engine_doc: {settings.default_content_processing_engine_doc}")
    
    settings.default_content_processing_engine_doc = "mineru"
    await settings.update()
    
    ContentSettings.clear_instance()
    settings = await ContentSettings.get_instance()
    print("New Database values:")
    print(f"default_content_processing_engine_doc: {settings.default_content_processing_engine_doc}")

if __name__ == "__main__":
    asyncio.run(main())