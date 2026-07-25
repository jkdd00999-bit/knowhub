# 知智 KnowHub — 企业级智能知识助手

面向企业官网知识服务场景，基于 **LangGraph + FastAPI + Qwen + Chroma** 构建企业级 AI 知识助手，实现企业知识问答、文档智能检索、联网搜索、用户记忆及智能订阅等能力。

## 项目结构

```
knowhub/
├── backend/          # 后端 (FastAPI + LangGraph + RAG)
│   ├── api.py                  # FastAPI 后端，JWT 认证，REST API
│   ├── agent_graph.py          # LangGraph 多节点 Agent Workflow
│   ├── agent.py                # Agent 入口
│   ├── tools.py                # 60+ Agent 工具集
│   ├── chunk.py                # 文档分块、Embedding、混合检索
│   ├── hierarchical_splitter.py # 层级语义分块器
│   ├── skills/                 # RAG 优化 Skill
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── frontend/         # 前端 (Vue 3 + Vite)
    ├── src/
    │   ├── views/              # 页面组件
    │   ├── components/         # 通用组件
    │   ├── composables/        # 组合式函数
    │   └── router/             # 路由配置
    ├── Dockerfile
    ├── nginx.conf
    └── package.json
```

## 核心功能

- **企业知识库自动构建**：支持上传 PDF、Word、Markdown 等企业资料，自动完成文档解析、Chunk 切分、Embedding 向量化及知识库构建
- **Agent Workflow 设计**：基于 LangGraph 设计多节点 Agent Workflow，编排 Query Rewrite、Query Clarify、Hybrid Retrieval、Memory、Tool Calling
- **RAG 混合检索**：BM25 + BGE Embedding + BGE Reranker 构建混合检索架构，结合标题分块及语义重排序优化召回效果
- **Tool Calling**：集成 Web Search、邮件通知等工具，知识库未命中时自动联网搜索
- **智能订阅推送**：用户创建行业政策订阅任务，定时检索最新信息并自动发送邮件
- **长期记忆管道**：LLM 自动抽取四类记忆并标注重要性，语义去重，自动衰减

## 技术栈

| 层 | 技术 |
|---|------|
| LLM | Qwen3.7-Plus (DashScope) |
| Agent 编排 | LangGraph StateGraph |
| 后端框架 | FastAPI |
| 向量数据库 | ChromaDB |
| Embedding | DashScope text-embedding-v4 |
| 重排序 | BGE-Reranker |
| 关键词检索 | BM25 (jieba 分词) |
| 前端框架 | Vue 3 + Vite |
| 部署 | Docker + docker-compose |

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
# 配置 .env 文件（API Keys）
python api.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### Docker 一键部署

```bash
docker-compose up -d
```
