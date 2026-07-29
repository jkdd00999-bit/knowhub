# 知智 KnowHub - 企业级智能知识助手

> 基于 LangGraph + FastAPI + Qwen + Chroma 构建的企业级 AI 知识助手平台

## 📖 项目简介

知智 KnowHub 是面向企业官网知识服务场景的**企业级智能知识助手**，实现企业知识问答、文档智能检索、联网搜索、用户记忆及智能订阅等能力。

平台支持企业上传产品手册、制度文档、政策文件等资料自动构建知识库，并以 **Agent Workflow** 协调 RAG、Memory 及 Tool Calling，实现企业 AI 助手的快速部署与应用。

## ✨ 核心功能

### 1. 企业知识库自动构建
- 支持上传 **PDF、Word、Markdown、TXT** 等企业资料
- 自动完成文档解析、Chunk 切分、Embedding 向量化及知识库构建
- 自定义层级语义分块器，兼容政策条文和学术论文
- 支持增量更新知识库

### 2. Agent Workflow 设计
- 基于 **LangGraph StateGraph** 设计 11 节点 Agent Workflow
- 包含 Query Rewrite、Query Clarify、Hybrid Retrieval、Memory、Tool Calling 等节点
- 实现复杂任务自动执行和意图路由

### 3. RAG 混合检索
- 采用 **BM25 + BGE Embedding + BGE Reranker** 构建混合检索架构
- 结合层级语义分块和语义重排序优化召回效果
- 覆盖 500+ 篇企业文档，3 秒内检索回复

### 4. 工具集成
- 集成 **37 个 Agent 工具**，覆盖文档搜索、网络搜索、文本处理、记忆管理、邮件发送等
- 知识库未命中时自动联网搜索（Tavily Search API）
- 支持用户创建行业政策订阅任务，定时检索最新信息并自动发送邮件

### 5. 长期记忆管道
- LLM 自动抽取四类记忆：用户偏好/事实、情节经验、知识沉淀、对话归档
- 入库前与已有记忆做语义比对去重（余弦相似度 > 0.85 判定重复）
- 长时间未调用的记忆自动衰减权重（60 天未匹配淘汰）

### 6. 用户系统
- JWT Token 认证，支持注册/登录/角色区分
- 多用户隔离：记忆、对话、订阅均按 user_id 隔离
- 管理后台：文档管理、AI 未回答问题统计

## 🛠️ 技术栈

| 模块 | 技术 |
|------|------|
| **后端框架** | FastAPI (异步) |
| **前端框架** | Vue 3 + Vite |
| **LLM** | Qwen3.7-Plus (DashScope) |
| **Embedding** | DashScope text-embedding-v4 (1024维) |
| **向量数据库** | ChromaDB |
| **检索策略** | BM25 + 向量检索 + BGE-Reranker v2-m3 |
| **Agent 框架** | LangGraph (11节点 StateGraph) |
| **数据库** | SQLite (WAL模式) |
| **缓存** | Redis |
| **部署** | Docker + Docker Compose |

## 📁 项目结构

```
knowhub/
├── backend/                    # 后端代码
│   ├── FastAPI.py              # FastAPI 主入口（JWT认证、REST API、调度器）
│   ├── agent_graph.py          # LangGraph 11 节点 Agent Workflow
│   ├── agent.py                # Agent 入口封装
│   ├── chunk.py                # 文档分块与检索
│   ├── tools.py                # 工具集（37 个工具）
│   ├── memory.py               # 记忆管理模块
│   ├── hierarchical_splitter.py # 层级语义分块器
│   ├── skills/                 # RAG 优化技能
│   │   ├── query_optimizer.py  #   查询优化
│   │   ├── clarify_skill.py    #   澄清判断
│   │   └── source_ranker.py    #   来源排序
│   ├── requirements.txt        # Python 依赖
│   ├── Dockerfile              # 后端 Docker 配置
│   └── .env.example            # 环境变量模板
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 通用组件（AiAssistant, Toast）
│   │   ├── router/             # 路由配置
│   │   ├── composables/        # 组合式函数
│   │   └── utils/              # 工具函数
│   ├── Dockerfile              # 前端 Docker 配置
│   └── nginx.conf              # Nginx 配置
│
├── docker-compose.yml          # 容器编排（后端+前端+Redis）
└── .env.example                # 环境变量模板
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- Redis（可选，Docker 部署自动包含）

### 本地开发

#### 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写：DASHSCOPE_API_KEY、TAVILY_API_KEY、JWT_SECRET_KEY

# 启动服务
python FastAPI.py
```

后端运行在 `http://localhost:8000`，API文档在 `http://localhost:8000/docs`

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`

### Docker 一键部署

```bash
# 在项目根目录
cp .env.example .env
# 编辑 .env 填写必填项

# 启动所有服务
docker-compose up -d

# 访问：前端 http://localhost | 后端 http://localhost:8000
```

## 📡 API 接口

启动后端后访问 `http://localhost:8000/docs` 查看完整 API 文档。

主要接口：
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/chat` - AI 对话
- `POST /api/upload` - 上传文档
- `GET /api/conversations` - 对话列表
- `GET /api/docs` - 文档列表
- `POST /api/subscriptions` - 创建订阅

## 📄 许可证

MIT License

---

**Made with ❤️ by 栾晓程**
