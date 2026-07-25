# 知智 KnowHub — 企业级智能知识助手

## 语言规则
- 始终用中文回答用户的所有问题。
- 代码注释用中文。

## 项目结构
| 文件 | 用途 |
|------|------|
| `chunk.py` | 文档加载、分块、向量库构建、检索器、问答链 |
| `api.py` | FastAPI 后端，JWT 认证，文件上传，问答接口 |
| `hierarchical_splitter.py` | 层级语义分块器（兼容政策文书和学术论文） |
| `crawler.py` | 多省市政府政策爬虫 |
| `tools.py` | LangChain Agent 工具集 |
| `agent.py` | LangChain Agent 入口 |

## 关键配置
- Embedding: DashScope `text-embedding-v4`，batch_size=10
- LLM: Qwen3.7-Plus，通过 DashScope 兼容 OpenAI 接口调用
- 向量库: ChromaDB，存储在 `vector_db/`
- 文档目录: `documents/`

## 运行方式
- `python chunk.py` — 命令行交互问答
- `python api.py` — 启动 Web API（端口 8000）
- `python crawler.py` — 爬取政策文档
