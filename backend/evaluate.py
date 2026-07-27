"""
MRR (A/B 对比：无重排 vs 有重排) + 幻觉率 评估脚本
利用 LLM-as-judge 自评，无需人工标注
"""
import time
import json
import os
import re
from dotenv import load_dotenv
import chunk

# 加载环境变量
load_dotenv()

from chunk import (
    BM25Retriever, HybridRetriever, BGEReranker,
    QWEN_MODEL, QWEN_BASE_URL, DOCUMENTS_DIR,
    chunk_only_new_files, create_vector_store, load_vector_store,
)
from langchain_openai import ChatOpenAI

# ==================== 配置 ====================
TOP_K = 10
API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    raise ValueError("❌ 请设置环境变量 DASHSCOPE_API_KEY")

TEST_QUERIES = [
    "电力公司出现重大安全隐患不报告会有什么法律后果？",
    "征信记录有误通过什么渠道可以申诉更正？",
    "企业节能审查没通过就擅自开工怎么处罚？",
    "广东如何推动区域性股权市场高质量发展？",
    "广东AI赋能科研专项方案的核心内容是什么？",
    "上海国际金融中心发展离岸金融有哪些行动方案？",
    "教育部发布的高考预警提醒考生注意什么？",
    "港车北上政策延长到哪一年？",
    "网络数据安全管理条例对企业的数据处理提出什么要求？",
    "稀土管理条例对稀土资源开采有什么管控要求？",
    "专利法实施细则对外观设计专利保护期限如何规定？",
    "互联网平台企业涉税信息报送规定要求平台报送哪些信息？",
    "节约用水条例对工业企业用水有什么定额要求？",
    "婚姻登记条例对跨省办理结婚登记有什么新规？",
    "退役军人安置条例对退役士兵就业有哪些扶持政策？",
    "医疗器械监督管理条例对医疗器械注册有什么分类管理？",
    "教学成果奖励条例对国家级教学成果奖的评选标准是什么？",
    "领事保护与协助条例对海外中国公民能提供什么帮助？",
    "计算机信息网络国际联网管理暂行规定对网络接入有什么要求？",
    "海洋观测预报管理条例对海洋灾害预警有什么规定？",
]


def init_retrievers():
    """初始化检索器（复用 chunk.py 的初始化逻辑）"""
    print("加载文档 & 分块...")
    files = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(('.pdf', '.txt'))]
    current_files = set(files)
    chunks = chunk_only_new_files(current_files, DOCUMENTS_DIR)
    if not chunks:
        raise RuntimeError("没有可用文档")

    print("加载/构建向量库...")
    vs = load_vector_store()
    if vs is None:
        vs = create_vector_store(chunks)

    hybrid = HybridRetriever(vs, BM25Retriever(chunks))
    reranker = BGEReranker(model_path="./bge_reranker_base")
    return hybrid, reranker, chunks


def init_llm(temperature=0):
    return ChatOpenAI(
        model=QWEN_MODEL,
        temperature=temperature,
        openai_api_key=API_KEY,
        openai_api_base=QWEN_BASE_URL,
    )


def judge_relevance(llm, query: str, doc, rank: int) -> bool:
    content = doc.page_content[:500]
    prompt = f"判断以下文档片段是否包含可以回答用户问题的信息。只回答 YES 或 NO。\n用户问题：{query}\n文档片段：\n{content}\n能回答吗？(YES/NO):"
    try:
        resp = llm.invoke(prompt).content.strip().upper()
        return resp.startswith("YES")
    except Exception as e:
        print(f"      ⚠️ rank={rank} 异常: {e}")
        return False


def compute_mrr(query: str, docs: list, judge) -> float:
    for rank, doc in enumerate(docs[:TOP_K], 1):
        if judge_relevance(judge, query, doc, rank):
            return 1.0 / rank
    return 0.0


def compute_hallucination(judge, answer: str, docs: list) -> dict:
    sentences = re.split(r'[。\n]+', answer)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
    if not sentences:
        return {"total": 0, "hallucinations": 0, "rate": 0.0, "sentences": []}

    ctx = "\n\n".join([d.page_content[:300] for d in docs[:5]])

    results = []
    for sent in sentences:
        prompt = (
            f"判断以下句子中的信息是否能在给定资料中找到事实依据。\n"
            f"资料：\n{ctx[:3000]}\n"
            f"待验证句子：{sent}\n"
            f"只回答 YES（有依据）或 NO（无依据/幻觉）:"
        )
        try:
            verdict = judge.invoke(prompt).content.strip().upper()
            is_hallu = verdict.startswith("NO")
            results.append({"sentence": sent[:80], "hallucination": is_hallu})
        except Exception as e:
            results.append({"sentence": sent[:80], "hallucination": None, "error": str(e)})

    hallu_count = sum(1 for r in results if r.get("hallucination") is True)
    return {
        "total": len(results),
        "hallucinations": hallu_count,
        "rate": hallu_count / len(results) if results else 0.0,
        "sentences": results,
    }


