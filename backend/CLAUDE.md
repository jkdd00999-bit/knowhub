# 知智 KnowHub — 企业级智能知识助手

## 语言规则
- 始终用中文回答用户的所有问题。
- 代码注释用中文。

## 项目结构

### 后端核心文件
| 文件 | 用途 |
|------|------|
| `FastAPI.py` | FastAPI 主应用，JWT 认证，REST API，文件上传，问答接口，调度器 |
| `agent_graph.py` | LangGraph 11 节点 Agent Workflow 定义（核心） |
| `agent.py` | Agent 入口封装，调用 agent_graph |
| `chunk.py` | 文档加载、分块、Embedding、混合检索器、向量库构建 |
| `tools.py` | 37 个 LangChain Agent 工具（文档/网络/文本/记忆/邮件/定时任务） |
| `memory.py` | 记忆提取工具模块（语义记忆/情节记忆/知识沉淀） |
| `hierarchical_splitter.py` | 层级语义分块器（兼容政策文书+学术论文） |

### Agent Skills 目录
| 文件 | 用途 |
|------|------|
| `skills/__init__.py` | Skills 模块初始化 |
| `skills/query_optimizer.py` | Query 优化（指代消解、问题补全） |
| `skills/clarify_skill.py` | 澄清判断（LLM 判断是否需要用户澄清） |
| `skills/source_ranker.py` | 来源权威性排序 |

### 前端目录（位于 `../frontend/`）
| 目录/文件 | 用途 |
|------|------|
| `src/views/` | 页面组件（Home, Dashboard, Documents, Conversations 等） |
| `src/components/` | 通用组件（AiAssistant, Toast, SkeletonLoader） |
| `src/composables/` | 组合式函数（useRequest, useToast） |
| `src/router/index.js` | 路由配置（含权限守卫） |

## 技术栈
- **LLM**: Qwen3.7-Plus（DashScope，兼容 OpenAI 接口）
- **Embedding**: DashScope `text-embedding-v4`，1024 维向量
- **Agent 编排**: LangGraph StateGraph（11 节点工作流）
- **向量数据库**: ChromaDB，存储在 `vector_db/`
- **重排序**: BGE-Reranker v2-m3（本地 CrossEncoder）
- **关键词检索**: BM25（jieba 中文分词）
- **缓存**: Redis（热点问答缓存）
- **前端框架**: Vue 3 + Vite
- **部署**: Docker + docker-compose

## Agent Workflow（11 节点）
```
START
  → load_memory（加载用户记忆）
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

## 关键配置
- 环境变量文件: `.env`（参考 `.env.example`）
- 必填项: `DASHSCOPE_API_KEY`, `TAVILY_API_KEY`, `JWT_SECRET_KEY`
- 可选: `HF_ENDPOINT`（HuggingFace 镜像加速）, `CORS_ORIGINS`, `SMTP_*`（邮件推送）

## 运行方式
- `python FastAPI.py` — 启动 Web API（端口 8000）
- 或 `uvicorn FastAPI:app --host 0.0.0.0 --port 8000`
- Docker 部署: 在项目根目录执行 `docker-compose up -d`

## 数据存储
- SQLite 数据库: `data/knowhub.db`
- 文档目录: `documents/`
- 向量数据库: `vector_db/`
- 定时任务: `scheduled_tasks.json`

## 重要说明
- 使用 `contextvars.ContextVar` 管理请求级别的用户隔离（tools.py）
- 文件工具已添加路径验证，防止路径穿越攻击
- 前端使用 DOMPurify 清理 v-html 渲染的内容，防止 XSS
