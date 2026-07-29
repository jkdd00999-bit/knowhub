"""
知智 KnowHub Agent 工具集 - 完整版
包含文档、学术、网络、文本、数据、文件、图像、代码等 60+ 工具
"""
import os
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
import json
import re
import math
import hashlib
import random
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from contextvars import ContextVar
from langchain.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

# 独立的 LLM 实例（不依赖 chunk.py 的局部变量）
_llm = ChatOpenAI(
    model="qwen3.7-plus",
    temperature=0.3,
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# ==================== 全局 RAG 检索器 ====================
_vector_store = None
_hybrid_retriever = None
_reranker = None
_rag_init_lock = threading.Lock()


def _ensure_rag():
    """确保 RAG 组件已初始化（线程安全的懒加载）"""
    global _vector_store, _hybrid_retriever, _reranker
    if _hybrid_retriever is not None:
        return

    with _rag_init_lock:
        # Double-check after acquiring lock
        if _hybrid_retriever is not None:
            return
        try:
            from chunk import initialize_rag_components
            _vector_store, _hybrid_retriever, _reranker = initialize_rag_components()
        except Exception as e:
            print(f"[WARN] RAG 初始化失败: {e}")


# ==================== 1. 文档工具 (8个) ====================

@tool
def search_documents(query: str) -> str:
    """搜索已上传的文档内容。输入自然语言问题或关键词，返回相关的文档片段。"""
    _ensure_rag()
    if _hybrid_retriever is None:
        return "知识库尚未初始化，请先上传文档"
    docs = _hybrid_retriever.similarity_search(query, k=5)
    if not docs:
        return "未找到相关内容"
    parts = []
    for i, doc in enumerate(docs[:3]):
        src = doc.metadata.get("source", "未知")
        parts.append(f"[来源{i+1}: {src}]\n{doc.page_content[:600]}")
    return "\n\n".join(parts)


@tool
def search_with_rerank(query: str) -> str:
    """精准搜索文档（使用AI重排序）。适合需要最准确答案的场景。"""
    _ensure_rag()
    if _hybrid_retriever is None:
        return "知识库尚未初始化，请先上传文档"
    docs = _hybrid_retriever.similarity_search(query, k=20)
    if not docs:
        return "未找到相关内容"
    if _reranker:
        try:
            docs = _reranker.rerank(query, docs, top_k=3)
        except Exception:
            docs = docs[:3]
    parts = []
    for i, doc in enumerate(docs):
        src = doc.metadata.get("source", "未知")
        parts.append(f"[来源{i+1}: {src}]\n{doc.page_content[:600]}")
    return "\n\n".join(parts)


@tool
def list_all_documents() -> str:
    """列出所有已上传的文档文件名。"""
    from pathlib import Path
    docs_dir = os.path.join(_TOOLS_BASE_DIR, "documents")
    if not os.path.exists(docs_dir):
        return "暂无文档"
    files = sorted(f.name for f in Path(docs_dir).iterdir()
                   if f.suffix in (".pdf", ".txt") and not f.name.startswith("_"))
    if not files:
        return "暂无文档"
    return "\n".join(f"{i+1}. {f}" for i, f in enumerate(files))


@tool
def get_document_info(filename: str) -> str:
    """获取指定文档的详细信息（大小、页数、分块数等）。"""
    filepath = os.path.join(_TOOLS_BASE_DIR, "documents", filename)
    # 路径验证，防止路径穿越
    valid, err = _validate_path(filepath)
    if not valid:
        return f"[ERR] 安全限制: {err}"
    if not os.path.exists(filepath):
        return f"文档「{filename}」不存在"
    size = os.path.getsize(filepath) / 1024
    return f"📄 {filename}\n大小: {size:.1f} KB"


@tool
def get_chunk_statistics() -> str:
    """获取知识库的统计信息（总文档数、总块数等）。"""
    from pathlib import Path
    docs_dir = os.path.join(_TOOLS_BASE_DIR, "documents")
    if not os.path.exists(docs_dir):
        return "📊 知识库统计\n文档数: 0"
    files = list(Path(docs_dir).glob("*.pdf")) + list(Path(docs_dir).glob("*.txt"))
    files = [f for f in files if not f.name.startswith("_")]
    return f"📊 知识库统计\n文档数: {len(files)}\n存储位置: {docs_dir}"


# ==================== 3. 时间日期工具 (6个) ====================

@tool
def get_current_time() -> str:
    """获取当前日期和时间。"""
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


@tool
def get_current_date() -> str:
    """获取当前日期（年月日）。"""
    return datetime.now().strftime("%Y年%m月%d日")


@tool
def get_weekday() -> str:
    """获取今天是星期几。"""
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[datetime.now().weekday()]


@tool
def calculate_date_days(date_str: str, days: int) -> str:
    """计算指定日期加上/减去天数后的日期。
    
    Args:
        date_str: 日期，格式 YYYY-MM-DD
        days: 天数，正数加，负数减
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        result = date + timedelta(days=days)
        return f"{date_str} {'+' if days >= 0 else '-'} {abs(days)}天 = {result.strftime('%Y-%m-%d')}"
    except Exception:
        return "日期格式错误，请使用 YYYY-MM-DD 格式"


@tool
def days_between_dates(date1: str, date2: str) -> str:
    """计算两个日期之间相隔的天数。"""
    try:
        d1 = datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.strptime(date2, "%Y-%m-%d")
        days = abs((d2 - d1).days)
        return f"{date1} 到 {date2} 相差 {days} 天"
    except Exception:
        return "日期格式错误"


@tool
def get_timestamp() -> str:
    """获取当前Unix时间戳。"""
    return str(int(datetime.now().timestamp()))


# ==================== 5. 文本处理工具 (12个) ====================

@tool
def translate(text: str, target_lang: str = "中文") -> str:
    """翻译文本到目标语言。"""
    prompt = f"请将以下文本翻译成{target_lang}，只输出翻译结果：\n{text}"
    return _llm.invoke(prompt).content


@tool
def polish_writing(text: str, style: str = "专业") -> str:
    """润色文字，使表达更流畅专业。
    
    Args:
        text: 要润色的文本
        style: 风格（专业、学术、简洁、口语）
    """
    prompt = f"请用{style}的风格润色以下文字，只输出润色结果：\n{text}"
    return _llm.invoke(prompt).content


@tool
def summarize_text(text: str, max_length: int = 200) -> str:
    """总结长文本，提取核心要点。"""
    prompt = f"请用{max_length}字以内总结以下文本：\n{text[:3000]}"
    return _llm.invoke(prompt).content


@tool
def extract_keywords(text: str, top_k: int = 10) -> str:
    """从文本中提取关键词。"""
    import jieba.analyse
    keywords = jieba.analyse.extract_tags(text, topK=top_k)
    return f"关键词：{', '.join(keywords)}"


@tool
def correct_grammar(text: str) -> str:
    """检查并纠正语法错误。"""
    prompt = f"请检查以下文本的语法错误并纠正，只输出纠正后的文本：\n{text}"
    return _llm.invoke(prompt).content


# ==================== 7. 文件工具 (4个) ====================

# 基于 __file__ 的绝对路径，避免 CWD 不同导致路径错误
_TOOLS_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 允许文件操作的目录白名单（绝对路径）
# 注意：不包含项目根目录，防止 Agent 读写 .env 等敏感文件
_ALLOWED_DIRS = [
    os.path.join(_TOOLS_BASE_DIR, "documents"),
    os.path.join(_TOOLS_BASE_DIR, "data"),
    os.path.join(_TOOLS_BASE_DIR, "vector_db"),
    os.path.join(_TOOLS_BASE_DIR, "temp_files"),
]

def _validate_path(filepath: str) -> tuple[bool, str]:
    """
    验证文件路径是否在允许的目录内，防止路径穿越攻击。
    返回 (是否合法, 错误消息)
    """
    try:
        # 解析为绝对路径，消除 .. 和符号链接
        abs_path = os.path.realpath(os.path.abspath(filepath))
        project_root = os.path.realpath(os.path.abspath(_TOOLS_BASE_DIR))

        # 检查路径是否在项目根目录内（使用 os.sep 防止前缀绕过）
        if not (abs_path == project_root or abs_path.startswith(project_root + os.sep)):
            return False, f"路径不在项目目录内: {filepath}"

        # 检查是否在允许的目录列表中（使用 os.sep 防止前缀绕过）
        for allowed in _ALLOWED_DIRS:
            allowed_abs = os.path.realpath(os.path.abspath(allowed))
            if abs_path == allowed_abs or abs_path.startswith(allowed_abs + os.sep):
                return True, ""

        return False, f"路径不在允许的目录内: {filepath}"
    except Exception as e:
        return False, f"路径验证失败: {e}"


@tool
def read_file(filepath: str) -> str:
    """读取文件内容。支持 txt, md, json 文件。"""
    # 路径验证
    valid, err = _validate_path(filepath)
    if not valid:
        return f"[ERR] 安全限制: {err}"

    if not os.path.exists(filepath):
        return f"文件不存在: {filepath}"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if len(content) > 2000:
                content = content[:2000] + "\n... (内容过长，已截断)"
            return content
    except Exception as e:
        return f"读取失败: {e}"


@tool
def write_to_file(filepath: str, content: str) -> str:
    """写入内容到文件。"""
    # 路径验证
    valid, err = _validate_path(filepath)
    if not valid:
        return f"[ERR] 安全限制: {err}"

    try:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"[OK] 已保存到 {filepath}"
    except Exception as e:
        return f"保存失败: {e}"


@tool
def list_directory(path: str = ".") -> str:
    """列出目录内容。"""
    # 路径验证
    valid, err = _validate_path(path)
    if not valid:
        return f"[ERR] 安全限制: {err}"

    try:
        items = os.listdir(path)
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
        result = f"📂 {path}\n"
        if dirs:
            result += f"\n文件夹 ({len(dirs)}):\n" + "\n".join(f"  📁 {d}" for d in dirs[:10])
        if files:
            result += f"\n\n文件 ({len(files)}):\n" + "\n".join(f"  📄 {f}" for f in files[:20])
        return result
    except Exception as e:
        return f"列出目录失败: {e}"


# ==================== 8. 记忆工具 (持久化 + 按用户隔离) ====================
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.getenv("DB_DIR", os.path.join(_TOOLS_BASE_DIR, "data")), "knowhub.db")

def _get_memory_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn

def _init_memory_table():
    """初始化记忆表"""
    conn = _get_memory_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT NOT NULL,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, memory_key)
        )
    """)
    conn.commit()
    conn.close()

