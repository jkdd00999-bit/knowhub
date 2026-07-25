# agent.py
# LangGraph Agent 封装层
# 提供统一的 chat_async 接口，内部调用 LangGraph StateGraph

from langchain_core.messages import HumanMessage, AIMessage
from agent_graph import compiled_graph, AgentState
from typing import List, Dict, Any


async def chat_async(message: str, history: list = None,
                     user_id: str = "0", conversation_id: int = 0) -> Dict[str, Any]:
    """
    统一的异步聊天接口（LangGraph 图调用）

    Args:
        message: 用户消息
        history: 对话历史，格式为 [("human", content), ("assistant", content), ...]
        user_id: 用户 ID
        conversation_id: 会话 ID

    Returns:
        dict: {
            "output": str,  # 回答内容
            "source": str,  # 来源 ("rag" | "web" | "chat" | "clarify" | "tool_fallback")
            "references": list  # 引用来源
        }
    """
    # 构建 LangChain messages
    messages = []
    if history:
        for role, content in history:
            if role == "human":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=message))

    # 初始化状态
    initial_state: AgentState = {
        "messages": messages,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "raw_message": message,
        "rewritten_query": message,
        "needs_clarification": False,
        "clarification_question": "",
        "intent": "",
        "user_memory": "",
        "episodic_memory": "",
        "knowledge_nuggets": "",
        "memory_context": "",
        "retrieved_docs": [],
        "rag_context": "",
        "references": [],
        "answer": "",
        "needs_tool_fallback": False,
        "source": "",
    }

    # 调用 LangGraph 图
    final_state = await compiled_graph.ainvoke(initial_state)

    return {
        "output": final_state["answer"],
        "source": final_state.get("source", ""),
        "references": final_state.get("references", []),
    }


def chat(message: str, history: list = None) -> str:
    """
    同步聊天接口（向后兼容）

    Args:
        message: 用户消息
        history: 对话历史

    Returns:
        str: 回答内容
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        chat_async(message, history)
    )
    return result["output"]


# 向后兼容：保留 agent_executor 别名（但实际不使用）
class _FakeAgentExecutor:
    """假的 AgentExecutor，仅用于向后兼容"""
    def invoke(self, inputs):
        message = inputs.get("input", "")
        history = inputs.get("chat_history", [])
        history_tuples = [(role, content) for role, content in history]
        result = chat(message, history_tuples)
        return {"output": result}


agent_executor = _FakeAgentExecutor()

print("[OK] agent.py loaded - LangGraph wrapper ready")