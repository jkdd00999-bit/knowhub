# 知智 KnowHub — 企业级智能知识助手

> 面向企业官网知识服务场景，基于 **LangGraph + FastAPI + Qwen + Chroma** 构建的企业级 AI 知识助手平台。  
> 支持企业知识问答、文档智能检索、联网搜索、用户记忆、智能订阅推送等核心能力，实现企业 AI 助手的快速部署与应用。

---

## ✨ 核心功能

### 1. 企业知识库自动构建
- 支持上传 **PDF、Word（.docx）、Markdown（.md）、TXT** 等多种格式企业资料
- 自动完成文档解析 → 层级语义分块 → Embedding 向量化 → ChromaDB 知识库构建
- 结合 Metadata 管理文档来源、发布时间及业务分类，支持增量更新知识库
- 自定义 `HierarchicalTextSplitter` 层级语义分块器，兼容红头文件、政策条文、学术论文

### 2. Agent Workflow 设计
基于 **LangGraph StateGraph** 设计 11 节点多 Agent 工作流，流程编排如下：

```
START
  → load_memory（加载用户记忆：语义记忆 + 情节记忆 + 知识沉淀）
  → query_rewrite（指代消解 + 问题补全）
  → query_clarify（LLM 判断是否需要澄清）
    → [需澄清] clarify_response → save_memory → END
    → [不需澄清] route_query（意图路由：web / knowledge / chat）
      → [knowledge] hybrid_retrieval → rag_generate → validate_answer
        → [回答有效] save_memory → END
        → [未命中] tool_calling → save_memory → END
      → [web] tool_calling → save_memory → END
      → [chat] chat_reply → save_memory → END
```

### 3. RAG 混合检索
- **BM25 关键词检索**（jieba 分词）+ **向量语义检索**（DashScope Embedding）混合加权
- **BGE-Reranker** 语义重排序，优化召回精度
- 覆盖 **500+ 篇**企业文档，实现 3 秒内检索回复
- Redis 缓存热点问答，减少重复计算

### 4. Tool Calling 工具调用
- 集成 **37 个 Agent 工具**，覆盖文档搜索、网络搜索、文本处理、记忆管理、邮件发送等
- 知识库未命中时**自动切换联网搜索**（Tavily Search API），实现知识兜底
- 支持翻译、文本润色、关键词提取等实用工具

### 5. 智能订阅推送
- 用户创建行业政策订阅任务（如"每日 AI 动态推送"）
- 支持**每天/每周**定时推送频率
- 后台调度器自动执行：Agent 检索最新信息 → 整理摘要 → **SMTP 邮件推送**到用户邮箱
- 实现"查询 — 分析 — 订阅"业务闭环

### 6. 长期记忆管道
- LLM 自动抽取**四类记忆**：用户偏好/事实（user_memory）、情节经验（episodic_memory）、知识沉淀（knowledge_nuggets）、对话归档（dialogue_archive）
- 入库前与已有记忆做**语义比对去重**（余弦相似度 > 0.85 判定重复）
- 长时间未调用的记忆**自动衰减权重**（60 天未匹配淘汰，低命中 30 天淘汰）
- 确保注入 Prompt 的上下文始终精准聚焦用户当前意图

### 7. 用户系统与权限
- JWT Token 认证，支持注册/登录/角色区分
- 多用户隔离：记忆、对话、订阅均按 user_id 隔离
- 管理后台：文档 CRUD、AI 未回答问题统计

---

## 🏗️ 项目结构

```
knowhub/
├── backend/                    # 后端 (Python 3.10+)
│   ├── FastAPI.py              # FastAPI 主应用，JWT 认证，REST API，调度器
│   ├── agent_graph.py          # LangGraph 11 节点 Agent Workflow
│   ├── agent.py                # Agent 入口封装
│   ├── tools.py                # 37 个 Agent 工具集（文档/网络/文本/记忆/邮件）
│   ├── chunk.py                # 文档加载、分块、Embedding、混合检索器
│   ├── memory.py               # 记忆提取工具模块
│   ├── hierarchical_splitter.py # 层级语义分块器（兼容政策文书+学术论文）
│   ├── skills/                 # RAG 优化 Skill
│   │   ├── __init__.py         #   Skills 模块初始化
│   │   ├── query_optimizer.py  #   Query 优化
│   │   ├── clarify_skill.py    #   澄清判断
│   │   └── source_ranker.py    #   来源权威性排序
│   ├── Dockerfile              # 后端容器配置
│   ├── .env.example            # 环境变量配置模板
│   ├── requirements.txt        # Python 依赖
│   ├── documents/              # 上传文档存储目录
│   └── vector_db/              # ChromaDB 向量数据库目录
│
├── frontend/                   # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   │   ├── Home.vue        #   首页（产品介绍）
│   │   │   ├── Dashboard.vue   #   用户控制台
│   │   │   ├── Knowledge.vue   #   知识库浏览（含热门文档、FAQ）
│   │   │   ├── Documents.vue   #   文档上传管理
│   │   │   ├── Docs.vue        #   文档详情页
│   │   │   ├── Conversations.vue #  对话历史
│   │   │   ├── Subscriptions.vue #  智能订阅管理
│   │   │   ├── Admin.vue       #   管理后台
│   │   │   ├── Login.vue       #   登录页
│   │   │   ├── Register.vue    #   注册页
│   │   │   └── NotFound.vue    #   404 页面
│   │   ├── components/         # 通用组件
│   │   │   ├── AiAssistant.vue #   AI 助手浮窗
│   │   │   ├── SkeletonLoader.vue # 骨架屏加载
│   │   │   └── Toast.vue       #   消息提示
│   │   ├── composables/        # 组合式函数
│   │   │   ├── useRequest.js   #   HTTP 请求封装
│   │   │   └── useToast.js     #   Toast 提示
│   │   ├── router/             # 路由配置
│   │   │   └── index.js        #   路由定义（含权限守卫）
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 应用入口
│   ├── public/                 # 静态资源
│   ├── Dockerfile              # 前端容器配置
│   ├── nginx.conf              # Nginx 反向代理
│   ├── vite.config.js          # Vite 配置
│   └── package.json            # 前端依赖
│
├── docker-compose.yml          # Docker 容器编排
└── README.md                   # 项目说明
```

