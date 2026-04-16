import asyncio
from dotenv import load_dotenv

load_dotenv(".env")
from open_notebook.database.repository import repo_query, db_connection

async def add_and_test_index():
    async with db_connection():
        # 1. 尝试直接在现有数据库上创建 description 的倒排索引
        print("1. 正在创建 description 字段的倒排索引...")
        try:
            await repo_query("DEFINE INDEX IF NOT EXISTS idx_kg_entity_desc ON TABLE kg_entity COLUMNS description SEARCH ANALYZER my_analyzer BM25;", {})
            print("=> 索引创建成功！")
        except Exception as e:
            print(f"=> 索引创建失败: {e}")
            return

        # 2. 尝试执行之前会崩溃的联合查询
        print("\n2. 测试联合查询 (name @1@ ... OR description @1@ ...)")
        try:
            test_results = await repo_query("""
                SELECT id, name, description, math::max(search::score(1)) AS relevance
                FROM kg_entity
                WHERE name @1@ 'test' OR description @1@ 'test'
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
