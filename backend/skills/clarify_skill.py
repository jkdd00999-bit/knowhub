"""
意图澄清 Skill
三层架构：快速判断(规则正则 <1ms) → 智能判断(LLM ~350ms) → 动态反问(LLM ~350ms)
评测数据：规则版 P=97.6% 单轮 / LLM版 P=83.3% 多轮
"""
import re
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# ============ 第一层：快速判断 — 规则正则 ============

# 明显的指代不明
VAGUE_REFERENT = [
    (r'那个|这个|这个文件|那个政策|那个规定|那个条款|那个办法',
     "指代", "您提到的具体是哪个文件或政策？"),
    (r'它|它们|那里|这里|其',
     "指代", "您问题中的指代不太明确，请说明具体指的是什么。"),
]

# 宽泛模式
BROAD_QUERIES = [
    (r'介绍一下|说说|讲一下|大概|基本|概述|简述',
     "宽泛", "您的问题比较宽泛，请问想了解具体哪方面？"),
    (r'有什么要求|需要什么|怎么办|怎么弄|怎么搞',
     "宽泛", "请问具体想问哪个事项的要求或流程？"),
    (r'^怎么',
     "宽泛", "请问想了解什么事项的办理方法？"),
    (r'^什么是',
     "宽泛", "请问想了解哪个概念或术语？"),
    (r'有哪些|有几条|有几项|第[一二三四五六七八九十]+条',
     "宽泛", "您的问题没有指明具体文件。"),
]

DOC_KEYWORDS = ["规定", "政策", "文件", "条", "款", "材料", "流程",
                "办理", "申请", "行政", "许可", "处罚", "条例",
                "什么", "如何", "怎么", "为什么", "哪些", "哪个", "多少"]

VAGUE_STANDALONE = {"介绍一下", "说说看", "讲一下", "怎么搞", "怎么办"}


def _fast_check(query: str, doc_names: list) -> dict:
    """
    规则正则第一层过滤，<1ms。
    返回:
      {"action": "pass"}                          — 明确不需澄清
      {"action": "clarify", "reply": "...", "reason": "..."}  — 明确需要且有固定回复
      {"action": "uncertain", "reason": "..."}    — 不确定，交给LLM
    """
    q = query.strip()

    # 1. 极短 / 纯闲聊
    if len(q) < 4:
        return {"action": "clarify", "reply": "您的问题比较简短，请详细描述您想了解的内容。",
                "reason": "极短查询"}
    if q in VAGUE_STANDALONE:
        return {"action": "clarify", "reply": "请问您想了解具体哪方面的内容？",
                "reason": "纯模糊词"}

    # 2. 文档名匹配 — query 提到已知文件 → 直接放行
    if doc_names:
        short_names = [n.rsplit(".", 1)[0] for n in doc_names]
        for name in short_names:
            if name in q:
                return {"action": "pass"}

    # 3. 明显指代不明
    for pattern, tag, reply in VAGUE_REFERENT:
        if re.search(pattern, q):
            return {"action": "clarify", "reply": reply, "reason": tag}

    # 4. 宽泛模式检测
    for pattern, tag, base_reply in BROAD_QUERIES:
        if re.search(pattern, q):
            if doc_names:
                short = [n.rsplit(".", 1)[0] for n in doc_names]
                doc_list = "、".join([f"《{n}》" for n in short[:8]])
                reply = f"{base_reply}\n当前资料库中有：{doc_list}。请问您想问哪个文件的内容？"
            else:
                reply = base_reply
            return {"action": "clarify", "reply": reply, "reason": tag}

    # 5. 缺少企业知识关键词 — 可能是闲聊
    if not any(kw in q for kw in DOC_KEYWORDS):
        return {"action": "uncertain", "reason": "缺少企业知识关键词"}

    return {"action": "pass"}


# ============ 第二层：智能判断 — LLM 消解 ============

DEEP_CHECK_MULTI_PROMPT = """你判断多轮对话中最新问题是否需要反问澄清。

规则：
1. 如果问题承接上文、指代词可在历史中消解 → 不需要澄清
2. 如果话题跳转、指代无法消解、过于宽泛、缺少对象 → 需要澄清

对话历史：
{history}
最新问题："{query}"

请按JSON输出：
{{"is_vague": true/false, "reason": "一句话说明为什么需要/不需要澄清"}}
只输出JSON。"""

DEEP_CHECK_SINGLE_PROMPT = """你判断一个独立的用户问题是否过于模糊，需要反问澄清。

规则：
- 如果问题明确了主语/对象/文件名/具体事项 → 不需要澄清（即使口语化）
- 如果问题缺少对象、纯指代、过于宽泛 → 需要澄清

判断标准：一个问题如果能让你立刻知道用户想问哪个领域、哪种文档、哪类事项，就不模糊。
例如：
- "电站大坝不安全了该怎么办" → 不模糊（电站+大坝+不安全，对象完整）
- "石油公司管道的所有权归属怎么认定" → 不模糊（对象完整）
- "怎么办" → 模糊（无对象）
- "有什么要求" → 模糊（无对象）
- "相关规定在哪" → 模糊（无对象）

问题："{query}"

请按JSON输出：
{{"is_vague": true/false, "reason": "一句话说明为什么需要/不需要澄清"}}
只输出JSON。"""


