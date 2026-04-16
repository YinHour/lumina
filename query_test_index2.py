import asyncio
from dotenv import load_dotenv

load_dotenv(".env")
from open_notebook.database.repository import repo_query, db_connection

async def add_and_test_index():
    async with db_connection():
        # 尝试执行正确的多字段联合查询 (使用不同的 match reference id)
        print("测试正确的联合查询 (name @1@ ... OR description @2@ ...)")
        try:
            test_results = await repo_query("""
                SELECT id, name, description, math::max([search::score(1), search::score(2)]) AS relevance
                FROM kg_entity
                WHERE name @1@ 'test' OR description @2@ 'test'
                ORDER BY relevance DESC
                LIMIT 1
            """, {})
            print("=> 查询成功执行，没有崩溃！")
            if test_results:
                print(f"找到匹配结果: {test_results[0].get('name')}")
            else:
                print("没有找到匹配 'test' 的数据，但语法验证通过。")
        except Exception as e:
            print(f"=> 查询依然失败: {e}")

if __name__ == "__main__":
    asyncio.run(add_and_test_index())
