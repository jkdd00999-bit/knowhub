"""
记忆提取工具模块
统一管理自动记忆提取逻辑，避免循环依赖
"""
import os
import json
import re


def _auto_extract_memory(user_id: str, question: str, answer: str):
    """自动从对话中提取用户的长期记忆，存入 SQLite"""
    try:
        from tools import _get_memory_conn
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="qwen3.7-plus",
            temperature=0.3,
            openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
            openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        prompt = (
            f"用户的提问：{question[:300]}\n"
            f"助手的回答：{answer[:300]}\n\n"
            f"从以上对话中提取关于这个用户的重要信息。只提取明确的信息，不要推测。\n"
            f"提取项包括：用户名、职业、偏好风格、关注领域、重要上下文等。\n"
            f"如果没有可提取的新信息，回复 EMPTY。\n"
            f"如果有，用 JSON 格式回复：{{\"key\": \"value\", ...}}\n"
            f"只用中文回复，不要其他内容。"
        )
        resp = llm.invoke(prompt)
        text = resp.content.strip()
        if "EMPTY" in text or len(text) < 5:
            return

        json_match = re.search(r'\{[^{}]+\}', text)
        if not json_match:
            return
        data = json.loads(json_match.group())

        conn = _get_memory_conn()
        try:
            for k, v in data.items():
                if isinstance(v, str) and len(v) >= 1 and len(k) >= 1:
                    conn.execute(
                        "INSERT OR REPLACE INTO user_memory (user_id, memory_key, memory_value, updated_at) "
                        "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                        (user_id, k.strip(), v.strip()[:500])
                    )
            conn.commit()
        finally:
            conn.close()
        if data:
            print(f"[INFO] 自动记忆提取: {list(data.keys())}")
    except Exception as e:
        print(f"[WARN] 自动记忆提取失败: {e}")


def _auto_extract_all(user_id: str, question: str, answer: str,
                      messages: list, conv_id: int):
    """统一自动提取：用户画像 + 情节记忆 + 对话归档 + 知识沉淀"""
    try:
        _auto_extract_memory(user_id, question, answer)
    except Exception as e:
        print(f"[WARN] memory._auto_extract_memory 失败: {e}")

    try:
        from tools import _auto_extract_episode
        _auto_extract_episode(user_id, question, messages, conv_id)
    except Exception as e:
        print(f"[WARN] memory._auto_extract_episode 失败: {e}")

    try:
        from tools import _archive_dialogue_turns
        _archive_dialogue_turns(user_id, conv_id, messages)
    except Exception as e:
        print(f"[WARN] memory._archive_dialogue_turns 失败: {e}")

    try:
        from tools import _auto_extract_knowledge
        _auto_extract_knowledge(user_id, question, answer, messages, conv_id)
    except Exception as e:
        print(f"[WARN] memory._auto_extract_knowledge 失败: {e}")
