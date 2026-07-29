# agent_graph.py
# LangGraph 多节点 Agent Workflow

import os
import traceback
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from memory import _auto_extract_all

# ==================== 配置（从 .env 文件加载）====================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3.7-plus"

if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY 或在 .env 文件中配置")

llm = ChatOpenAI(
    model=QWEN_MODEL,
    temperature=0.3,
    openai_api_key=DASHSCOPE_API_KEY,
    openai_api_base=QWEN_BASE_URL
)

# ==================== AgentExecutor 单例缓存 ====================
_tool_calling_executor = None


def _get_tool_calling_executor():
    """获取或创建 AgentExecutor 单例（避免每次请求都重建）"""
    global _tool_calling_executor
    if _tool_calling_executor is None:
        from tools import ALL_TOOLS
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是知智，企业级智能知识助手。你有以下工具可用：

## 重要规则
1. 用户可能一次提出多个需求，你可以连续调用多个工具
2. 优先使用工具获取信息，而不是自己编造
3. 回答要友好、完整、有用
4. 引用信息来源（如有）
5. 最重要：search_documents 只能搜索本地已上传的文档。如果 search_documents 没有找到相关信息，你必须立即调用 search_web 进行联网搜索。

现在开始帮助用户！"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
        _tool_calling_executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=15
        )
    return _tool_calling_executor


# ==================== RAG Prompt ====================
PROMPT = PromptTemplate(
    template="""你是知智，企业级智能知识助手。请根据以下参考资料回答用户问题。

【参考资料】
{context}

【对话历史】
{history}

【用户问题】
{question}

【要求】
1. 回答要准确、完整、有条理
2. 优先使用参考资料中的信息，并注明来源
3. 如果参考资料中没有相关信息，可以基于你的知识回答，但要说明
4. 回答要友好、专业

【回答】""",
    input_variables=["context", "question", "history"]
)

# ==================== 全局 RAG 组件（懒加载）====================
_hybrid_retriever = None
_reranker = None
_rag_init_lock = __import__('threading').Lock()


def _init_rag():
    """懒初始化 RAG 组件（线程安全的双重检查锁）"""
    global _hybrid_retriever, _reranker
    if _hybrid_retriever is not None:
        return

    with _rag_init_lock:
        if _hybrid_retriever is not None:
            return
        try:
            from chunk import initialize_rag_components
            _, _hybrid_retriever, _reranker = initialize_rag_components()
        except Exception as e:
            print(f"[WARN] RAG 初始化失败: {e}")
            traceback.print_exc()


# ==================== AgentState 定义 ====================
class AgentState(TypedDict):
    """LangGraph 全局状态"""

    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    conversation_id: int
    raw_message: str
    rewritten_query: str
    needs_clarification: bool
    clarification_question: str
    intent: str
    user_memory: str
    episodic_memory: str
    knowledge_nuggets: str
    memory_context: str
    retrieved_docs: List[Any]
    rag_context: str
    references: List[Dict]
    answer: str
    needs_tool_fallback: bool
    source: str


# ==================== 节点 1: load_memory ====================
def load_memory_node(state: AgentState) -> dict:
    """加载用户记忆：语义记忆 + 情节记忆 + 知识沉淀"""
    user_id = state["user_id"]
    memory_parts = []

    try:
        from tools import _get_memory_conn
        conn = _get_memory_conn()
        try:
            # 一次性查询所有三类记忆，共用一个连接
            rows = conn.execute(
                "SELECT memory_key, memory_value FROM user_memory WHERE user_id=?",
                (user_id,)
            ).fetchall()
            if rows:
                lines = ["【用户长久记忆】"]
                for k, v in rows:
                    lines.append(f"  • {k}: {v}")
                memory_parts.append("\n".join(lines))

            epi_rows = conn.execute(
                """SELECT task_description, fix, success_count FROM episodic_memory
                   WHERE user_id=? ORDER BY hit_count DESC LIMIT 3""",
                (user_id,)
            ).fetchall()
            if epi_rows:
                lines = ["【相关经验记忆】"]
                for desc, fix, cnt in epi_rows:
                    if fix:
                        lines.append(f"  • {desc}: {fix} (成功{cnt}次)")
                memory_parts.append("\n".join(lines))

            kn_rows = conn.execute(
                """SELECT title, content FROM knowledge_nuggets
                   WHERE user_id=? ORDER BY hit_count DESC LIMIT 3""",
                (user_id,)
            ).fetchall()
            if kn_rows:
                lines = ["【知识沉淀】"]
                for title, content in kn_rows:
                    lines.append(f"  • {title}: {content[:200]}")
                memory_parts.append("\n".join(lines))
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] 记忆加载失败: {e}")

    memory_context = "\n\n".join(memory_parts) if memory_parts else ""

    return {
        "memory_context": memory_context,
        "user_memory": memory_parts[0] if len(memory_parts) > 0 else "",
        "episodic_memory": memory_parts[1] if len(memory_parts) > 1 else "",
        "knowledge_nuggets": memory_parts[2] if len(memory_parts) > 2 else "",
    }


