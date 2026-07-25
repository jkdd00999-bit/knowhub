# 知智 KnowHub - SaaS 企业级智能知识助手

> 基于 LangGraph + FastAPI + Qwen + Chroma 构建的企业级 AI 知识助手平台

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

## 📖 项目简介

知智 KnowHub 是面向企业官网知识服务场景的 **SaaS 企业级智能知识助手**，实现企业知识问答、文档智能检索、联网搜索、用户记忆及智能订阅等能力。

平台支持企业上传产品手册、制度文档、政策文件等资料自动构建知识库，并以 **Agent Workflow** 协调 RAG、Memory 及 Tool Calling，实现企业 AI 助手的快速部署与应用。

## ✨ 核心功能

### 1. 企业知识库自动构建
- 支持上传 **PDF、Word、Markdown** 等企业资料
- 自动完成文档解析、Chunk 切分、Embedding 向量化及知识库构建
- 结合 **Metadata** 管理文档来源、发布时间及业务分类
- 支持增量更新知识库，减少人工维护成本

### 2. Agent Workflow 设计
- 基于 **LangGraph** 设计多节点 Agent Workflow
- 将 Query Rewrite、Query Clarify、Hybrid Retrieval、Memory、Tool Calling 等能力进行流程编排
- 实现复杂任务自动执行

### 3. RAG 优化
- 采用 **BM25 + BGE Embedding + BGE Reranker** 构建混合检索架构
- 结合标题分块及语义重排序优化召回效果
- 覆盖 **500+ 篇企业文档**，实现 **3 秒内检索回复**
- **Recall@10 由 70.8% 提升至 91.8%**

### 4. 工具集成
- 集成 **Web Search、邮件通知** 等工具
- 知识库未命中时自动联网搜索
- 支持用户创建行业政策订阅任务，定时检索最新信息并自动发送邮件
- 实现"查询—分析—订阅"业务闭环

### 5. 长期记忆管道
- LLM 自动抽取四类记忆（偏好/事实/事件/知识）并标注重要性
- 入库前与已有记忆做语义比对去重
- 长时间未调用的记忆自动衰减权重
- 确保注入 prompt 的上下文始终精准聚焦用户当前意图

### 6. SaaS 平台特性
- 多用户支持，JWT 认证
- 对话历史管理
- 文档管理面板
- 响应式前端界面

## 🛠️ 技术栈

| 模块 | 技术 |
|------|------|
| **后端框架** | FastAPI (异步) |
| **前端框架** | Vue 3 + Vite |
| **LLM** | Qwen (通义千问) |
| **Embedding** | DashScope text-embedding-v4 / BGE |
| **向量数据库** | ChromaDB |
| **检索策略** | BM25 + 向量检索 + BGE Reranker |
| **Agent 框架** | LangGraph |
| **数据库** | SQLite (开发) / PostgreSQL (生产) |
| **缓存** | Redis |
| **部署** | Docker + Docker Compose |

## 📁 项目结构

```
.
├── RAG/                    # 后端代码
│   ├── api.py             # FastAPI 主入口
│   ├── agent.py           # Agent 逻辑
│   ├── chunk.py           # 文档分块与检索
│   ├── tools.py           # 工具集（联网搜索、邮件等）
│   ├── hierarchical_splitter.py  # 层级文本分块器
│   ├── requirements.txt   # Python 依赖
│   ├── Dockerfile         # 后端 Docker 配置
│   └── docker-compose.yml # 容器编排
│
└── help-center/
    └── frontend/          # 前端代码
        ├── src/
        │   ├── views/     # 页面组件
        │   ├── components/# 通用组件
        │   ├── router/    # 路由配置
        │   └── composables/# 组合式函数
        ├── Dockerfile     # 前端 Docker 配置
        └── nginx.conf     # Nginx 配置
```

## 🚀 快速开始

### 本地开发

#### 后端

```bash
# 进入后端目录
cd RAG

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python api.py
```

后端运行在 `http://localhost:8000`

#### 前端

```bash
# 进入前端目录
cd help-center/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`

### Docker 部署

```bash
# 克隆项目
git clone <repo-url>
cd knowledge-assistant

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY

# 启动服务
docker-compose up -d

# 访问
# 前端: http://localhost
# 后端: http://localhost:8000
```

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| 文档处理速度 | 100+ 页/分钟 |
| 检索响应时间 | < 3 秒 |
| Recall@10 | 91.8% |
| 并发支持 | 100+ QPS |
| 知识库容量 | 1000+ 文档 |

## 🔑 API 文档

启动后端后访问：`http://localhost:8000/docs`

主要接口：

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/upload` - 上传文档
- `POST /api/chat` - AI 对话
- `GET /api/conversations` - 获取对话列表
- `GET /api/files` - 获取文件列表

## 📝 使用场景

1. **政策法规检索** - 快速查找科技、财税、环保等领域政策文件
2. **企业知识管理** - 构建产品手册、制度文档知识库
3. **智能客服** - 自动回答客户常见问题
4. **研究助手** - 文献检索与分析

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- 邮箱：1924521171@qq.com
- 电话：15589520210

---

**Made with ❤️ by 栾晓程**
