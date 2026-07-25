import json
import os
from chunk import (
    load_documents, split_documents, create_vector_store,
    load_vector_store, build_qa_chain, DOCUMENTS_DIR, VECTOR_DB_DIR
)
from hierarchical_splitter import HierarchicalTextSplitter

# ==================== 配置 ====================
TEST_QUERIES_FILE = "test_queries.json"

# ==================== 评估函数 ====================
def evaluate_mrr_without_rerank(hybrid_retriever, test_queries):
    """无重排：直接使用混合检索结果"""
    reciprocal_ranks = []
    
    for test in test_queries:
        question = test["question"]
        expected_source = test["expected_source"]
        expected_keyword = test.get("expected_keyword", "")
        
        # 混合检索（返回更多结果）
        docs = hybrid_retriever.similarity_search(question, k=30)
        
        # 查找正确答案的排名（不经过重排）
        rank = None
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "")
            content = doc.page_content
            if expected_source in source:
                if expected_keyword:
                    if expected_keyword in content:
                        rank = i + 1
                        break
                else:
                    rank = i + 1
                    break
        
        if rank:
            reciprocal_ranks.append(1 / rank)
            print(f"   ✅ 命中排名: {rank}, RR: {1/rank:.4f}")
        else:
            reciprocal_ranks.append(0)
            print(f"   ❌ 未命中")
    
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
    return mrr, reciprocal_ranks

def evaluate_mrr_with_rerank(reranker, hybrid_retriever, test_queries):
    """有重排：混合检索 + 重排"""
    reciprocal_ranks = []
    
    for test in test_queries:
        question = test["question"]
        expected_source = test["expected_source"]
        expected_keyword = test.get("expected_keyword", "")
        
        # 混合检索
        docs = hybrid_retriever.similarity_search(question, k=30)
        
        # 重排
        reranked_docs = reranker.rerank(question, docs, top_k=30)
        
        # 查找正确答案的排名
        rank = None
        for i, doc in enumerate(reranked_docs):
            source = doc.metadata.get("source", "")
            content = doc.page_content
            if expected_source in source:
                if expected_keyword:
                    if expected_keyword in content:
                        rank = i + 1
                        break
                else:
                    rank = i + 1
                    break
        
        if rank:
            reciprocal_ranks.append(1 / rank)
            print(f"   ✅ 命中排名: {rank}, RR: {1/rank:.4f}")
        else:
            reciprocal_ranks.append(0)
            print(f"   ❌ 未命中")
    
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
    return mrr, reciprocal_ranks

# ==================== 主函数 ====================
def main():
    # 加载测试集
    with open(TEST_QUERIES_FILE, 'r', encoding='utf-8') as f:
        test_queries = json.load(f)
    
    print("="*60)
    print("初始化 RAG 系统...")
    print("="*60)
    
    # 加载文档
    documents = load_documents(DOCUMENTS_DIR)
    if not documents:
        print("❌ 没有找到文档")
        return
    
    # 分块
    splitter = HierarchicalTextSplitter()
    chunks = splitter.split_documents(documents)
    print(f"分块完成: {len(chunks)} 个块")
    
    # 加载向量库
    if os.path.exists(VECTOR_DB_DIR) and os.listdir(VECTOR_DB_DIR):
        from chunk import load_vector_store
        vector_store = load_vector_store()
    else:
        from chunk import create_vector_store
        vector_store = create_vector_store(chunks)
    
    if vector_store is None:
        print("❌ 向量库初始化失败")
        return
    
    # 初始化检索器
    from chunk import BM25Retriever, HybridRetriever, BGEReranker
    
    bm25_retriever = BM25Retriever(chunks)
    hybrid_retriever = HybridRetriever(vector_store, bm25_retriever)
    reranker = BGEReranker()
    
    print("\n" + "="*60)
    print("📊 开始 MRR 对比评估")
    print("="*60)
    
    # 场景1：无重排
    print("\n" + "-"*40)
    print("场景1: 纯混合检索（无重排）")
    print("-"*40)
    mrr_without, rr_list_without = evaluate_mrr_without_rerank(hybrid_retriever, test_queries)
    
    # 场景2：有重排
    print("\n" + "-"*40)
    print("场景2: 混合检索 + BGE重排")
    print("-"*40)
    mrr_with, rr_list_with = evaluate_mrr_with_rerank(reranker, hybrid_retriever, test_queries)
    
    # 输出对比结果
    print("\n" + "="*60)
    print("📊 对比结果")
    print("="*60)
    print(f"无重排 MRR: {mrr_without:.4f} ({mrr_without*100:.2f}%)")
    print(f"有重排 MRR: {mrr_with:.4f} ({mrr_with*100:.2f}%)")
    
    # 计算提升
    if mrr_without > 0:
        improvement = (mrr_with - mrr_without) / mrr_without * 100
        print(f"\n🚀 重排带来的 MRR 提升: {improvement:.2f}%")
    else:
        print("\n⚠️ 无法计算提升比例（基线 MRR 为 0)")
    
    # 详细对比表格
    print("\n" + "="*60)
    print("详细对比（每个问题的 RR 值）")
    print("="*60)
    print(f"{'问题':<30} {'无重排':<10} {'有重排':<10} {'提升':<10}")
    print("-"*60)
    for i, test in enumerate(test_queries):
        question_short = test['question'][:28] + ".." if len(test['question']) > 30 else test['question']
        rr_without = rr_list_without[i] if i < len(rr_list_without) else 0
        rr_with = rr_list_with[i] if i < len(rr_list_with) else 0
        diff = rr_with - rr_without
        print(f"{question_short:<30} {rr_without:<10.4f} {rr_with:<10.4f} {diff:+.4f}")
    
    # 命中率对比
    hit_without = sum(1 for r in rr_list_without if r > 0)
    hit_with = sum(1 for r in rr_list_with if r > 0)
    print("\n" + "="*60)
    print(f"无重排命中率: {hit_without}/{len(test_queries)} = {hit_without/len(test_queries)*100:.1f}%")
    print(f"有重排命中率: {hit_with}/{len(test_queries)} = {hit_with/len(test_queries)*100:.1f}%")

if __name__ == "__main__":
    main()