# 初始化表
_init_memory_table()

# 使用 ContextVar 实现请求级别的用户隔离，避免并发串号
# 每个异步任务/线程都有独立的上下文副本
_current_request_user_id: ContextVar[str] = ContextVar(
    "current_user_id", default="default_user"
)

def set_current_user_id(user_id: str):
    """设置当前请求的用户 ID（用于记忆隔离）
    使用 ContextVar，确保并发请求间数据隔离"""
    _current_request_user_id.set(user_id)

def _get_current_user_id() -> str:
    """获取当前用户 ID（由 FastAPI.py 通过 set_current_user_id 设置）"""
    return _current_request_user_id.get()


@tool
def save_to_memory(key: str, value: str, user_id: Optional[str] = None) -> str:
    """记住用户的重要信息或偏好，跨会话持久化存储。
    
    Args:
        key: 信息类型，如 "name", "prefer_style"
        value: 具体内容，如 "张三", "简洁"
        user_id: 用户ID（可选，默认从上下文获取）
    """
    uid = user_id or _get_current_user_id()

    conn = _get_memory_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_memory (user_id, memory_key, memory_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (uid, key, value))
        conn.commit()
    finally:
        conn.close()
    
    return f"[OK] 已记住: {key} = {value}"


@tool
def recall_from_memory(key: str = "", user_id: Optional[str] = None) -> str:
    """回忆用户之前保存的信息。不指定key则返回全部。
    
    Args:
        key: 要回忆的信息类型，留空则返回全部
        user_id: 用户ID（可选，默认从上下文获取）
    """
    uid = user_id or _get_current_user_id()

    conn = _get_memory_conn()
    try:
        cursor = conn.cursor()

        if key:
            cursor.execute(
                "SELECT memory_value FROM user_memory WHERE user_id = ? AND memory_key = ?",
                (uid, key)
            )
            row = cursor.fetchone()
            if row:
                return f"📝 {key} = {row[0]}"
            else:
                return f"未找到关于「{key}」的记忆"
        else:
            cursor.execute(
                "SELECT memory_key, memory_value FROM user_memory WHERE user_id = ?",
                (uid,)
            )
            rows = cursor.fetchall()

            if not rows:
                return "暂无存储的记忆"

            result = "📝 存储的记忆：\n"
            for k, v in rows:
                result += f"  • {k}: {v}\n"
            return result
    finally:
        conn.close()


