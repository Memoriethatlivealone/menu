from langchain.tools import tool
import pymysql
import os
from dotenv import load_dotenv
from pathlib import Path
from pymysql.cursors import DictCursor
from sqlalchemy import text

load_dotenv()
root_path = Path(__file__).parent.parent
embeddings = None
milvus_client = None
engine = None
agent = None


def get_embeddings():
    global embeddings
    if embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model=str(root_path / "models" / "bge-m3"))
    return embeddings


def get_milvus_client():
    global milvus_client
    if milvus_client is None:
        from pymilvus import MilvusClient

        milvus_client = MilvusClient(
            uri=os.getenv("MILVUS_URI"), token=os.getenv("MILVUS_TOKEN")
        )
    return milvus_client


def mysql_connection():
    global engine
    if engine is None:
        from sqlalchemy import create_engine

        engine = create_engine(
            url=f"mysql+pymysql://{os.getenv('MYSQL_USERNAME')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}",
            pool_size=15,
        )
    return engine


# 工具 用来搜索餐厅中的主材
@tool
def search_main_dishes():
    """
    搜索餐厅中的特色菜品
    从数据库中查询所有特色菜品（is_featured=1）的详细信息，包括菜名、价格、描述、分类等
    返回格式化后的菜品列表
    """
    key_name_mapping = {
        "dish_name": "主菜名称",
        "price": "价格",
        "description": "描述",
        "category": "分类",
        "spice_level": " 辣度等级",
        "flavor": "口味",
        "main_ingredients": "主要食材",
        "cooking_method": "烹饪方法",
        "is_vegetarian": "是否为素食",
        "allergens": "过敏信息",
    }
    try:
        with pymysql.connect(
            host=os.getenv("MYSQL_BASE_HOST"),
            user=os.getenv("MYSQL_BASE_USER"),
            password=os.getenv("MYSQL_BASE_PASSWORD"),
            port=int(os.getenv("MYSQL_BASE_PORT")),
            database="menu",
        ) as conn:
            with conn.cursor(DictCursor) as cursor:
                sql = """
                    select
                        dish_name,
                        price,
                        description,
                        category,
                        spice_level,
                        flavor,
                        main_ingredients,
                        cooking_method,
                        is_vegetarian,
                        allergens
                    from
                        menu_items
                    where
                        is_featured=1
                """
                cursor.execute(sql)
                results = cursor.fetchall()
                # 定义json的键，将数据封装成json

                json_results = []
                for item in results:
                    json_item = {}
                    for key, value in item.items():
                        json_item[key_name_mapping[key]] = value
                    json_results.append(json_item)

                return json_results
    except Exception as e:
        return f"查询菜品时发生错误: {str(e)}"


@tool
def user_flavor_search(user_query: str):
    """
    基于用户的口味，来去查找相关的菜品
    使用向量搜索在Milvus数据库中查找与用户口味描述最匹配的菜品
    """
    try:
        # 1、构建用户query的向量
        embeddings = get_embeddings()
        query_vector = embeddings.embed_query(user_query)

        # 2、连接milvus，进行向量搜索
        client = get_milvus_client()

        # 3、进行向量搜索
        search_res = client.search(
            collection_name="menu_items",
            data=[query_vector],
            anns_field="vector",
            output_fields=["text"],
            limit=1,
        )
        print("当前查找结果为：", search_res)
        # 4、解析搜索结果
        if search_res:
            all_results = search_res[0]
            # all_results: 列表
            final_result = []

            for item in all_results:
                item_str = item["entity"]["text"]
                final_result.append(item_str)

            return final_result
        else:
            return "在当前库里面没有找到和用户喜好相关的菜品"
    except Exception as e:
        return f"搜索菜品时发生错误: {str(e)}"


from pydantic import BaseModel, Field