---

## 🛠️ 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **LLM** | Qwen3.7-Plus | 阿里云 DashScope，兼容 OpenAI 接口 |
| **Agent 编排** | LangGraph | StateGraph 多节点工作流，条件路由 |
| **后端框架** | FastAPI | 异步 REST API，JWT 认证，自动文档 |
| **向量数据库** | ChromaDB | 持久化向量存储，支持元数据过滤 |
| **Embedding** | DashScope text-embedding-v4 | 1024 维向量，批量生成 |
| **重排序** | BGE-Reranker (v2-m3) | 本地 CrossEncoder 语义重排 |
| **关键词检索** | BM25 | jieba 中文分词 + BM25 评分 |
| **缓存** | Redis | 热点问答缓存，TTL 1 小时 |
| **前端框架** | Vue 3 (Composition API) | `<script setup>` 语法，Vite 5 构建 |
| **部署** | Docker + docker-compose | 前后端容器化，Nginx 反向代理 |

---

## 🚀 快速启动

### 环境要求
- Python 3.10+（3.9 亦可运行，部分语法特性不支持）
- Node.js 18+
- Redis（可选，用于缓存加速）
- 重排模型（可选）：首次启动时自动从 HuggingFace 下载 `BAAI/bge-reranker-v2-m3`（约 2.2GB）。国内用户建议在 `.env` 中设置镜像加速：`HF_ENDPOINT=https://hf-mirror.com`

> **💡 提示**：建议将项目克隆到**无中文字符的路径**（如 `D:\projects\knowhub`），避免 Windows 下 Python 路径编码问题。

### 1. 克隆仓库

```bash
git clone https://github.com/jkdd00999-bit/knowhub.git
cd knowhub
```

### 2. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 复制 .env.example 为 .env 并填写实际值
cp .env.example .env

# 编辑 .env 文件，填写以下必填项：
# - DASHSCOPE_API_KEY: 阿里云 DashScope API Key（获取地址：https://dashscope.console.aliyun.com/）
# - TAVILY_API_KEY: Tavily Search API Key（获取地址：https://tavily.com/）
# - JWT_SECRET_KEY: JWT 密钥（请修改为随机字符串）
#   ⚠️ 生产环境务必设置为随机字符串，否则 JWT 签名不安全

# 启动后端服务
python FastAPI.py
```

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（端口 5173）
npm run dev
```

### 4. Docker 一键部署

```bash
# 确保在项目根目录
cd knowhub

# 配置环境变量（docker-compose 读取根目录 .env）
cp .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY、TAVILY_API_KEY、JWT_SECRET_KEY 等必填项

# 启动所有服务（后端 + 前端 + Redis）
docker-compose up -d
```

启动后访问：
- 前端页面：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

> **💡 提示**：国内用户建议在 `.env` 中设置 HuggingFace 镜像加速：`HF_ENDPOINT=https://hf-mirror.com`

---

## 📡 API 接口一览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| **认证相关** | | | |
| POST | `/api/auth/register` | 用户注册 | ✗ |
| POST | `/api/auth/login` | 用户登录 | ✗ |
| GET | `/api/auth/me` | 获取当前用户信息 | ✓ |
| PUT | `/api/auth/me` | 更新用户信息（邮箱） | ✓ |
| **AI 对话** | | | |
| POST | `/api/chat` | AI 聊天（流式响应） | ✓ |
| **文档管理** | | | |
| POST | `/api/upload` | 上传文档（PDF/Word/MD/TXT） | ✓ |
| GET | `/api/docs` | 文档列表 | ✗ |
| GET | `/api/docs/{id}` | 文档详情 | ✗ |
| GET | `/api/docs/catalog` | 文档目录/分类 | ✗ |
| GET | `/api/docs/hot` | 热门文档 | ✗ |
| GET | `/api/docs/faq` | FAQ 列表 | ✗ |
| POST | `/api/docs` | 创建文档（管理后台） | ✓ |
| PUT | `/api/docs/{id}` | 更新文档（管理后台） | ✓ |
| DELETE | `/api/docs/{id}` | 删除文档 | ✓ |
| **对话管理** | | | |
| POST | `/api/conversations` | 创建新会话 | ✓ |
| GET | `/api/conversations` | 对话列表 | ✓ |
| GET | `/api/conversations/{id}` | 对话详情 | ✓ |
| PUT | `/api/conversations/{id}` | 更新会话（标题/消息） | ✓ |
| DELETE | `/api/conversations/{id}` | 删除对话 | ✓ |
| **订阅推送** | | | |
| GET | `/api/subscriptions` | 订阅列表 | ✓ |
| POST | `/api/subscriptions` | 创建订阅 | ✓ |
| DELETE | `/api/subscriptions/{id}` | 取消订阅 | ✓ |
| **文件管理** | | | |
| GET | `/api/files` | 上传文件列表 | ✓ |
| **管理后台** | | | |
| GET | `/api/admin/unanswered` | 未回答问题统计 | ✓ (admin) |
| **系统** | | | |
| GET | `/api/health` | 健康检查 | ✗ |

---

## 📄 License

本项目仅供学习与展示使用。