@tool
def forget_from_memory(key: str, user_id: Optional[str] = None) -> str:
    """忘记指定的记忆。
    
    Args:
        key: 要忘记的信息类型
        user_id: 用户ID（可选，默认从上下文获取）
    """
    uid = user_id or _get_current_user_id()

    conn = _get_memory_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_memory WHERE user_id = ? AND memory_key = ?",
            (uid, key)
        )
        affected = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    if affected:
        return f"[OK] 已忘记: {key}"
    return f"未找到「{key}」的记忆"


@tool
def clear_memory(user_id: Optional[str] = None) -> str:
    """清除当前用户的所有记忆。

    Args:
        user_id: 用户ID（可选，默认从上下文获取）
    """
    uid = user_id or _get_current_user_id()

    conn = _get_memory_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_memory WHERE user_id = ?", (uid,))
        affected = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return f"[OK] 已清除 {affected} 条记忆"


@tool
def update_conversation_summary(summary: str) -> str:
    """更新对话摘要（自动维护）。"""
    # 持久化到 SQLite，重启不丢失
    try:
        uid = _get_current_user_id()
        conn = _get_memory_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO user_memory (user_id, memory_key, memory_value, updated_at) "
                "VALUES (?, '__conversation_summary__', ?, CURRENT_TIMESTAMP)",
                (uid, summary[:2000])
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] 对话摘要持久化失败: {e}")
    return "对话摘要已更新"


# 全局内存缓存（用于热数据加速，可选）
# ==================== 7. 文件工具 (4个) ====================


# ==================== 情节记忆（Episodic Memory）====================
# Embedding 客户端（复用 DashScope）
from openai import OpenAI as DashScopeClient
_embed_client = DashScopeClient(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def _get_task_embedding(text: str) -> list:
    """获取任务描述的 embedding 向量（1536维）"""
    try:
        resp = _embed_client.embeddings.create(
            model="text-embedding-v4",
            input=text[:2000],
            dimensions=1024
        )
        return resp.data[0].embedding
    except Exception:
        return None

def _cosine_similarity(a: list, b: list) -> float:
    """余弦相似度"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def _init_episodic_table():
    """初始化情节记忆表（在 api.py init_db 调用后兜底）"""
    conn = _get_memory_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_embedding TEXT NOT NULL,
            task_description TEXT,
            conversation_id INTEGER,
            mistake TEXT,
            fix TEXT,
            tool_trajectory TEXT,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            hit_count INTEGER DEFAULT 1,
            last_matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

_init_episodic_table()

# 情节记忆匹配阈值
EPISODE_SIMILARITY_THRESHOLD = 0.85
# 淘汰阈值
EPISODE_MAX_AGE_DAYS = 60          # 超过60天未匹配则淘汰
EPISODE_MIN_HIT_COUNT = 2          # 命中少于2次且超过30天淘汰

def _auto_extract_episode(user_id: str, question: str,
                          messages: list, conv_id: int):
    """
    从本轮对话中自动提取情节记忆。
    触发条件：Agent 执行轨迹中有"先失败后调整成功"的模式。
    """
    try:
        # 分析本轮对话是否有多轮工具调用迹象
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if len(user_msgs) < 1:
            return

        # 用 LLM 反思：本轮 Agent 有没有失败→调整→成功的模式
        recent = messages[-8:] if len(messages) >= 8 else messages
        dialog_text = "\n".join(
            f"{'用户' if m['role']=='user' else '助手'}: {m.get('content','')[:300]}"
            for m in recent
        )

        reflection_prompt = f"""分析以下对话，判断 Agent 在执行任务时是否经历了"失败→调整策略→成功"的过程。

【对话内容】
{dialog_text}

【要求】
1. 如果 Agent 一次性成功（只调了一个工具就得到答案），回复 NO_EPISODE
2. 如果 Agent 没有失败直接成功，回复 NO_EPISODE  
3. 只有 Agent 初次尝试失败、调整策略后成功，才提取情节记忆
4. 用 JSON 格式回复：
{{
  "has_episode": true/false,
  "task_type": "政策检索/文档问答/联网搜索/...",
  "task_description": "用户的原始问题（30字以内）",
  "mistake": "Agent 失败的策略是什么",
  "fix": "Agent 调整后成功的策略是什么",
  "tool_trajectory": "工具调用链路简述，如 rag_search失败→web_search成功"
}}
只输出 JSON，不要其他内容。"""

        resp = _llm.invoke(reflection_prompt)
        text = resp.content.strip()

        # 解析 JSON
        json_match = re.search(r'\{[^{}]*"has_episode"[^{}]*\}', text)
        if not json_match:
            return
        data = json.loads(json_match.group())
        if not data.get("has_episode"):
            return

        task_desc = data.get("task_description", question[:30])
        task_type = data.get("task_type", "通用问答")
        mistake = data.get("mistake", "")
        fix_str = data.get("fix", "")
        trajectory = data.get("tool_trajectory", "")

        if not mistake or not fix_str:
            return

        # 获取任务 embedding
        emb = _get_task_embedding(task_desc)
        if emb is None:
            return

        conn = _get_memory_conn()

        # 查找相似任务
        existing = conn.execute(
            "SELECT id, task_embedding, success_count, fail_count, hit_count "
            "FROM episodic_memory WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        matched_id = None
        for row in existing:
            try:
                old_emb = json.loads(row["task_embedding"])
                sim = _cosine_similarity(emb, old_emb)
                if sim > EPISODE_SIMILARITY_THRESHOLD:
                    matched_id = row["id"]
                    break
            except Exception:
                continue

        emb_json = json.dumps(emb)

        if matched_id:
            # 更新已有经验：不覆盖 mistake/fix，只更新计数器
            conn.execute("""
                UPDATE episodic_memory
                SET hit_count = hit_count + 1,
                    last_matched_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    task_embedding = ?
                WHERE id = ?
            """, (emb_json, matched_id))
        else:
            # 新经验
            conn.execute("""
                INSERT INTO episodic_memory
                (user_id, task_type, task_embedding, task_description,
                 conversation_id, mistake, fix, tool_trajectory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, task_type, emb_json, task_desc,
                  conv_id, mistake, fix_str, trajectory))

        # 淘汰：删除超过60天未匹配 + 命中<2次且超过30天
        conn.execute("""
            DELETE FROM episodic_memory WHERE user_id = ?
            AND (
                last_matched_at < datetime('now', '-60 days')
                OR (hit_count < ? AND last_matched_at < datetime('now', '-30 days'))
            )
        """, (user_id, EPISODE_MIN_HIT_COUNT))

        conn.commit()
        conn.close()

        print(f"🧠 情节记忆已提取: {task_type} | 失败策略: {mistake[:30]}... | 成功策略: {fix_str[:30]}...")

    except Exception as e:
        print(f"[WARN] 情节记忆提取失败: {e}")

