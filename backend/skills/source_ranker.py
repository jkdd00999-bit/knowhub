# skills/source_ranker.py
from typing import List
from langchain.schema import Document


def rerank_by_authority(documents: List[Document]) -> List[Document]:
    """
    按文档来源的权威性进行重排序
    权威性高的文档排在前面
    """
    if not documents:
        return documents
    
    # 权威性分数配置
    def get_score(source: str) -> int:
        source_lower = source.lower()
        if "国务院" in source or "国家发展改革委" in source or "国家能源局" in source:
            return 100
        elif "省" in source or "北京" in source or "上海" in source or "广东" in source:
            return 80
        elif "市" in source:
            return 60
        elif "cimd" in source_lower:
            return 50
        else:
            return 40
    
    # 为每个文档计算分数
    scored_docs = []
    for doc in documents:
        source = doc.metadata.get("source", "")
        score = get_score(source)
        scored_docs.append((doc, score))
    
    # 按分数降序排序（分数高的在前）
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    # 返回排序后的文档列表
    return [doc for doc, _ in scored_docs]