# ==================== 节点 2: query_rewrite ====================
def query_rewrite_node(state: AgentState) -> dict:
    """指代消解 + 问题补全"""
    raw = state["raw_message"]
    msgs = state["messages"]

    history_msgs = [m for m in msgs[:-1]]
    if len(history_msgs) < 2:
        return {"rewritten_query": raw}

    history_parts = []
    for m in history_msgs[-6:]:
        role = "用户" if isinstance(m, HumanMessage) else "助手"
        history_parts.append(f"{role}：{m.content[:300]}")
    history_text = "\n".join(history_parts)

    rewrite_prompt = f"""你是一个问题重写助手。请根据对话历史，把当前问题重写成完整独立的问题。

【对话历史】
{history_text}

【当前问题】
{raw}

规则：
1. 替换指代词（"这个"、"那篇"、"上述方法"等）为具体内容
2. 补全省略主语的追问
3. 如果问题已完整独立，直接输出原问题
4. 只输出重写后的问题

重写后的问题："""

    try:
        resp = llm.invoke(rewrite_prompt)
        rewritten = resp.content.strip()
        if rewritten and rewritten != raw:
            print(f"[REWRITE] {raw} -> {rewritten}")
            return {"rewritten_query": rewritten}
    except Exception as e:
        print(f"[WARN] 问题重写失败: {e}")

    return {"rewritten_query": raw}


# ==================== 节点 3: query_clarify ====================
def query_clarify_node(state: AgentState) -> dict:
    """判断是否需要向用户澄清问题（严格模式：只在真正模糊时才澄清）"""
    query = state["rewritten_query"]
    memory = state.get("memory_context", "")

    clarify_prompt = f"""判断以下问题是否**极其模糊**，必须澄清才能回答。

{f'【用户背景】{memory}' if memory else ''}

【用户问题】{query}

**判断标准（必须同时满足才需要澄清）：**
1. 问题完全没有明确的对象或主题
2. 无法判断用户想要什么类型的信息
3. 问题过于简短（少于5个字）且含义不明

**以下情况不需要澄清（直接输出 NO）：**
- 询问最新信息、新闻、发展情况（即使没有指定具体领域）
- 询问技术、行业、市场等通用话题
- 问题有明确的主谓宾结构
- 可以通过联网搜索回答的问题

如果问题清晰或可以通过搜索回答，输出：NO
只有当问题**极其模糊**无法理解时，输出：YES，并写出澄清问题。

输出格式：YES/NO [澄清问题]"""

    try:
        resp = llm.invoke(clarify_prompt)
        content = resp.content.strip()
        # 只在前3个字符内查找 YES
        first_line = content.split('\n')[0].strip()
        if first_line.startswith("YES") or first_line == "YES":
            question = content[3:].strip().lstrip("：:").strip()
            # 如果澄清问题为空或太短，不澄清
            if question and len(question) > 10:
                return {
                    "needs_clarification": True,
                    "clarification_question": question,
                }
    except Exception as e:
        print(f"[WARN] 澄清判断失败: {e}")

    return {"needs_clarification": False, "clarification_question": ""}


# ==================== 节点 4: clarify_response ====================
def clarify_response_node(state: AgentState) -> dict:
    """生成澄清回复并结束"""
    question = state["clarification_question"]
    return {
        "answer": question,
        "source": "clarify",
        "messages": [AIMessage(content=question)],
    }