class ReservationToolArgsInfo(BaseModel):
    num_people: int = Field(description="预约的总人数")
    num_children: int = Field(description="预约的0-2岁儿童人数")
    arrival_time: str = Field(description="预约的到达时间,格式：YYYY-MM-DD HH")
    seat_preference: str = Field(
        description="预约的座位偏好，当用户没有特殊需求时，传递空字符串即可"
    )
    main_dish_preference: str = Field(
        description="预约的主菜偏好，当用户没有特殊需求时，传递空字符串即可"
    )
    comment: str = Field(
        description="预约的其他备注，当用户没有特殊需求时，传递空字符串即可"
    )


@tool(args_schema=ReservationToolArgsInfo)
def make_reservation(
    num_people: int,
    num_children: int,
    arrival_time: str,
    seat_preference: str,
    main_dish_preference: str,
    comment: str,
):
    """
    用来进行餐厅预定的工具：
    通过MySQL向数据库当中写入数据
    """
    try:
        engine = mysql_connection()
        with engine.connect() as conn:
            sql = """
INSERT INTO reservation_order
(num_people, num_children, arrival_time, seat_preference, main_dish_preference, other_comments)
VALUES
(:num_people, :num_children, :arrival_time, :seat_preference, :main_dish_preference, :other_comments)
"""
            params = {
                "num_people": num_people,
                "num_children": num_children,
                "arrival_time": arrival_time,
                "seat_preference": seat_preference,
                "main_dish_preference": main_dish_preference,
                "other_comments": comment,
            }
            conn.execute(statement=text(sql), parameters=params)
            conn.commit()

            return "预订成功"
    except Exception as e:
        return f"预订失败: {str(e)}"


async def assistant_query(user_query: str):
    """接收前端查询，并以 SSE 形式转发智能助手的流式输出。"""
    from datetime import datetime
    from langchain_core.messages import ToolMessage

    try:
        assistant = await create_agent()
        current_date = datetime.now().strftime("%Y-%m-%d")
        day_of_week = datetime.now().weekday() + 1
        time_system_prompt = {
            "role": "system",
            "content": f"当前日期为：{current_date}，当前是周{day_of_week}",
        }
        config = {"configurable": {"thread_id": 123}}

        async for chunk in assistant.astream(
            {"messages": [time_system_prompt, {"role": "user", "content": user_query}]},
            config=config,
            stream_mode="messages",
        ):
            message = chunk[0]
            if isinstance(message, ToolMessage):
                continue

            content = message.content
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            if not isinstance(content, str) or not content:
                continue

            import json

            yield f"data: {json.dumps({'content': content, 'type': 'token'}, ensure_ascii=False)}\n\n"
    except Exception as exc:
        import json

        error_payload = {"type": "error", "error": "助手暂时无法响应，请稍后重试。"}
        print(f"assistant stream failed: {exc}")
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"


async def create_agent():
    global agent
    if agent is None:
        from pathlib import Path
        from langgraph.prebuilt import create_react_agent
        from langchain_openai import ChatOpenAI
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

        client = MultiServerMCPClient(
            connections={
                "amap_map": {
                    "transport": "sse",
                    "url": "https://mcp.api-inference.modelscope.net/ccaef2a2308042/sse",
                }
            }
        )

        # OpenAI-compatible provider configuration must be explicit so the
        # service does not accidentally use a different shell environment.
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key or not base_url:
            raise RuntimeError("OPENAI_API_KEY and OPENAI_BASE_URL must be configured")

        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "qwen-plus"),
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
        )
        with open(
            str(root_path / "agent" / "prompts" / "system_prompt.txt"),
            encoding="utf-8",
            mode="r",
        ) as f:
            system_prompt = f.read()
        mcp_tools = await client.get_tools()
        agent = create_react_agent(
            model=llm,
            tools=[search_main_dishes, user_flavor_search, make_reservation]
            + mcp_tools,
            prompt=system_prompt,
            checkpointer=checkpointer,
        )
    return agent


async def test_agent():
    agent = await create_agent()
    config = {"configurable": {"thread_id": "123"}}
    res = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "你能为我做什么？"}]}, config=config
    )

    print(res["messages"][-1].content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_agent())
