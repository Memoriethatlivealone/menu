# AiMenu 智能点餐系统

AiMenu 是一个用于学习「LLM Agent + 餐厅业务工具 + Web 前后端」的智能点餐项目。前端使用 Vue 3 与 Element Plus，是带真实菜品图片、分类导航、搜索、购物车和本地订单记录的完整点餐界面；后端使用 FastAPI 提供 HTTP/SSE 接口；智能助手通过 LangGraph Agent（默认模型 `deepseek-flash`，可经 `OPENAI_MODEL` 更换）接收用户意图，并在需要时调用 MySQL、Milvus、地图 MCP 等工具。Redis 用于 FAQ 推荐，MySQL 保存菜单和预订数据。仓库另附 `study/` 目录，提供 Agent 学习指南网页与详细教程 PDF。

本文档同时作为项目导览：说明已跟踪文件的用途、主要调用关系、环境准备、启动步骤，以及建议的循序学习路径。文档以当前仓库代码为准；其中有些前端预留功能尚未由后端实现，会明确标注。

## 项目当前能力与边界

### 已实现的主要能力

- **工具型餐厅 Agent**：`agent/langchain_assistant.py` 使用 LangGraph 的 `create_react_agent` 创建 Agent。Agent 根据系统提示词和用户意图决定是否调用工具，而不只是将消息直接转发给模型。
- **Agent 工具**：查询特色菜、按口味进行 Milvus 向量检索、创建餐厅预订，以及连接配置好的地图 MCP 工具。
- **流式对话**：后端 `/chat` 以 SSE 返回文本片段，前端逐段显示回答。
- **菜单与预订查询**：后端通过 MySQL 查询在售菜品和预订记录。
- **FAQ 推荐**：后端从 Redis 读取 FAQ，并用 `SequenceMatcher` 与 Jaccard 字符集合相似度对问题排序。
- **前端页面**：新版完整点餐界面——顶部品牌栏（菜品搜索、我的订单/我的预订/AI 助手入口）、左侧常驻 AI 对话面板（快捷提问、FAQ 联想、流式回答、推荐菜高亮）、右侧分类导航与菜品卡片（真实图片、辣度/素食/分类标签）、底部购物车结算栏及订单/预订抽屉。

### 当前未完成或需要注意的部分

- 前端 API 模块声明了 `POST /delivery`，但 `api/main.py` 没有配送路由；`app.vue` 中的 `checkDelivery()` 也没有接入任何模板入口，因此配送查询暂不可用。
- 购物车下单只是**前端演示闭环**：确认订单后生成订单号并保存到浏览器 localStorage（key 为 `aimenu_orders`），可在「我的订单」抽屉查看历史；后端没有订单接口，订单不会写入 MySQL，换浏览器或清缓存即丢失。
- `/health` 只返回服务存活信息，不检查 MySQL、Redis、模型 API、Milvus 或 MCP 是否可用。
- Agent 是按需初始化的；未配置模型 API 时，聊天请求会失败，但菜单等不需要 Agent 的接口仍可单独运行（前提是数据库已配置）。
- `agent/milvus_data_sync.py` 在模块加载时会直接调用同步函数，并先删除 `menu_items` collection。不要把它当作无副作用的普通导入操作；执行前确认连接目标和数据备份。
- `agent/redis_demo.py` 导入时会执行 Redis 示例写入；不要在不需要演示时直接导入该模块。

## 技术栈与请求流程