def main():
    print("=" * 70)
    print("MRR (无重排 vs 有重排 A/B 对比) + 幻觉率 评估")
    print("=" * 70)

    # 1. 初始化
    print("\n[1/3] 初始化...")
    hybrid, reranker, chunks = init_retrievers()
    judge = init_llm()
    llm = init_llm(temperature=0)

    # 2. 逐条评估
    mrr_no = []
    mrr_with = []
    hallu_results = []

    print(f"\n[2/3] 评估中... ({len(TEST_QUERIES)} 条 query)")
    print("-" * 70)

    for idx, query in enumerate(TEST_QUERIES):
        q_short = query[:30]
        print(f"\n[{idx+1:02d}] {q_short}...")

        docs = hybrid.similarity_search(query, k=TOP_K)
        mrr1 = compute_mrr(query, docs, judge)
        mrr_no.append(mrr1)

        reranked = reranker.rerank(query, docs[:TOP_K], top_k=TOP_K)
        mrr2 = compute_mrr(query, reranked, judge)
        mrr_with.append(mrr2)

        delta = mrr2 - mrr1
        print(f"    MRR: {mrr1:.4f} → {mrr2:.4f}  Δ={delta:+.4f}")

        # 端到端 QA + 幻觉
        ctx = "\n\n".join([d.page_content[:300] for d in reranked[:3]])
        answer = llm.invoke(f"基于资料用中文回答：\n资料：{ctx}\n问题：{query}").content
        hallu = compute_hallucination(judge, answer, reranked[:5])
        hallu_results.append({"query": query, "answer": answer[:200], "hallucination": hallu})
        if hallu["total"] > 0:
            print(f"    幻觉率: {hallu['rate']:.1%} ({hallu['hallucinations']}/{hallu['total']})")

    # 3. 汇总
    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)

    avg_no = sum(mrr_no) / len(mrr_no)
    avg_with = sum(mrr_with) / len(mrr_with)
    improvement = (avg_with - avg_no) / max(avg_no, 0.001) * 100

    print(f"\n📊 MRR (top-{TOP_K})：")
    print(f"  无重排:  {avg_no:.4f}")
    print(f"  有重排:  {avg_with:.4f}")
    print(f"  提升:    {improvement:+.1f}%")
    print(f"\n  明细：")
    print(f"  {'#':<4} {'查询':<32} {'无重排':<8} {'有重排':<8} {'Δ':<8}")
    for i in range(len(TEST_QUERIES)):
        print(f"  [{i+1:02d}] {TEST_QUERIES[i][:30]:<32} {mrr_no[i]:.4f}   {mrr_with[i]:.4f}   {mrr_with[i]-mrr_no[i]:+.4f}")

    rates = [h["hallucination"]["rate"] for h in hallu_results if h["hallucination"]["total"] > 0]
    if rates:
        avg_hallu = sum(rates) / len(rates)
        print(f"\n📊 幻觉率:")
        print(f"  平均: {avg_hallu:.1%}  最小: {min(rates):.1%}  最大: {max(rates):.1%}")
        print(f"\n  明细：")
        for i, h in enumerate(hallu_results):
            hr = h["hallucination"]
            if hr["total"] > 0:
                hallu_sents = [s["sentence"] for s in hr["sentences"] if s.get("hallucination")]
                print(f"  [{i+1:02d}] {hr['rate']:.1%} ({hr['hallucinations']}/{hr['total']})", end="")
                if hallu_sents:
                    print(f"  → {hallu_sents[0]}")
                else:
                    print()

    # 保存结果
    out_path = os.path.join(os.path.dirname(__file__), "output", "eval_result.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "mrr": {"no_rerank": avg_no, "with_rerank": avg_with, "improvement_pct": improvement,
                     "per_query": [{"query": TEST_QUERIES[i], "no": mrr_no[i], "with": mrr_with[i]} for i in range(len(mrr_no))]},
            "hallucination": {"avg_rate": avg_hallu, "per_query": hallu_results},
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 详细结果: {out_path}")


if __name__ == "__main__":
    main()
