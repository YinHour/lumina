import asyncio
import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env")

# 必须先加载环境变量再导入数据库连接
from open_notebook.database.repository import repo_query, db_connection

async def get_sample_graph():
    async with db_connection():
        # 抽取 1 条有关系的实体边
        relations = await repo_query("""
            SELECT 
                id,
                in.name AS source_name,
                in.type AS source_type,
                type AS relation_type,
                description AS relation_desc,
                out.name AS target_name,
                out.type AS target_type
            FROM kg_relation
            LIMIT 1
        """, {})
        
        # 抽取一个包含 description 的实体
        entity_with_desc = await repo_query("""
            SELECT id, name, type, description 
            FROM kg_entity 
            WHERE description != None 
            LIMIT 1
        """, {})

        print("=== 关系 (Relation) 示例 ===")
        print(json.dumps(relations, indent=2, ensure_ascii=False) if relations else "没有找到关系数据")
        
        print("\n=== 带描述的实体 (Entity) 示例 ===")
        print(json.dumps(entity_with_desc, indent=2, ensure_ascii=False) if entity_with_desc else "没有找到实体数据")

if __name__ == "__main__":
    asyncio.run(get_sample_graph())