| 层次 | 技术 | 主要位置 |
| --- | --- | --- |
| 浏览器 UI | Vue 3、Element Plus | `ui/src/app.vue`、`ui/src/main.js` |
| 前端 API 与代理 | Axios、Fetch、Vite | `ui/src/api/index.js`、`ui/vite.config.js` |
| HTTP 服务 | FastAPI、Starlette StreamingResponse | `api/main.py` |
| Agent 编排 | LangChain、LangGraph | `agent/langchain_assistant.py` |
| 结构化数据 | MySQL、SQLAlchemy、PyMySQL | `api/main.py`、`agent/langchain_assistant.py` |
| FAQ | Redis | `api/main.py`、`agent/redis_data_sync.py` |
| 向量检索 | Milvus、HuggingFace Embeddings、`bge-m3` | `agent/langchain_assistant.py`、`agent/milvus_data_sync.py` |
| 外部工具 | LangChain MCP Adapters、地图 MCP | `agent/langchain_assistant.py` |
| Python 项目管理 | Python 3.12+、uv | `pyproject.toml`、`uv.lock` |

聊天主要调用链：

```text
ui/src/app.vue
  └─ chatAPI.sendStreamMessage()                 ui/src/api/index.js
      └─ POST /api/chat                           Vite 代理移除 /api
          └─ POST /chat                           api/main.py
              └─ assistant_query()                agent/langchain_assistant.py
                  └─ create_agent()               LangGraph Agent
                      ├─ LLM：OpenAI 兼容 API
                      ├─ 工具：MySQL / Milvus
                      └─ 工具：地图 MCP
                  └─ SSE data: JSON 事件流返回前端
```

FAQ、菜单和预订信息是单独的 HTTP 请求，不需要经过 Agent：

```text
Vue 页面 → ui/src/api/index.js → Vite /api 代理 → FastAPI 路由
                                             ├─ Redis：FAQ
                                             └─ MySQL：菜单、预订列表
```

## 项目文件导览

以下清单逐一介绍 Git 跟踪的项目文件。`node_modules`、`.venv`、构建产物等被忽略的依赖或生成文件不属于源代码清单。

### 仓库根目录

| 文件 | 作用与阅读提示 |
| --- | --- |
| `README.md` | 本文档。项目总览、文件索引、配置和学习路径的入口。建议先读“请求流程”和“学习路径”，再按模块阅读源文件。 |
| `.gitignore` | Git 忽略规则，包括 Python 字节码、虚拟环境、`.env`、Node 依赖、构建输出和 `menu.sql`。密钥文件不应提交。 |
| `.python-version` | 指定项目 Python 版本为 `3.12`，供 pyenv 等版本管理工具识别；`pyproject.toml` 也声明 Python `>=3.12`。 |
| `pyproject.toml` | Python 项目元数据、Python 版本范围、运行依赖、`uv_build` 构建配置，以及 `menu = "menu:main"` 命令入口。注意该入口实际指向 `src/menu/__init__.py` 中的 `main()`，并不是 FastAPI 服务。 |
| `uv.lock` | uv 生成的 Python 依赖锁文件，记录解析后的依赖版本与来源。日常安装优先使用 `uv sync`，不要手工编辑锁文件。 |
| `package-lock.json` | 仓库根目录的 npm 锁文件。当前锁文件的 `packages` 为空，根目录没有对应的 `package.json`；前端实际使用的是 `ui/package.json` 与 `ui/package-lock.json`。 |
| `run.py` | Python 命令入口示例，目前只打印 `Hello from menu!`，不启动 API 或 Agent。可作为学习 Python 包入口与脚本的最小示例。 |
| `init_db.py` | 非破坏性本地 MySQL 初始化：创建缺失的业务表/特色菜字段；仅当菜单表为空时写入明确标记的演示菜品；不会删除或改写现有菜品，也不写入预订。运行前确认 `.env` 指向本地开发数据库。 |
| `study.py` | 独立的模型/Agent 学习实验：通过 LangChain 初始化聊天模型、创建无工具 Agent 并流式打印结果。它不是应用后端启动入口，运行前需要检查其中的模型配置及本地环境变量。配套阅读资料见 `study/` 目录。 |

### 后端 API：`api/`