# ==================== 节点 5: route_query ====================
def route_query_node(state: AgentState) -> dict:
    """LLM 意图路由：web / knowledge / chat"""
    query = state["rewritten_query"]

    intent_prompt = f"""判断用户问题类型：

【用户问题】{query}

类型：
- web：需要实时信息、最新数据、联网搜索（新闻、天气、股价、最新政策等）
- knowledge：需要查询已上传文档/知识库的内容（分析、总结、对比文档等）
- chat：普通闲聊、问候、与知识库无关的通用问题

只输出类型名称：web / knowledge / chat"""

    try:
        resp = llm.invoke(intent_prompt)
        intent = resp.content.strip().lower()
        if intent not in ("web", "knowledge", "chat"):
            intent = "knowledge"
    except Exception as e:
        print(f"[WARN] 意图路由失败: {e}")
        intent = "knowledge"

    return {"intent": intent}


# ==================== 节点 6: hybrid_retrieval ====================
def hybrid_retrieval_node(state: AgentState) -> dict:
    """混合检索：HybridRetriever + BGEReranker"""
    query = state["rewritten_query"]

    _init_rag()

    if _hybrid_retriever is None:
        return {
            "retrieved_docs": [],
            "rag_context": "",
            "references": [],
            "needs_tool_fallback": True,
        }

    docs = _hybrid_retriever.similarity_search(query, k=30)
    if not docs:
        return {
            "retrieved_docs": [],
            "rag_context": "",
            "references": [],
            "needs_tool_fallback": True,
        }

    try:
        reranked = _reranker.rerank(query, docs, top_k=8) if _reranker else docs[:8]
    except Exception as e:
        print(f"[WARN] 重排序失败: {e}")
        reranked = docs[:8]

    diverse = []
    file_counts = {}
    for d in reranked:
        src = d.metadata.get("source", "")
        cnt = file_counts.get(src, 0)
        if cnt < 1:
            diverse.append(d)
            file_counts[src] = cnt + 1
        if len(diverse) >= 4:
            break

    context_parts = []
    references = []
    for i, d in enumerate(diverse):
        src = d.metadata.get("source", "未知")
        section = d.metadata.get("section_title", "")
        parts = [f"【来源{i + 1}: {src}"]
        if section:
            parts.append(f" | {section}")
        parts.append("】")
        context_parts.append("".join(parts) + f"\n{d.page_content}")
        references.append({
            "doc_id": i + 1,
            "title": src,
            "content": d.page_content[:200]
        })

    return {
        "retrieved_docs": diverse,
        "rag_context": "\n\n".join(context_parts),
        "references": references,
        "needs_tool_fallback": False,
    }


# ==================== 节点 7: rag_generate ====================
def rag_generate_node(state: AgentState) -> dict:
    """基于 RAG 上下文 + 记忆生成回答"""
    memory = state.get("memory_context", "")
    context = state["rag_context"]
    query = state["rewritten_query"]
    messages = state["messages"]

    history_parts = []
    for m in messages[-6:-1]:
        if isinstance(m, HumanMessage) and m.content == state["raw_message"]:
            continue
        role = "用户" if isinstance(m, HumanMessage) else "助手"
        history_parts.append(f"{role}：{m.content[:300]}")
    history_context = "\n".join(history_parts)

    if memory:
        history_context = memory + "\n\n" + history_context

    formatted = PROMPT.format(
        context=context,
        question=query,
        history=history_context
    )
    response = llm.invoke(formatted)

    return {
        "answer": response.content,
        "messages": [AIMessage(content=response.content)],
        "source": "rag",
    }


# ==================== 节点 8: validate_answer ====================
def validate_answer_node(state: AgentState) -> dict:
    """检查 RAG 回答是否包含'找不到'信号"""
    answer = state["answer"]
    no_result_signals = [
        "没有找到", "未找到", "找不到", "无法找到", "暂未收录",
        "建议您查阅", "建议您自行", "没有相关信息", "不包含",
        "资料中没有", "没有关于", "未涉及", "建议咨询"
    ]

    if any(signal in answer for signal in no_result_signals):
        print("[FALLBACK] RAG 回答包含'未找到'信号，切换 Agent 联网搜索")
        return {"needs_tool_fallback": True}

    return {"needs_tool_fallback": False}


