from dotenv import load_dotenv

load_dotenv()
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

# 1.初始化模型
model = init_chat_model(
    model="qwen3.7-plus",
    model_provider="openai",
    extra_body={"thinking": {"type": "disabled"}},  # 控制不要思考
)

# 2.初始化agent
agent = create_agent(
    model=model, tools=[], system_prompt="你是apple公司工作人员。"
)
# 3.streaming模式下调用agent
stream = agent.stream_events(
    {"messages": [HumanMessage(content="你们性能最强大的产品是什么目前")]},
    version="v3",
)

for message in stream.messages:
    for token in message.text:
        print(token, end="", flush=True)