| 文件 | 作用与阅读提示 |
| --- | --- |
| `api/main.py` | FastAPI 应用和 HTTP 接口定义。包含 `/health`、`/chat`、`/faq/suggest`、`/reservation/list`、`/menu/list`；定义请求/响应数据模型；FAQ 在 Redis 中取数并排序，菜单和预订通过 SQLAlchemy 查询 MySQL。可从 `app = FastAPI()`、路由装饰器开始阅读。 |

### Agent 与数据工具：`agent/`

| 文件 | 作用与阅读提示 |
| --- | --- |
| `agent/langchain_assistant.py` | Agent 主体。包含延迟初始化的 embedding、Milvus client、MySQL engine；定义 `search_main_dishes`、`user_flavor_search`、`make_reservation` 三个业务工具；`assistant_query()` 将 Agent 的消息转为 SSE；`create_agent()` 设置模型、工具、系统提示词、地图 MCP client 和内存 checkpointer。`create_chat_model()` 默认使用 `deepseek-flash`，并在 `OPENAI_BASE_URL` 主机为 `api.deepseek.com` 时自动附加 `extra_body={"thinking": {"type": "disabled"}}` 关闭思考模式（通用工具循环不回放 reasoning_content）。建议按“工具 → Agent 创建 → 流式调用”的顺序学习。 |
| `agent/prompts/system_prompt.txt` | Agent 的系统提示词，定义助手角色、可回答范围、预订所需信息、二次确认要求和餐厅资料。Agent 的行为约束与业务规则主要从这里理解；提示词不能替代后端对输入、权限和数据的校验。 |
| `agent/milvus_data_sync.py` | 将 MySQL 菜品转换为文本、计算 embedding 并写入 Milvus collection 的学习/初始化脚本。当前文件在模块末尾直接执行 `insert_data()`，且会先删除同名 collection 再重建，具有破坏性；务必先检查代码、目标环境和备份，不要在生产数据上试跑。 |
| `agent/redis_data_sync.py` | 定义示例 FAQ 及 `sync_faq_items_to_redis()`，用 Redis Hash 保存问答、用 Set 索引 FAQ key，并通过 pipeline 批量写入。函数定义后不会自动调用；目前连接地址写死为 `redis://localhost:6379`，与 API 读取 `REDIS_URL` 的方式不同。 |
| `agent/redis_demo.py` | Redis 命令教学示例，演示 String、Hash、Set 和 pipeline。文件末尾会立即执行 `redis_command_demo1()` 并写入示例 key；`redis_command_demo2()` 中还包含 30 秒等待。不要在只想导入函数时直接导入此模块。 |

### Python 包：`src/`

| 文件 | 作用与阅读提示 |
| --- | --- |
| `src/menu/__init__.py` | `menu` 包入口，定义 `main()` 并打印示例文本。与 `pyproject.toml` 中的 `menu` 命令对应；不是 API 路由或 Agent 实现。 |
| `src/.env` | 当前工作区中存在的本地环境文件，不在 Git 跟踪清单内；内容使用 `LLM_BASE_URL`、`LLM_API_KEY` 等名称，而应用代码实际读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 等变量。并且后端明确从仓库根目录加载 `.env`，因此不要假定 `src/.env` 会被应用读取。建议在仓库根目录创建 `.env` 并按下方配置填写；不要提交密钥。 |

### 学习资料与测试：`study/`、`tests/`

| 文件 | 作用与阅读提示 |
| --- | --- |
| `study/agent-learning-guide.html` | Agent 学习指南网页版，浏览器直接打开即可阅读；与本文“建议学习路径”互补，侧重 Agent 原理与本项目代码的对照讲解。 |
| `study/详细教程.pdf` | 项目详细教程 PDF（约 3 MB），适合离线系统学习。 |
| `tests/test_assistant.py` | 后端 Agent 单元测试：不调用外部模型、不写真实数据库。覆盖模型客户端 TLS/关闭行为、DeepSeek 非思考模式参数、配置缺失报错、菜单查询与向量检索回退、SSE 流式输出与错误脱敏。用 `uv run python -m unittest discover -s tests -v` 运行。 |

