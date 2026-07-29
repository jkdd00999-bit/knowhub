# skills/query_optimizer.py
import json
import re
from typing import List

# Query 优化专用 Prompt
OPTIMIZER_PROMPT = """你是一个查询扩展助手。用户输入可能简短、模糊或缺少关键词。
请根据用户输入,推测其最可能的完整查询意图,输出最多3个候选关键词,以JSON数组形式返回。

规则：
- 输出仅包含JSON数组,不要有其他解释。
- 如果输入已经完整（长度>5且包含明确主体),只需返回包含原词的数组。
- 考虑常见的同义词、上下义词、典型企业知识用语。

示例1:
输入："级"
输出：["企业级", "国家级", "高级"]

示例2:
输入："补助"
输出：["投资补助", "财政补贴", "资金补助"]

示例3:
输入："电网安全"
输出：["电网安全", "电力系统安全", "电力安全规定"]

现在请输出：
"""

def optimize_query(raw_query: str, llm) -> List[str]:
    """
    调用大模型优化用户查询
    raw_query: 用户原始输入
    llm: 你的 ChatOpenAI 实例（由外部传入）
    返回: 候选查询列表（包含原词）
    """
    # 如果输入已经足够长（>8字符）且包含多个词，可能不需要优化
    import jieba
    tokens = [w for w in jieba.lcut(raw_query) if len(w) >= 2]
    if len(raw_query) > 8 and len(tokens) >= 2:
        return [raw_query]

    try:
        response = llm.invoke(OPTIMIZER_PROMPT + f"\n输入：\"{raw_query}\"\n输出：")
        content = response.content.strip()
        # 用正则提取 JSON 数组（非贪婪 + 不嵌套）
        match = re.search(r'\[[^\[\]]*\]', content)
        if match:
            candidates = json.loads(match.group())
            # 去重、限制3个、原词优先
            candidates = list(dict.fromkeys(candidates))  # 有序去重
            if raw_query not in candidates:
                candidates.insert(0, raw_query)
            return candidates[:3]
        else:
            return [raw_query]
    except Exception as e:
        print(f"[QueryOptimizer] 错误: {e}")
        return [raw_query]