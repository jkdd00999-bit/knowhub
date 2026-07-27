"""
记忆提取工具模块
统一管理自动记忆提取逻辑，避免循环依赖
"""


def _auto_extract_all(user_id: str, question: str, answer: str,
                      messages: list, conv_id: int):
    """统一自动提取：用户画像 + 情节记忆 + 对话归档 + 知识沉淀"""
    try:
        from api import _auto_extract_memory
        _auto_extract_memory(user_id, question, answer)
    except Exception:
        pass

    try:
        from tools import _auto_extract_episode
        _auto_extract_episode(user_id, question, messages, conv_id)
    except Exception:
        pass

    try:
        from tools import _archive_dialogue_turns
        _archive_dialogue_turns(user_id, conv_id, messages)
    except Exception:
        pass

    try:
        from tools import _auto_extract_knowledge
        _auto_extract_knowledge(user_id, question, answer, messages, conv_id)
    except Exception:
        pass