### 前端：`ui/`

| 文件 | 作用与阅读提示 |
| --- | --- |
| `ui/package.json` | 前端项目定义。列出 Vue、Element Plus、Axios 和 Vite 依赖，以及 `dev`、`build`、`preview` 脚本。 |
| `ui/package-lock.json` | 前端 npm 依赖锁文件。使用 `npm ci` 时根据该文件安装一致的依赖版本。 |
| `ui/index.html` | Vite 的 HTML 入口，提供 `#app` 挂载节点并加载 `/src/main.js`；内置 🍽️ emoji 图标、主题色 `#FFD100` 和标题「智能点餐助手 - AI 智能点餐系统」。 |
| `ui/public/dishes/*.jpg` | 16 张菜品实拍图（宫保鸡丁、番茄炒蛋、炒饭、酸辣汤等）及 `default.jpg` 兜底图。`app.vue` 按菜名关键词映射到对应图片；Vite 构建时原样复制到 `dist/`。 |
| `ui/vite.config.js` | 配置 Vue 插件、`@` 到 `src` 的别名、开发服务器端口 `3000` 和 API 代理。代理把 `/api/...` 转为本机后端（当前本地配置为 `http://127.0.0.1:8010`）。 |
| `ui/start.bat` | Windows 前端启动辅助脚本：检查 Node.js，缺少 `node_modules` 时运行 `npm install`，然后执行 `npm run dev`。日常可用 `npm ci` 获得锁文件指定的依赖版本。 |
| `ui/readme.md` | 前端目录下的旧版说明文档，包含初始功能介绍。部分结构、接口和功能描述可能与当前代码不符；以本根目录 README、`ui/src` 和后端路由为准。 |
| `ui/src/main.js` | Vue 应用入口：创建 App、注册 Element Plus、引入组件样式、设置 Vue 全局错误处理并挂载到 `#app`。 |
| `ui/src/app.vue` | 主页面与交互逻辑（约 2800 行，已随“更换前端”重写）。分区：顶部品牌栏（搜索框、我的订单/我的预订/AI 助手按钮）、店铺信息条、左侧常驻 AI 对话面板（快捷提问 chips、FAQ 联想、SSE 流式消费、推荐菜高亮）、右侧分类导航 + 菜品卡片（真实图片、辣度/素食/分类标签、加购按钮）、底部购物车结算栏，以及购物车/确认订单/下单成功/我的订单/我的预订等抽屉与弹窗。下单为前端演示闭环，订单存 localStorage。模板、`setup()` 与样式均在同一文件中；阅读时可先按 template 的分区注释浏览页面结构，再跟进对应函数。 |
| `ui/src/api/index.js` | 前端 API 封装。Axios 实例处理普通 JSON 请求；聊天流使用 Fetch 和 `ReadableStream` 解析 SSE；导出聊天、配送、菜单、FAQ、预订和健康检查方法。配送方法对应后端不存在的 `/delivery`（调用会 404），且页面尚无配送表单入口；健康检查方法虽已声明，但页面没有调用。 |

## 环境要求