# ==================== 节点 9: tool_calling ====================
async def tool_calling_node(state: AgentState) -> dict:
    """Agent 工具调用（使用缓存的 AgentExecutor，异步执行避免阻塞事件循环）"""
    raw = state["raw_message"]
    intent = state.get("intent", "web")
    messages = state["messages"]

    chat_history = []
    for m in messages[-10:-1]:
        if isinstance(m, HumanMessage):
            chat_history.append(("human", m.content))
        elif isinstance(m, AIMessage):
            chat_history.append(("assistant", m.content))

    # 使用缓存的 AgentExecutor
    executor = _get_tool_calling_executor()

    # 异步调用，避免阻塞事件循环
    result = await executor.ainvoke({
        "input": raw,
        "chat_history": chat_history
    })
    answer = result["output"]

    source = "web" if intent == "web" else "tool_fallback"

    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
        "source": source,
        "needs_tool_fallback": False,
    }


# ==================== 节点 10: chat_reply ====================
def chat_reply_node(state: AgentState) -> dict:
    """普通闲聊回复"""
    memory = state.get("memory_context", "")
    raw = state["raw_message"]

    chat_prompt = f"""你是知智，企业级智能知识助手。请友好地回复用户。

{f'{memory}' if memory else ''}

【用户消息】{raw}

【回复】"""

    resp = llm.invoke(chat_prompt)

    return {
        "answer": resp.content,
        "messages": [AIMessage(content=resp.content)],
        "source": "chat",
    }


# ==================== 节点 11: save_memory ====================
def save_memory_node(state: AgentState) -> dict:
    """回答后自动提取记忆"""
    try:
        messages = []
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                messages.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                messages.append({"role": "assistant", "content": m.content})

        _auto_extract_all(
            state["user_id"],
            state["raw_message"],
            state.get("answer", ""),
            messages,
            state.get("conversation_id", 0),
        )
    except Exception as e:
        print(f"[WARN] 记忆保存失败: {e}")

    return {}


# ==================== 条件路由函数 ====================
def route_after_clarify(state: AgentState) -> str:
    """澄清判断后的路由"""
    if state.get("needs_clarification"):
        return "clarify"
    return "route"


def route_by_intent(state: AgentState) -> str:
    """意图路由"""
    intent = state.get("intent", "knowledge")
    return intent


def route_after_validate(state: AgentState) -> str:
    """RAG 验证后的路由"""
    if state.get("needs_tool_fallback"):
        return "fallback"
    return "save"


# ==================== 构建 StateGraph ====================
def build_graph():
    """构建 LangGraph StateGraph"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("query_clarify", query_clarify_node)
    graph.add_node("clarify_response", clarify_response_node)
    graph.add_node("route_query", route_query_node)
    graph.add_node("hybrid_retrieval", hybrid_retrieval_node)
    graph.add_node("rag_generate", rag_generate_node)
    graph.add_node("validate_answer", validate_answer_node)
    graph.add_node("tool_calling", tool_calling_node)
    graph.add_node("chat_reply", chat_reply_node)
    graph.add_node("save_memory", save_memory_node)

    # 固定边
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "query_rewrite")
    graph.add_edge("query_rewrite", "query_clarify")
    graph.add_edge("hybrid_retrieval", "rag_generate")
    graph.add_edge("rag_generate", "validate_answer")
    graph.add_edge("tool_calling", "save_memory")
    graph.add_edge("chat_reply", "save_memory")
    graph.add_edge("clarify_response", "save_memory")
    graph.add_edge("save_memory", END)

    # 条件边 1：是否需要澄清
    graph.add_conditional_edges(
        "query_clarify",
        route_after_clarify,
        {
            "clarify": "clarify_response",
            "route": "route_query",
        }
    )

    # 条件边 2：意图路由
    graph.add_conditional_edges(
        "route_query",
        route_by_intent,
        {
            "web": "tool_calling",
            "knowledge": "hybrid_retrieval",
            "chat": "chat_reply",
        }
    )

    # 条件边 3：RAG 回答是否有效
    graph.add_conditional_edges(
        "validate_answer",
        route_after_validate,
        {
            "fallback": "tool_calling",
            "save": "save_memory",
        }
    )

    return graph.compile()


# ==================== 编译图（全局单例）====================
compiled_graph = build_graph()

print("[OK] LangGraph StateGraph compiled")
print("[INFO] Nodes: load_memory -> query_rewrite -> query_clarify -> route_query -> ...")
print("[INFO] Conditional edges: clarify check, intent routing, RAG validation")