def _deep_check(query: str, history: list, llm) -> dict:
    """
    LLM 判断问题是否模糊，~350ms。
    history: [(user_query, system_reply), ...]
    返回: {"is_vague": bool, "reason": str}
    """
    if history:
        conv = "\n".join(
            f"第{i+1}轮 用户：{q}\n第{i+1}轮 系统：{a}"
            for i, (q, a) in enumerate(history)
        )
        prompt = DEEP_CHECK_MULTI_PROMPT.format(history=conv, query=query)
    else:
        prompt = DEEP_CHECK_SINGLE_PROMPT.format(query=query)
    try:
        r = llm.invoke([HumanMessage(content=prompt)])
        import json
        content = r.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except:
        pass
    return {"is_vague": False, "reason": "LLM解析失败，按不模糊处理"}


# ============ 第三层：动态反问 — 候选推荐生成 ============

INQUIRY_PROMPT = """用户问题："{query}"
判断原因：{reason}
{doc_hint}

请生成一个友好的反问，帮助用户明确ta想问的具体内容。

要求：
1. 指出问题模糊在哪里（缺少对象/指代不明/过于宽泛等）
2. 如果资料库有文档，从中推荐2-3个最相关的文件名称，引导用户选择
3. 给出2-3个具体化的示例问法，帮助用户表达意图
4. 语气专业但友好，先说问题再给建议
5. 只输出反问内容，不要解释

示例输出：
"您的问题没有指明具体文件。当前资料库中有《电力安全工作规程》《招标投标法》《安全生产许可证条例》，请问您想了解哪个文件的内容？例如：1) 电力安全工作规程中有哪些高处作业要求？2) 招标投标法中邀请招标的适用条件是什么？"
"""


def _generate_inquiry(query: str, doc_names: list, reason: str, llm) -> str:
    """
    基于文档列表生成带候选推荐的自然反问，~350ms。
    """
    doc_hint = ""
    if doc_names:
        short = [n.rsplit(".", 1)[0] for n in doc_names[:10]]
        doc_hint = f"资料库中有以下文件：{'、'.join([f'《{n}》' for n in short])}。"

    prompt = INQUIRY_PROMPT.format(query=query, reason=reason, doc_hint=doc_hint)
    try:
        r = llm.invoke([HumanMessage(content=prompt)])
        return r.content.strip()
    except:
        # 兜底：基于文档列表的简单反问
        if doc_names:
            short = [n.rsplit(".", 1)[0] for n in doc_names[:5]]
            docs = "、".join([f"《{n}》" for n in short])
            return f"您的问题不太明确。当前资料库中有：{docs}。请问您想问哪个文件的具体内容？"
        return "您的问题不太明确，请补充详细信息。"


# ============ Skill 入口 ============

class ClarifySkill:
    """
    意图澄清 Skill — 三级流水线。

    输入: {
        "query": str,
        "doc_names": [str],        # 资料库文件名列表
        "history": [(q, a), ...],  # 多轮对话历史
        "enable_llm": bool         # 是否启用 LLM 第二/三层
    }
    输出: {
        "needs_clarify": bool,
        "message": str | None,     # 反问内容
        "method": "rule" | "llm"   # 实际走到的层级
    }
    """
    name = "clarify"
    description = "模糊问题意图澄清：规则正则快速判断 + LLM深层消解 + 动态候选推荐反问"

    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(
            model="qwen-turbo", temperature=0,
            api_key="sk-6c50a5e024c5403588e4e228f56cf6ea",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def execute(self, input: dict) -> dict:
        query = input["query"]
        doc_names = input.get("doc_names", [])
        history = input.get("history", [])
        enable_llm = input.get("enable_llm", False)

        # 第一层：快速判断
        fast = _fast_check(query, doc_names)

        # 规则放行 → 如果启用 LLM，再深判一次兜底（防止关键词白名单误放）
        if fast["action"] == "pass":
            if not enable_llm:
                return {"needs_clarify": False, "message": None, "method": "rule"}
            deep = _deep_check(query, history, self.llm)
            if deep["is_vague"]:
                reply = _generate_inquiry(query, doc_names, deep.get("reason", "问题不够明确"), self.llm)
                return {"needs_clarify": True, "message": reply, "method": "llm"}
            return {"needs_clarify": False, "message": None, "method": "llm"}

        # 未启用 LLM → 规则直接判（clarify / uncertain 路径）
        if not enable_llm:
            reply = fast.get("reply", "您的问题不太明确，请补充详细信息。")
            return {"needs_clarify": True, "message": reply, "method": "rule"}

        # 第二层：LLM 深判（支持单轮 + 多轮）
        deep = _deep_check(query, history, self.llm)
        if not deep["is_vague"]:
            return {"needs_clarify": False, "message": None, "method": "llm"}

        # 第三层：动态反问
        reason = deep.get("reason", fast.get("reason", "问题不够明确"))
        reply = _generate_inquiry(query, doc_names, reason, self.llm)
        return {"needs_clarify": True, "message": reply, "method": "llm"}
