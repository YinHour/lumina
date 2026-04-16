import asyncio
from dotenv import load_dotenv
load_dotenv()
from open_notebook.domain.content_settings import ContentSettings

async def main():
    print("Initial:")
    s = await ContentSettings.get_instance()
    print("DB key:", s.tavily_api_key)
    
    print("Updating to 'new_key'...")
    s.tavily_api_key = "new_key"
    await s.update()
    
    print("After update:")
    s2 = await ContentSettings.get_instance()
    print("DB key:", s2.tavily_api_key)

asyncio.run(main())