- Python **3.12 或更高版本**。
- [uv](https://docs.astral.sh/uv/)；用于创建/同步 Python 依赖环境。
- Node.js 与 npm；用于前端开发与构建。
- 按使用功能准备服务：MySQL（菜单和预订）、Redis（FAQ）、Milvus（向量检索）、OpenAI 兼容模型 API（Agent 对话）。
- Agent 的菜品语义检索需要本地 `models/bge-m3` 模型目录。

不使用某项可选功能时，不一定要启动其服务。例如只调试前端构建，无需连接数据库；但菜单和预订查询必须有 MySQL，FAQ 推荐必须有 Redis，聊天需要模型 API，向量检索工具需要 Milvus 和 embedding 模型。

## 环境变量配置

后端通过 `load_dotenv()`/`load_dotenv(PROJECT_ROOT / ".env")` 加载环境变量。请在**仓库根目录**创建 `.env`，不要把真实密钥提交到 Git：

```dotenv
# OpenAI 兼容聊天模型：聊天 Agent 必需
OPENAI_API_KEY=替换为你的密钥
OPENAI_BASE_URL=https://你的模型服务地址/v1
OPENAI_MODEL=deepseek-flash  # 示例；必须替换为该 API 账号可用的模型 ID

# SQLAlchemy 主数据库：菜单、预订列表、预订写入
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USERNAME=你的数据库用户名
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=menu

# FAQ 推荐
REDIS_URL=redis://localhost:6379/0

# 菜品向量搜索
MILVUS_URI=http://localhost:19530
MILVUS_TOKEN=
```

配置与代码的对应关系：

- Agent 初始化明确要求 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`；`OPENAI_MODEL` 未设置时默认使用 `deepseek-flash`。模型名称必须是当前 API 账号可用的模型 ID；使用 OpenAI 兼容接口，不代表只能连接特定模型服务商。当 `OPENAI_BASE_URL` 的主机为 `api.deepseek.com` 时，模型客户端会自动附加 `extra_body={"thinking": {"type": "disabled"}}` 关闭 DeepSeek 思考模式（当前通用工具循环不回放 reasoning_content）；连接其他服务商时不附加该参数。
- `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USERNAME`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 用于 SQLAlchemy engine；特色菜和口味推荐工具复用同一数据库连接，无需另外配置 `MYSQL_BASE_*`。
- `REDIS_URL` 供 API 的 FAQ 查询使用；但 `agent/redis_data_sync.py` 和 `agent/redis_demo.py` 示例目前各自写有 localhost 连接地址。
- `MILVUS_URI`、`MILVUS_TOKEN` 与本地 `models/bge-m3` 用于可选向量检索。未配置、结果为空或检索失败时，口味推荐读取 MySQL 在售菜单供助手筛选；基础推荐无需先安装 embedding 模型或配置 Milvus。
- 地图 MCP 为可选功能，通过 `.env` 的 `AMAP_MCP_URL` 配置获准使用的 SSE 地址；不设置就不加载，连接失败不会阻止本地工具使用。

## 安装与启动

### 1. 安装 Python 依赖

从仓库根目录运行：

```bash
uv sync
```

### 2. 初始化本地 MySQL（仅首次需要）

确认仓库根目录 `.env` 指向本地开发数据库，然后运行：

```bash
uv run python init_db.py
```

脚本不会删除表或已有数据，只在菜单为空时添加明确标注的演示菜品；预订表保持不变。不要在生产数据库运行演示初始化。

### 3. 启动后端 API

```bash
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
```

- API 地址：<http://127.0.0.1:8010>
- OpenAPI 文档：<http://127.0.0.1:8010/docs>
- 存活检查：<http://127.0.0.1:8010/health>

`/health` 成功只代表 FastAPI 进程响应，不代表其他依赖已经连通。聊天状态标签在首次请求前显示“待验证”，请求时显示“响应中”，成功收到模型文本并结束后显示“可用”，失败显示“异常”。

基础验收：先问“你们几点营业？”，再问“你们有哪些特色菜？”、“推荐几个不辣的菜”。菜单记录既用于右侧展示，也供助手查询真实菜名、价格、口味和过敏原；仅插入数据不会修复模型服务连接。用户只说“点菜”时助手会先询问需求，不会自动创建预订或声称完成真实订单。

模型连接使用 certifi CA 根证书并保持 HTTPS 证书及主机名校验，避免 Windows truststore 证书链处理异常。鉴权、网络、超时和模型名错误会返回安全提示，详细异常见后端终端；修改 `.env` 后重启后端。

### 4. 安装并启动前端

打开另一个终端：

```bash
cd ui
npm ci
npm run dev
```

浏览器访问 Vite 终端输出的 Local 地址。默认是 <http://localhost:3000>；端口被占用时会自动递增（例如 `http://localhost:3002`）。不要反复启动多个前后端进程；当前代理连接的是 8010 后端。Windows 也可在 `ui` 目录运行：

```bat
start.bat
```

开发服务器代理规则在 `ui/vite.config.js`：前端请求 `/api/menu/list` 时，Vite 转发到 `http://127.0.0.1:8010/menu/list`。

### 5. 构建和预览前端

在 `ui` 目录执行：

```bash
npm run build
npm run preview
```

`npm run build` 生成 `ui/dist/` 静态文件；`preview` 用于本地预览构建结果。实际部署需由 Web 服务器托管静态文件，并单独设置 API 转发。

## 后端 API 清单

以下是 `api/main.py` 当前实际注册的路由。直接请求后端时路径不带 `/api`；从前端开发服务器调用时会带 `/api` 并由 Vite 移除此前缀。

| 方法 | 路径 | 请求/响应说明 |
| --- | --- | --- |
| `GET` | `/health` | 返回 `{ "status": "ok", "service": "aimenu-api" }`；轻量存活检查。 |
| `POST` | `/chat` | 请求 JSON：`{ "query": "..." }`；响应类型为 `text/event-stream`，每条 `data:` 包含 JSON，文本片段为 `type: token`，错误事件为 `type: error`。 |
| `GET` | `/faq/suggest?query=...&limit=...` | 查询 FAQ 推荐；`limit` 默认 `1`，服务端限制在 `1` 到 `10`；响应含 `success`、原始查询和 `suggestions`。 |
| `GET` | `/reservation/list` | 查询预订记录，返回 `reservations`、`count` 和状态消息。 |
| `GET` | `/menu/list` | 查询可售菜品，返回 `menu_items`、`count` 和状态消息。 |

**并非现有后端路由的路径：** `ui/src/api/index.js` 中的 `POST /delivery` 目前会返回 404。前端也没有完整订单提交 API。

## Agent 工作方式与工具说明

`create_agent()` 创建 LangGraph ReAct Agent，核心不是预先写死“问题对应答案”，而是把可用工具和系统提示词提供给模型，让模型在对话中判断何时需要调用工具。工具结果再交回 Agent，由模型组织自然语言回复。

| 工具 | 数据来源 | 用途与当前注意点 |
| --- | --- | --- |
| `search_main_dishes` | MySQL 当前配置数据库中的 `menu_items` 表 | 如果表有 `is_featured` 字段，则查询特色可售菜；旧表缺少该字段时回退为查询所有可售菜。 |
| `user_flavor_search` | MySQL 在售菜单；可选本地 `bge-m3` + Milvus | 已配置时优先向量检索；未配置、失败或无结果时回退到真实在售菜单，助手根据辣度、食材等筛选，不捏造菜品。 |
| `make_reservation` | MySQL `reservation_order` | 把预订信息写入数据库。系统提示词要求信息齐全后先向用户二次确认；需要进一步学习时，应确认工具调用前的业务校验和写入边界。 |
| 地图 MCP 工具 | `AMAP_MCP_URL` 指定的 SSE 服务 | 配置后按需加载远端地图工具；未配置或连接失败不阻塞基础聊天。 |

聊天请求到达后，`assistant_query()` 创建/复用 Agent，并用 LangGraph `astream(..., stream_mode="messages")` 获取消息；后端跳过工具消息，将文本片段包装为 SSE `data:` JSON；前端 `sendStreamMessage()` 读取响应流并把 token 追加到当前 assistant 消息。

## 数据服务初始化与安全提示

- **MySQL**：需准备代码中使用的 `menu_items` 与 `reservation_order` 表结构和数据。仓库未跟踪 SQL 初始化文件（`.gitignore` 忽略 `menu.sql`），因此表结构需从项目已有数据库/独立资料获取，不能仅靠本 README 推断。
- **Redis**：FAQ 推荐读取 `faq:all_items` 集合及其引用的 Hash。`agent/redis_data_sync.py` 提供示例 FAQ 和同步函数，但尚未提供命令行入口；需在开发环境显式调用函数。
- **Milvus**：向量数据同步脚本包含删除并重建 `menu_items` collection 的逻辑，而且文件加载时自动执行。务必先审阅并修改脚本的副作用与连接配置，确认非生产环境和备份后再执行。
- **密钥与数据库凭证**：只放在未跟踪的本地 `.env` 或安全的部署密钥管理中，不要写入 README、提交记录、日志或公开 issue。
- **用户输入和 Agent 工具**：Prompt 约束是行为指引，不是访问控制。面向真实业务部署前，应补充身份认证、授权、输入验证、预订确认的服务端校验、敏感信息处理、超时和可观测性。

## 建议学习路径

按以下顺序从“能运行”逐步走到“理解 Agent 与数据流”。每一步都可以单独验证，不建议一开始同时排查所有外部依赖。

### 第 1 阶段：认识项目与启动前端

1. 阅读本 README 的“项目文件导览”和“请求流程”。
2. 先查看 `ui/package.json`、`ui/index.html`、`ui/src/main.js`，理解 npm 脚本、HTML 挂载点和 Vue 启动过程。
3. 阅读 `ui/src/app.vue` 的 template，按分区注释标出品牌栏、AI 对话面板、分类导航与菜品卡片、购物车结算栏和各抽屉/弹窗；暂时跳过较长的 CSS。
4. 在 `ui` 下运行 `npm ci`、`npm run dev`。前端需要 API 才能填充业务数据，但构建本身可先通过 `npm run build` 检查。
5. 读 `ui/vite.config.js`，理解 `/api` 代理与浏览器同源请求的关系。

**阶段目标：** 能说明浏览器如何加载 Vue 页面，且理解前端端口 `3000` 与后端端口 `8010` 的关系。

### 第 2 阶段：理解普通 HTTP API 与数据库

1. 阅读 `api/main.py` 的 Pydantic 响应模型和路由，先看 `/health`，再看 `/menu/list` 与 `/reservation/list`。
2. 阅读 `ui/src/api/index.js` 中 Axios 拦截器及 `menuAPI`、`reservationAPI`。
3. 回到 `ui/src/app.vue`，跟踪 `onMounted()`、`loadMenuItems()`、`loadReservations()` 如何请求并更新 Vue `ref` 状态，以及菜品图片如何按名称关键词映射到 `ui/public/dishes/`。
4. 配置本地 MySQL 和根目录 `.env` 后访问 `/docs` 或 `/menu/list`。如果暂时没有数据库，可以先理解查询与错误响应，不要把服务暂不可用误认为路由未启动。

**阶段目标：** 能从页面加载追踪到 FastAPI 路由、SQL 查询和 JSON 响应，再说明数据如何呈现。

### 第 3 阶段：掌握 Redis FAQ 推荐

1. 阅读 `agent/redis_data_sync.py`，理解 Hash 保存问答、Set 保存 FAQ key、pipeline 批量写入。
2. 阅读 `api/main.py` 的 `_get_redis_client()`、`_load_faq_items_from_redis()`、`_get_similarity_score()` 和 `/faq/suggest`。
3. 阅读 `ui/src/api/index.js` 的 `faqAPI`，再读 `ui/src/app.vue` 的输入监听、去抖计时器和建议点击处理。
4. 用独立开发 Redis 验证数据结构。不要直接运行有导入副作用的示例模块；先检查它执行什么命令。

**阶段目标：** 理解用户输入经过 debounce、HTTP 请求、Redis 读取、相似度排序后如何成为可点击建议。

### 第 4 阶段：学习流式 Agent 与工具调用

1. 先读 `agent/prompts/system_prompt.txt`，提炼角色、约束和预订信息收集步骤。
2. 在 `agent/langchain_assistant.py` 阅读三个业务工具及其入参/返回值，留意它们各自依赖的数据库或向量服务。
3. 阅读 `create_agent()`，识别模型、工具列表、MCP client、prompt 和 checkpointer 分别注入到 Agent 的位置。
4. 阅读 `assistant_query()`，理解一次用户输入如何进入 `astream()`，以及工具消息为什么不作为普通文本返回。
5. 对照 `api/main.py` 的 `/chat` 与 `ui/src/api/index.js` 的 `sendStreamMessage()`，从服务端生成器一直追踪到浏览器的流式响应解析。
6. 配好模型 API 后先问无需外部查询的餐厅问题，再试特色菜/预订等工具场景；查看后端日志确认是否调用工具。Milvus 和地图 MCP 可作为后续独立依赖接入。

**阶段目标：** 能区分“LLM 生成文本”和“Agent 决定调用工具”，并解释 SSE 如何把模型输出逐段送到 UI。

### 第 5 阶段：数据同步、脚本与工程化

1. 阅读 `agent/milvus_data_sync.py` 的 MySQL 数据读取、文本拼装、embedding、schema/index 创建和插入流程；先做代码审阅，不要直接执行会删除 collection 的脚本。
2. 阅读 `agent/redis_demo.py` 与 `study.py`，把它们当作实验脚本，辨认模块级执行、副作用和外部服务依赖。
3. 阅读 `pyproject.toml`、`uv.lock`、`.python-version`，理解 Python 版本、声明式依赖和锁文件的职责；用 `uv sync` 还原环境。
4. 对比根目录 `package-lock.json` 与 `ui/package-lock.json`，理解前端工作区实际位于 `ui/`。
5. 评估尚未实现的功能：配送路由、订单 API、输入/权限校验、错误提示和自动化测试。每次补功能时同步更新 API 文档与测试。

**阶段目标：** 能安全地描述数据导入副作用，并区分应用入口、实验脚本、锁文件和真正的服务启动命令。

## 常见问题排查

| 现象 | 检查方向 |
| --- | --- |
| 页面打开但菜单为空 | 确认后端已启动、Vite 代理目标正确、根目录 `.env` 的 MySQL 配置有效且 `menu_items` 表可读。 |
| FAQ 建议为空 | 确认 Redis 正常、`REDIS_URL` 正确，且 `faq:all_items` 和对应 FAQ Hash 已写入。Redis 故障时 API 会返回空建议。 |
| 聊天报错或超时 | 根据页面错误检查 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、账号权限/额度及网络。查看后端异常；确认重启的是代理连接的 8010 服务，不是其他端口的旧进程。 |
| 菜品口味向量搜索失败 | 基础推荐会回退到 MySQL，先确认菜单可读；如需启用向量搜索，再配置 `models/bge-m3`、Milvus 服务和匹配的 collection。 |
| `/delivery` 404 | 这是当前实现状态：后端没有配送路由，前端 API 声明不能代表服务端已经实现。 |
| `uv run menu` 只打印一句话 | 这是 `src/menu/__init__.py` 的预期行为；它不是 FastAPI 启动命令。请用本文中的 Uvicorn 命令启动 API。 |
| `.env` 修改后仍读不到 | 确认文件位于仓库根目录，变量名与代码读取名称一致；当前 `src/.env` 中的 `LLM_*` 变量并不匹配应用代码使用的 `OPENAI_*` 名称。 |

## 测试与项目状态

已提供不调用外部模型、不写入真实数据库的连接与推荐回归测试：

```bash
uv run python -m unittest discover -s tests -v
```

另外可执行以下基础验证：

```bash
# 仓库根目录：确认 Python 依赖环境
uv sync

# ui 目录：检查前端依赖与生产构建
npm ci
npm run build
```

运行业务接口还需要相应外部服务和数据。不要把“前端构建成功”或 `/health` 返回成功等同于 Agent、数据库和所有业务流程已经通过集成测试。