@tool
def recall_episodes(query: str = "") -> str:
    """
    回忆过去执行任务的经验和策略。Agent 遇到新任务时可以先调用此工具，
    查找是否有类似的成功经验可以复用。
    
    Args:
        query: 当前任务的描述，留空则返回最近的经验列表
    """
    uid = _get_current_user_id()
    conn = _get_memory_conn()

    if query:
        # 语义匹配：找最相似的经验
        emb = _get_task_embedding(query)
        if emb is None:
            conn.close()
            return "无法获取任务向量，请直接描述需求"

        rows = conn.execute(
            "SELECT * FROM episodic_memory WHERE user_id = ? ORDER BY updated_at DESC",
            (uid,)
        ).fetchall()

        if not rows:
            conn.close()
            return "暂无历史经验记录"

        # 计算相似度排序
        scored = []
        for row in rows:
            try:
                old_emb = json.loads(row["task_embedding"])
                sim = _cosine_similarity(emb, old_emb)
                scored.append((sim, row))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3]

        parts = ["📚 相关历史经验（按相似度排序）："]
        for sim, row in top:
            if sim < 0.5:
                continue
            parts.append(
                f"\n--- 相似度 {sim:.0%} ---\n"
                f"任务: {row['task_description']}\n"
                f"失败策略: {row['mistake']}\n"
                f"成功策略: {row['fix']}\n"
                f"工具链路: {row['tool_trajectory']}\n"
                f"命中次数: {row['hit_count']} | 成功率: {row['success_count']}/{row['success_count']+row['fail_count']}"
            )
        conn.close()
        return "\n".join(parts) if len(parts) > 1 else "未找到足够相似的历史经验"
    else:
        # 返回最近经验列表
        rows = conn.execute(
            "SELECT * FROM episodic_memory WHERE user_id = ? ORDER BY updated_at DESC LIMIT 5",
            (uid,)
        ).fetchall()
        conn.close()

        if not rows:
            return "暂无历史经验记录"

        parts = ["📚 最近的经验记录："]
        for row in rows:
            parts.append(
                f"\n  [{row['task_type']}] {row['task_description']}\n"
                f"    [ERR] 失败: {row['mistake'][:50]}...\n"
                f"    [OK] 成功: {row['fix'][:50]}...\n"
                f"    链路: {row['tool_trajectory']}"
            )
        return "\n".join(parts)

