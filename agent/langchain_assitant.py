"""
用来定义agent的主要代码
"""
from langchain.tools import tool
@tool
def search_featured_dishes(query: str) -> str:
    """
        搜索工具函数
    查找当前餐厅当中的特色主打主菜，不包含所有菜系，仅包含特色主菜
    return :
    dict:
    id->主菜的ID
    dish_name->主菜的名称
    flavor->主菜的口味
    price->主菜的价格
    category->主菜的分类
    description->主菜的描述

    """

    # 这里可以实现搜索逻辑，比如调用搜索引擎API
    return f"搜索结果: {query}"


async def create_agent():
    """
    创建agent的函数
    """
    from pathlib import Path

    root_path = Path(__file__).parent.parent
    from agent.langchain_assitant import LangChainAssistant
    from agent.langchain_assitant import LangChainAgent
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI()
    with open(
        root_path / "agent" / "prompts" / "system_prompt.txt", "r", encoding="utf-8"
    ) as f:
        system_prompt = f.read()

    agent = create_agent(model=llm, system_prompt=system_prompt)
    # 创建LangChainAssistant实例

    assistant = LangChainAssistant()

    # 创建LangChainAgent实例，并传入assistant
    agent = LangChainAgent(assistant)

    return agent
