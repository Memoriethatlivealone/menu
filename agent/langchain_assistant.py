from langchain.tools import tool
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import URL
import logging

logger = logging.getLogger(__name__)

root_path = Path(__file__).resolve().parent.parent
load_dotenv(root_path / ".env")
embeddings = None
milvus_client = None
engine = None
agent = None
model_http_client = None
model_async_http_client = None


class AssistantConfigurationError(RuntimeError):
    pass

None
def create_chat_model():
    import ssl
    import certifi
    from openai import DefaultHttpxClient, DefaultAsyncHttpxClient
    from langchain_openai import ChatOpenAI

    global model_http_client, model_async_http_client
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key or not base_url:
        raise AssistantConfigurationError("请在项目根目录 .env 配置 OPENAI_API_KEY 和 OPENAI_BASE_URL，然后重启后端。")

    # Explicit CA roots avoid the Windows truststore crash without disabling TLS verification.
    context = ssl.create_default_context(cafile=certifi.where())
    if model_http_client is None:
        model_http_client = DefaultHttpxClient(verify=context, timeout=30)
    if model_async_http_client is None:
        model_async_http_client = DefaultAsyncHttpxClient(verify=context, timeout=30)
    from urllib.parse import urlsplit

    model_options = {}
    if urlsplit(base_url).hostname == "api.deepseek.com":
        # This generic tool loop does not replay DeepSeek reasoning_content.
        model_options["extra_body"] = {"thinking": {"type": "disabled"}}
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL") or "deepseek-flash",
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        timeout=30,
        max_retries=1,
        http_socket_options=(),
        http_client=model_http_client,
        http_async_client=model_async_http_client,
        **model_options,
    )


async def close_model_clients():
    global model_http_client, model_async_http_client, agent
    agent = None
    if model_async_http_client is not None:
        await model_async_http_client.aclose()
        model_async_http_client = None
    if model_http_client is not None:
        model_http_client.close()
        model_http_client = None


def assistant_error_message(exc):
    from openai import APIConnectionError, APITimeoutError, APIStatusError

    if isinstance(exc, AssistantConfigurationError):
        return "聊天配置不完整，请在项目根目录 .env 配置 OPENAI_API_KEY 和 OPENAI_BASE_URL，然后重启后端。"
    if isinstance(exc, APITimeoutError):
        return "模型服务响应超时，请稍后重试或检查网络连接。"
    if isinstance(exc, APIConnectionError):
        return "无法连接模型服务，请检查 OPENAI_BASE_URL、网络代理和 HTTPS 证书配置。"
    if isinstance(exc, APIStatusError):
        if exc.status_code in (401, 403):
            return "模型服务鉴权失败或无访问权限，请检查 OPENAI_API_KEY 和账号权限。"
        if exc.status_code == 429:
            return "模型服务限流或额度不足，请检查账号额度后重试。"
        if exc.status_code in (400, 404):
            return "模型服务不支持当前请求，请检查 OPENAI_MODEL、OPENAI_BASE_URL 及工具调用支持情况。"
        return "模型服务返回异常，请稍后重试并查看后端日志。"
    return "助手处理失败，请查看后端日志中的具体原因。"


def get_embeddings():
    global embeddings
    if embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        model_path = root_path / "models" / "bge-m3"
        if not model_path.is_dir():
            raise RuntimeError(f"口味检索模型不存在：{model_path}，请先配置 models/bge-m3")
        embeddings = HuggingFaceEmbeddings(model_name=str(model_path))
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

        url = URL.create(
            "mysql+pymysql",
            username=os.getenv("MYSQL_USERNAME"),
            password=os.getenv("MYSQL_PASSWORD"),
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE"),
        )
        engine = create_engine(url, pool_size=15, pool_pre_ping=True)
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
        from sqlalchemy import inspect

        engine = mysql_connection()
        columns = {column["name"] for column in inspect(engine).get_columns("menu_items")}
        featured_filter = "is_featured = 1 AND " if "is_featured" in columns else ""
        with engine.connect() as conn:
            results = conn.execute(text(f"""
                SELECT dish_name, price, description, category, spice_level,
                       flavor, main_ingredients, cooking_method, is_vegetarian, allergens
                FROM menu_items
                WHERE {featured_filter}is_available = 1
            """)).mappings().all()
        return [
            {label: str(item[key]) if item[key] is not None else ""
             for key, label in key_name_mapping.items()}
            for item in results
        ]
    except Exception:
        logger.exception("查询特色菜失败")
        return "查询菜品时发生错误，请检查数据库连接及菜单表结构。"


def load_available_menu():
    """向量服务不可用时，提供实际在售菜单供助手按口味筛选。"""
    try:
        with mysql_connection().connect() as conn:
            results = conn.execute(text("""
                SELECT id, dish_name, price, description, category, spice_level,
                       flavor, main_ingredients, cooking_method, is_vegetarian, allergens
                FROM menu_items
                WHERE is_available = 1
                ORDER BY category, dish_name
            """)).mappings().all()
        items = [{**dict(item), "price": str(item["price"])} for item in results]
        return {
            "source": "mysql",
            "instruction": "这是当前在售菜单，请根据用户需求筛选；spice_level=0 表示不辣，不要捏造菜品或价格。",
            "menu_items": items,
            "message": "success" if items else "当前暂无在售菜品。",
        }
    except Exception:
        logger.exception("查询在售菜单失败")
        return {"source": "mysql", "menu_items": [], "error": "菜单数据库暂不可用，请检查数据库连接。"}


@tool
def user_flavor_search(user_query: str):
    """查询菜单或按口味推荐菜品；优先向量检索，未配置或失败时读取 MySQL 在售菜单。"""
    uri = os.getenv("MILVUS_URI") or ""
    vector_configured = (
        (root_path / "models" / "bge-m3").is_dir()
        and bool(uri)
        and "{" not in uri
        and "}" not in uri
    )
    if vector_configured:
        try:
            query_vector = get_embeddings().embed_query(user_query)
            search_res = get_milvus_client().search(
                collection_name="menu_items",
                data=[query_vector],
                anns_field="vector",
                output_fields=["text"],
                limit=5,
                timeout=5,
            )
            if search_res and search_res[0]:
                return {"source": "milvus", "results": [item["entity"]["text"] for item in search_res[0]]}
        except Exception:
            logger.warning("向量检索不可用，改用 MySQL 菜单", exc_info=True)
    return load_available_menu()


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

        error_payload = {"type": "error", "error": assistant_error_message(exc)}
        logger.exception("assistant stream failed")
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"


async def create_agent():
    global agent
    if agent is None:
        from langgraph.prebuilt import create_react_agent
        from langgraph.checkpoint.memory import MemorySaver

        llm = create_chat_model()
        with open(root_path / "agent" / "prompts" / "system_prompt.txt", encoding="utf-8") as f:
            system_prompt = f.read()

        tools = [search_main_dishes, user_flavor_search, make_reservation]
        mcp_url = os.getenv("AMAP_MCP_URL")
        if mcp_url:
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient

                client = MultiServerMCPClient(
                    connections={"amap_map": {"transport": "sse", "url": mcp_url}}
                )
                import asyncio

                tools += await asyncio.wait_for(client.get_tools(), timeout=5)
            except Exception:
                logger.warning("地图 MCP 不可用，继续使用本地工具", exc_info=True)

        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            checkpointer=MemorySaver(),
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