@tool
def record_episode(task_type: str, task_description: str,
                   mistake: str, fix: str, tool_trajectory: str = "") -> str:
    """
    手动记录一次情节记忆。当 Agent 发现某个策略值得记住时主动调用。
    
    Args:
        task_type: 任务类型，如 政策检索、文档问答、联网搜索
        task_description: 用户的问题简述
        mistake: 失败的策略
        fix: 成功的策略
        tool_trajectory: 工具调用链路，如 rag_search失败→web_search成功
    """
    uid = _get_current_user_id()
    emb = _get_task_embedding(task_description)
    if emb is None:
        return "[ERR] 获取任务向量失败"

    emb_json = json.dumps(emb)
    conn = _get_memory_conn()

    # 查重
    existing = conn.execute(
        "SELECT id, task_embedding FROM episodic_memory WHERE user_id = ?",
        (uid,)
    ).fetchall()

    for row in existing:
        try:
            old_emb = json.loads(row["task_embedding"])
            if _cosine_similarity(emb, old_emb) > EPISODE_SIMILARITY_THRESHOLD:
                conn.execute(
                    "UPDATE episodic_memory SET hit_count=hit_count+1, "
                    "last_matched_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (row["id"],)
                )
                conn.commit()
                conn.close()
                return f"[OK] 已更新已有经验 #{row['id']}"
        except Exception:
            continue

    conn.execute("""
        INSERT INTO episodic_memory
        (user_id, task_type, task_embedding, task_description,
         mistake, fix, tool_trajectory)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (uid, task_type, emb_json, task_description, mistake, fix, tool_trajectory))
    conn.commit()
    conn.close()
    return f"[OK] 已记录新经验: {task_description[:30]}"


# ==================== 对话归档（Dialogue Archive）====================
DIALOGUE_EMBED_BATCH_SIZE = 5   # 每次最多 embed 5 条消息

def _init_dialogue_archive_table():
    """初始化对话归档表（兜底）"""
    conn = _get_memory_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dialogue_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id INTEGER NOT NULL,
            turn INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            content_embedding TEXT,
            tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_user ON dialogue_archive(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_conv ON dialogue_archive(conversation_id, turn)")
    conn.commit()
    conn.close()

_init_dialogue_archive_table()

def _init_knowledge_nuggets_table():
    """初始化知识沉淀表（兜底）"""
    conn = _get_memory_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nuggets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source_conv_id INTEGER,
            tags TEXT,
            content_embedding TEXT,
            confidence REAL DEFAULT 0.5,
            hit_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_user ON knowledge_nuggets(user_id, created_at)")
    conn.commit()
    conn.close()

_init_knowledge_nuggets_table()

def _archive_dialogue_turns(user_id: str, conv_id: int, messages: list):
    """
    将本轮新增的消息归档到 dialogue_archive。
    只归档非空的 user/assistant 消息，附带 embedding。按内容哈希去重。
    """
    try:
        conn = _get_memory_conn()

        # 获取当前对话已有轮数，确定新增消息的 turn 偏移
        max_turn = conn.execute(
            "SELECT COALESCE(MAX(turn), -1) FROM dialogue_archive WHERE conversation_id=?",
            (conv_id,)
        ).fetchone()[0]

        # 获取已归档消息的内容哈希集合（用于去重）
        existing = conn.execute(
            "SELECT role, content FROM dialogue_archive WHERE conversation_id=?",
            (conv_id,)
        ).fetchall()
        existing_hashes = set()
        for row in existing:
            h = hashlib.md5(f"{row['role']}|{row['content']}".encode()).hexdigest()
            existing_hashes.add(h)

        new_msgs = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if role not in ("user", "assistant") or len(content) < 2:
                continue
            # 内容哈希去重
            content_hash = hashlib.md5(f"{role}|{content}".encode()).hexdigest()
            if content_hash in existing_hashes:
                continue
            existing_hashes.add(content_hash)  # 防止同一批次重复
            new_msgs.append((role, content, max_turn + 1 + len(new_msgs)))

        if not new_msgs:
            conn.close()
            return

        # 批量获取 embedding
        texts = [c for _, c, _ in new_msgs[:DIALOGUE_EMBED_BATCH_SIZE]]
        embeddings = []
        for text in texts:
            emb = _get_task_embedding(text[:2000])
            embeddings.append(json.dumps(emb) if emb else None)

        # 批量写入
        for idx, (role, content, turn_num) in enumerate(new_msgs):
            emb_json = embeddings[idx] if idx < len(embeddings) else None
            conn.execute(
                "INSERT INTO dialogue_archive (user_id, conversation_id, turn, role, content, content_embedding, tokens) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, conv_id, turn_num, role, content, emb_json, len(content))
            )

        conn.commit()
        conn.close()
        print(f"📝 已归档 {len(new_msgs)} 条对话到存档 (conv={conv_id})")
    except Exception as e:
        print(f"[WARN] 对话归档失败: {e}")

@tool
def search_history(query: str = "", top_k: int = 3) -> str:
    """
    搜索历史对话记录。适用于：
    - 用户提到"上次那个文件""之前讨论过的那条法规"
    - 需要回溯之前讨论过的具体内容
    - 查找之前某个话题的完整上下文
    
    Args:
        query: 搜索关键词或语义描述
        top_k: 返回结果数量，默认 3
    """
    uid = _get_current_user_id()
    conn = _get_memory_conn()

    if not query.strip():
        # 返回最近对话摘要
        rows = conn.execute(
            "SELECT role, content, created_at FROM dialogue_archive "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
            (uid,)
        ).fetchall()
        conn.close()
        if not rows:
            return "暂无对话存档"
        parts = ["📝 最近的对话记录："]
        for r in rows:
            parts.append(f"  [{r['role']}] {r['content'][:80]}...  ({r['created_at'][:10]})")
        return "\n".join(parts)

    # 语义检索
    emb = _get_task_embedding(query)
    if emb is None:
        conn.close()
        return "无法获取查询向量，请重试"

    rows = conn.execute(
        "SELECT id, role, content, content_embedding, created_at, conversation_id, turn "
        "FROM dialogue_archive WHERE user_id=? AND content_embedding IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 50",
        (uid,)
    ).fetchall()

    if not rows:
        conn.close()
        return "暂无对话存档，无法搜索"

    # 计算相似度排序
    scored = []
    for row in rows:
        try:
            row_emb = json.loads(row["content_embedding"])
            sim = _cosine_similarity(emb, row_emb)
            if sim > 0.5:
                scored.append((sim, row))
        except Exception:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        conn.close()
        return f"未在历史对话中找到关于「{query}」的相关记录"

    # 获取上下文（每条结果前后各 1 轮）
    parts = [f"🔍 历史对话中关于「{query}」的记录："]
    for sim, row in top:
        context_rows = conn.execute(
            "SELECT role, content FROM dialogue_archive "
            "WHERE conversation_id=? AND turn BETWEEN ? AND ? "
            "ORDER BY turn",
            (row["conversation_id"], max(0, row["turn"] - 1), row["turn"] + 1)
        ).fetchall()

        context_text = "\n".join(f"  {cr['role']}: {cr['content'][:100]}" for cr in context_rows)
        parts.append(
            f"\n--- 相似度 {sim:.0%} | 会话#{row['conversation_id']} 第{row['turn']}轮 | {row['created_at'][:10]} ---\n"
            f"{context_text}"
        )

    conn.close()
    return "\n".join(parts)


# ==================== 知识沉淀（Knowledge Nuggets）====================
_knowledge_collection = None

def _get_knowledge_collection():
    """获取 ChromaDB 知识沉淀 collection（独立于文档 vector store）"""
    global _knowledge_collection
    if _knowledge_collection is not None:
        return _knowledge_collection

    import chromadb
    from chunk import VECTOR_DB_DIR, DashScopeEmbeddings

    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    embeddings = DashScopeEmbeddings()

    try:
        _knowledge_collection = client.get_or_create_collection(
            name="knowledge_nuggets",
            metadata={"hnsw:space": "cosine"}
        )
        print("📚 知识沉淀 collection 已就绪")
    except Exception:
        _knowledge_collection = client.create_collection(
            name="knowledge_nuggets",
            metadata={"hnsw:space": "cosine"}
        )
    return _knowledge_collection


def _auto_extract_knowledge(user_id: str, user_msg: str, assistant_msg: str,
                             messages: list, conv_id: int):
    """
    用 LLM 分析本轮对话，提取可沉淀的知识条目。
    触发条件：用户纠正了错误 / 补充了新知识 / 总结了规律。
    """
    try:
        # 取最近 4 轮对话作为上下文
        recent = messages[-6:] if len(messages) >= 6 else messages
        recent_text = "\n".join(
            f"{'用户' if m['role']=='user' else '助手'}：{m['content'][:200]}"
            for m in recent
        )

        prompt = f"""分析以下对话，判断是否产生了可沉淀为长期知识的内容。

可沉淀的知识类型：
1. 用户纠正了事实错误（如"不是这样，正确的是XXX"）
2. 用户补充了领域知识（如"这个法规实际上是XXX"）
3. 对话中总结出可复用的规律（如"以后遇到XXX就用YYY方法"）

如果本轮对话没有可沉淀的知识，直接回答"NO_KNOWLEDGE"。
如果有，用 JSON 格式输出（只输出 JSON，不要其他文字）：

{{"items": [
  {{"title": "简短标题(≤20字)", "content": "知识内容(≤200字)", "tags": "标签1,标签2", "confidence": 0.8}}
]}}

注意：confidence 根据知识的确定性评分（0.3-1.0），"可能是""似乎"等不确定表述降低分数。

对话内容：
{recent_text}

用户最新消息：{user_msg}
助手回复：{assistant_msg[:300]}
"""
        response = _llm.invoke(prompt)
        text = response.content.strip()

        if "NO_KNOWLEDGE" in text or not text:
            return

        # 解析 JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return
        data = json.loads(json_match.group())
        items = data.get("items", [])

        if not items:
            return

        # 写入 SQLite + ChromaDB
        conn = _get_memory_conn()
        collection = _get_knowledge_collection()

        for item in items:
            title = item.get("title", "")[:50]
            content = item.get("content", "")[:500]
            tags = item.get("tags", "")[:100]
            confidence = float(item.get("confidence", 0.5))

            if len(content) < 10 or confidence < 0.4:
                continue

            # 去重：检查是否已有高度相似的知识
            existing = conn.execute(
                "SELECT id, content, content_embedding FROM knowledge_nuggets WHERE user_id=?",
                (user_id,)
            ).fetchall()

            is_duplicate = False
            emb = _get_task_embedding(content)
            if emb and existing:
                for ex in existing:
                    if ex["content_embedding"]:
                        try:
                            ex_emb = json.loads(ex["content_embedding"])
                            if _cosine_similarity(emb, ex_emb) > 0.85:
                                is_duplicate = True
                                # 更新已有条目（提升 confidence）
                                new_conf = min(1.0, confidence + 0.05)
                                conn.execute(
                                    "UPDATE knowledge_nuggets SET confidence=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                    (new_conf, ex["id"])
                                )
                                break
                        except Exception:
                            pass

            if is_duplicate:
                continue

            emb_json = json.dumps(emb) if emb else None

            # SQLite
            conn.execute(
                "INSERT INTO knowledge_nuggets (user_id, title, content, source_conv_id, tags, content_embedding, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, title, content, conv_id, tags, emb_json, confidence)
            )
            nugget_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # ChromaDB
            try:
                collection.add(
                    ids=[f"nugget_{nugget_id}"],
                    documents=[content],
                    metadatas=[{"title": title, "tags": tags, "user_id": user_id, "confidence": confidence}]
                )
            except Exception:
                pass

        conn.commit()
        conn.close()
        print(f"🧠 已沉淀 {len(items)} 条知识 (conv={conv_id})")
    except Exception as e:
        print(f"[WARN] 知识沉淀提取失败: {e}")


@tool
def recall_knowledge(query: str = "", top_k: int = 3) -> str:
    """
    从历史对话中沉淀的知识库里检索相关知识。
    适用于：
    - 用户问"之前是不是说过XXX"
    - 需要引用之前纠正过的事实
    - 查找对话中积累的规律或经验

    Args:
        query: 搜索关键词或语义描述
        top_k: 返回结果数量，默认 3
    """
    uid = _get_current_user_id()
    conn = _get_memory_conn()

    if not query.strip():
        # 列出最近沉淀的知识
        rows = conn.execute(
            "SELECT title, content, tags, confidence, created_at FROM knowledge_nuggets "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
            (uid,)
        ).fetchall()
        conn.close()
        if not rows:
            return "暂无沉淀的知识"
        parts = ["📚 最近沉淀的知识："]
        for r in rows:
            parts.append(f"  • [{r['title']}] {r['content'][:60]}... (置信度 {r['confidence']:.0%})")
        return "\n".join(parts)

    # SQLite 分词匹配：拆为单字/词，每个词必须命中 title+content+tags 之一
    # 避免整词 LIKE 的"方向反了"问题（"矿山修复期限" 不包含 "修复期限"）
    words = [w for w in query if '\u4e00' <= w <= '\u9fff' or w.isalpha()]
    if not words:
        words = [query]
    
    conditions = []
    params = [uid]
    for w in words:
        like_w = f"%{w}%"
        conditions.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
        params.extend([like_w, like_w, like_w])
    
    where_clause = " OR ".join(conditions)
    sqlite_rows = conn.execute(
        f"SELECT id, title, content, tags, confidence FROM knowledge_nuggets "
        f"WHERE user_id=? AND ({where_clause}) "
        f"ORDER BY confidence DESC LIMIT 10",
        params
    ).fetchall()

    # ChromaDB 语义检索
    emb = _get_task_embedding(query)
    chroma_results = []
    if emb:
        try:
            collection = _get_knowledge_collection()
            results = collection.query(
                query_embeddings=[emb],
                n_results=top_k
            )
            if results["ids"] and results["ids"][0]:
                for i, nugget_id in enumerate(results["ids"][0]):
                    doc = results["documents"][0][i] if results["documents"] else ""
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    dist = results["distances"][0][i] if results["distances"] else 1.0
                    sim = 1.0 - dist if results.get("distances") else 0.5
                    chroma_results.append({
                        "id": nugget_id.replace("nugget_", ""),
                        "title": meta.get("title", ""),
                        "content": doc,
                        "similarity": sim,
                        "source": "semantic"
                    })
        except Exception:
            pass

    # 合并结果：SQLite 精确匹配 + ChromaDB 语义匹配
    seen_ids = set()
    merged = []

    # 先加 ChromaDB 语义结果（质量更高）
    for cr in chroma_results:
        if cr["id"] not in seen_ids and cr["similarity"] > 0.5:
            seen_ids.add(cr["id"])
            merged.append(cr)

    # 再加 SQLite 模糊匹配（补漏）
    for row in sqlite_rows:
        rid = str(row["id"])
        if rid not in seen_ids:
            seen_ids.add(rid)
            merged.append({
                "id": rid,
                "title": row["title"],
                "content": row["content"],
                "confidence": row["confidence"],
                "source": "keyword"
            })

    if not merged:
        conn.close()
        return f"知识库中没有关于「{query}」的记录"

    parts = [f"🧠 知识库中关于「{query}」的记录："]
    for item in merged[:top_k]:
        src_tag = "🔍语义" if item.get("source") == "semantic" else "📎关键词"
        conf = item.get("confidence", item.get("similarity", 0.5))
        parts.append(
            f"\n--- {src_tag} | {item['title']} | 置信度 {conf:.0%} ---\n"
            f"{item['content']}"
        )

    conn.close()
    return "\n".join(parts)


# ==================== 9. 网络工具 (3个) ====================

@tool
def search_web(query: str) -> str:
    """联网搜索，基于 Tavily Search API。返回搜索结果摘要。"""
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "错误：未配置 TAVILY_API_KEY 环境变量。"
        tool = TavilySearchResults(max_results=5, api_key=api_key)
        results = tool.invoke(query)
        if not results:
            return "未找到相关结果。"
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("content", "")[:200]
            url = r.get("url", "")
            lines.append(f"{i}. {title}\n   {url}")
        return "\n\n".join(lines)
    except ImportError:
        return "错误：未安装 langchain_community，请运行 pip install langchain-community tavily-python"
    except Exception as e:
        return f"搜索出错：{e}"


@tool
def get_weather(city: str) -> str:
    """查询城市实时天气（通过 wttr.in，无需 API Key）。"""
    import urllib.request
    import urllib.parse
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded}?format=j1&lang=zh"
        req = urllib.request.Request(url, headers={"User-Agent": "curl"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        current = data["current_condition"][0]
        descs = current.get("lang_zh", current.get("weatherDesc", [{"value": "未知"}]))
        desc = descs[0]["value"] if descs else "未知"
        temp_c = current["temp_C"]
        feels = current.get("FeelsLikeC", temp_c)
        humidity = current.get("humidity", "N/A")
        wind = current.get("windspeedKmph", "N/A")
        wind_dir = current.get("winddir16Point", "")
        today = data["weather"][0]
        high, low = today["maxtempC"], today["mintempC"]
        return (
            f"城市：{city}\n"
            f"天气：{desc}\n"
            f"温度：{temp_c}°C（体感 {feels}°C）\n"
            f"最高/最低：{high}°C / {low}°C\n"
            f"湿度：{humidity}%\n"
            f"风速：{wind} km/h {wind_dir}\n"
            f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        return f"天气查询失败: {e}。请检查城市名是否正确（如 周口、北京）。"


@tool
def get_news(category: str = "科技") -> str:
    """获取最新新闻和资讯。通过联网搜索获取实时结果。"""
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return f"新闻功能需要配置 TAVILY_API_KEY。你想查看的类别: {category}"
        tool = TavilySearchResults(max_results=5, api_key=api_key)
        results = tool.invoke(f"{category} 最新新闻动态")
        if not results:
            return f"未找到 {category} 相关的最新新闻。"
        lines = [f"【{category} 最新资讯】"]
        for i, r in enumerate(results, 1):
            title = r.get("content", "")[:200]
            url = r.get("url", "")
            lines.append(f"{i}. {title}\n   {url}")
        return "\n\n".join(lines)
    except ImportError:
        return "新闻搜索需要安装 tavily-python：pip install tavily-python"
    except Exception as e:
        return f"新闻获取失败：{e}"
@tool
def get_file_metadata(filename: str, question: str = "") -> str:
    """获取文档的元数据信息。"""
    import sqlite3
    import re

    db_path = os.path.join(os.getenv("DB_DIR", os.path.join(_TOOLS_BASE_DIR, "data")), "knowhub.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        clean_name = re.sub(r'[《》]', '', filename)
        cursor.execute("""
            SELECT filename, file_size, page_count, article_count, word_count, chunk_count
            FROM user_files
            WHERE filename LIKE ? OR filename LIKE ? OR filename LIKE ?
            ORDER BY id DESC
            LIMIT 1
        """, (f"%{clean_name}%", f"%{clean_name}法%", f"%{clean_name}条例%"))

        row = cursor.fetchone()
    finally:
        conn.close()
    
    if not row:
        return f"未找到「{filename}」这个文件"
    
    # 根据问题类型返回不同内容
    if "条" in question:
        return f"《{row['filename']}》共有 **{row['article_count']} 条**。"
    elif "页" in question:
        return f"《{row['filename']}》共 {row['page_count']} 页。"
    elif "大" in question or "大小" in question:
        return f"《{row['filename']}》文件大小约 {row['file_size']} KB。"
    else:
        return f"《{row['filename']}》共有 {row['article_count']} 条，{row['page_count']} 页，{row['file_size']} KB。"

# ==================== 10. 定时任务与邮件工具 ====================

# 定时任务存储文件
SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "scheduled_tasks.json")
_scheduler_running = False


def _load_tasks() -> list:
    """从 JSON 加载定时任务"""
    if not os.path.exists(SCHEDULE_FILE):
        return []
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(tasks: list):
    """保存定时任务到 JSON（原子写入防损坏）"""
    import tempfile
    dir_name = os.path.dirname(SCHEDULE_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, SCHEDULE_FILE)  # 原子替换
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _parse_time(time_str: str) -> str:
    """解析时间字符串，统一返回 'YYYY-MM-DD HH:MM' 格式"""
    if ":" in time_str and "-" not in time_str:
        # 只有时分，默认今天
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today} {time_str}"
    return time_str


def _get_next_id(tasks: list) -> int:
    """获取下一个任务ID（自增）"""
    if not tasks:
        return 1
    return max(t.get("id", 0) for t in tasks) + 1


@tool
def schedule_task(query: str, time_str: str, repeat: str = "once") -> str:
    """
    创建或修改定时任务。time_str 格式为 'HH:MM'(默认今天) 或 'YYYY-MM-DD HH:MM'。
    repeat: once(一次性) / daily(每天) / weekly(每周)。
    示例: schedule_task('搜索最新政策', '09:00', 'daily')
    """
    tasks = _load_tasks()
    exec_time = _parse_time(time_str)

    task = {
        "id": _get_next_id(tasks),
        "query": query,
        "time": exec_time,
        "repeat": repeat,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_run": None,
    }
    tasks.append(task)
    _save_tasks(tasks)

    repeat_label = {"once": "一次性", "daily": "每天", "weekly": "每周"}.get(repeat, repeat)
    return f"[OK] 已创建定时任务 #{task['id']}：{repeat_label} {exec_time} — {query}"


@tool
def list_scheduled_tasks() -> str:
    """列出所有已创建的定时任务"""
    tasks = _load_tasks()
    if not tasks:
        return "暂无定时任务。"

    lines = [f"共 {len(tasks)} 个定时任务："]
    repeat_label = {"once": "一次性", "daily": "每天", "weekly": "每周"}
    for t in tasks:
        rl = repeat_label.get(t.get("repeat", "once"), t.get("repeat", "once"))
        last = f"，上次执行: {t['last_run']}" if t.get("last_run") else ""
        lines.append(f"  #{t['id']} {rl} {t['time']} — {t['query']}{last}")
    return "\n".join(lines)


@tool
def cancel_scheduled_task(task_id: int) -> str:
    """取消指定编号的定时任务。编号通过 list_scheduled_tasks 查看。"""
    tasks = _load_tasks()
    target = next((t for t in tasks if t["id"] == task_id), None)
    if not target:
        return f"[ERR] 未找到编号为 {task_id} 的定时任务。"

    tasks.remove(target)
    _save_tasks(tasks)
    return f"[OK] 已取消定时任务 #{task_id}：{target['query']}"


@tool
def check_due_tasks() -> str:
    """检查是否有到期的定时任务，返回需要执行的任务列表。Agent 调用后可自主执行到期任务。"""
    tasks = _load_tasks()
    now = datetime.now()
    due = []

    for t in tasks:
        try:
            exec_dt = datetime.strptime(t["time"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if exec_dt <= now:
            if t["repeat"] == "once":
                # 一次性任务：标记已执行并移除
                t["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                due.append(t)
            elif t["repeat"] == "daily":
                # 每天任务：执行后顺延到明天
                t["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                t["time"] = (exec_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
                due.append(t)
            elif t["repeat"] == "weekly":
                t["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                t["time"] = (exec_dt + timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
                due.append(t)

    # 移除已执行的一次性任务
    tasks = [t for t in tasks if t["repeat"] != "once" or t["id"] not in {d["id"] for d in due}]
    _save_tasks(tasks)

    if not due:
        return "暂无到期任务。"

    lines = [f"📋 有 {len(due)} 个任务到期待执行："]
    for t in due:
        lines.append(f"  #{t['id']} {t['query']}")
    return "\n".join(lines)


# SMTP 配置（从环境变量读取）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    发送邮件。需先在 .env 中配置 SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD。
    QQ邮箱: SMTP_HOST=smtp.qq.com, SMTP_PORT=587，密码填授权码（非QQ密码）。
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        return "[ERR] 未配置 SMTP，请在 .env 中设置 SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD。QQ邮箱需使用授权码。\n参考: https://service.mail.qq.com/detail/0/428"

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return f"[OK] 邮件已发送 → {to} 主题：{subject}"
    except smtplib.SMTPAuthenticationError:
        return "[ERR] SMTP 认证失败，请检查 SMTP_USER 和 SMTP_PASSWORD 是否正确。QQ邮箱需使用授权码。"
    except Exception as e:
        return f"[ERR] 邮件发送失败: {str(e)}"

# ==================== 汇总 ====================
ALL_TOOLS = [
    # 文档 (8)
    search_documents, search_with_rerank, list_all_documents,
    get_document_info, get_chunk_statistics,
    # 时间 (6)
    get_current_time, get_current_date, get_weekday,
    calculate_date_days, days_between_dates, get_timestamp,
    # 文本 (5)
    translate, polish_writing, summarize_text, extract_keywords,
    correct_grammar,
    # 文件 (3)
    read_file, write_to_file, list_directory,
    # 记忆 (5)
    save_to_memory, recall_from_memory, forget_from_memory,
    clear_memory, update_conversation_summary,
    # 情节记忆 (2)
    recall_episodes, record_episode,
    # 对话归档 (1)
    search_history,
    # 知识沉淀 (1)
    recall_knowledge,
    # 网络 (3)
    search_web, get_weather, get_news,
    get_file_metadata,
    # 定时任务与邮件 (5)
    schedule_task, list_scheduled_tasks, cancel_scheduled_task,
    check_due_tasks, send_email,
]

print(f"[OK] tools.py 加载完成，共 {len(ALL_TOOLS)} 个工具")
