import os
import re
import json
import pickle
import shutil
import hashlib
import traceback
import warnings
import math
from collections import Counter
from typing import List
from dotenv import load_dotenv
import dashscope
import jieba

# Redis 可选导入
try:
    import redis
except ImportError:
    redis = None

from dashscope import TextEmbedding

# 加载环境变量
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from hierarchical_splitter import HierarchicalTextSplitter
from skills.clarify_skill import ClarifySkill

warnings.filterwarnings("ignore")
# ==================== 配置 ====================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("❌ 请设置环境变量 DASHSCOPE_API_KEY（参考 .env.example）")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3.7-plus"

DOCUMENTS_DIR = "./documents"
VECTOR_DB_DIR = "./vector_db"
# ==================== 全局变量（供 agent.py 调用）====================
hybrid_retriever = None
reranker = None

dashscope.api_key = DASHSCOPE_API_KEY
# ==================== Skill 开关 ====================
USE_QUERY_OPTIMIZER = True   # Query 优化 Skill（已内嵌在检索逻辑中）
USE_SOURCE_RANKER = True     # 来源权威性排序 Skill
# ==================== Redis 缓存（可选） ====================
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_TTL = 3600

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()
    print("✅ Redis 连接成功，缓存已启用")
except Exception as e:
    print(f"⚠️ Redis 连接失败: {e}，将不使用缓存")
    redis_client = None


def _cache_key(question: str) -> str:
    normalized = question.strip().lower()
    return f"qa:cache:{hashlib.md5(normalized.encode()).hexdigest()}"


# ==================== Embedding 类 ====================
class DashScopeEmbeddings:
    """阿里云 DashScope Embedding（text-embedding-v4）"""

    def __init__(self, model="text-embedding-v4"):
        self.model = model

    def embed_documents(self, texts):
        """批量生成向量，每批最多 10 条"""
        batch_size = 10
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                resp = TextEmbedding.call(model=self.model, input=batch)
                if resp.status_code == 200:
                    for item in resp.output["embeddings"]:
                        all_embeddings.append(item["embedding"])
                else:
                    print(f"Embedding API 错误: code={resp.status_code}, message={resp.message}")
                    return []
            except Exception as e:
                print(f"Embedding 调用失败: {e}")
                traceback.print_exc()
                return []
        return all_embeddings

    def embed_query(self, text):
        """单条查询向量"""
        try:
            resp = TextEmbedding.call(model=self.model, input=[text])
            if resp.status_code == 200:
                return resp.output["embeddings"][0]["embedding"]
            else:
                print(f"Query Embedding 错误: code={resp.status_code}, message={resp.message}")
                return [0.0] * 1024
        except Exception as e:
            print(f"Query Embedding 异常: {e}")
            traceback.print_exc()
            return [0.0] * 1024


# ==================== BM25 检索器 ====================
class BM25Retriever:
    """BM25 关键词检索器"""

    def __init__(self, chunks: List[Document], k1=1.5, b=0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self.doc_words = [self._tokenize(c.page_content) for c in chunks]
        self.doc_lengths = [len(w) for w in self.doc_words]
        self.avg_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        self.idf = self._compute_idf()

    def _tokenize(self, text: str) -> List[str]:
        words = jieba.lcut(text)
        return [w for w in words if len(w) >= 2]

    def _compute_idf(self):
        doc_count = len(self.doc_words)
        word_doc_freq = Counter()
        for words in self.doc_words:
            for word in set(words):
                word_doc_freq[word] += 1
        return {
            word: math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1)
            for word, freq in word_doc_freq.items()
        }

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        query_words = self._tokenize(query)
        scores = []
        for idx, words in enumerate(self.doc_words):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            for word in query_words:
                if word not in self.idf:
                    continue
                word_freq = words.count(word)
                if word_freq == 0:
                    continue
                numerator = word_freq * (self.k1 + 1)
                denominator = word_freq + self.k1 * (1 - self.b + self.b * doc_len / self.avg_length)
                score += self.idf[word] * numerator / denominator
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [self.chunks[idx] for idx, score in scores[:k] if score > 0]


# ==================== 混合检索器 ====================
class HybridRetriever:
    """向量检索 + BM25 混合检索"""

    def __init__(self, vector_store, bm25_retriever):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        vector_docs = self.vector_store.similarity_search(query, k=k * 2)
        bm25_docs = self.bm25_retriever.similarity_search(query, k=k * 2)

        seen = set()
        merged = []
        for doc in vector_docs + bm25_docs:
            # 使用更长的文本片段和来源信息进行去重，避免误去重
            key = f"{doc.metadata.get('source', '')}:{doc.page_content[:300]}"
            if key not in seen:
                seen.add(key)
                merged.append(doc)
            if len(merged) >= k:
                break
        return merged


# ==================== BGE-Reranker 重排器 ====================
class BGEReranker:
    """BGE 重排模型 - 使用 base 版本"""

    def __init__(self, model_path="./bge_reranker_base"):
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        print(f"正在从本地路径加载重排模型: {self.model_path}...")
        try:
            from sentence_transformers import CrossEncoder
            abs_path = os.path.abspath(self.model_path)
            self.model = CrossEncoder(
                abs_path, device="cpu", trust_remote_code=True,
                model_kwargs={"low_cpu_mem_usage": True},
            )
            _ = self.model.predict([["预热", "预热"]], show_progress_bar=False)
            print("✅ 重排模型加载完成")
        except Exception as e:
            import traceback
            print(f"⚠️ 重排模型加载失败: {e}")
            traceback.print_exc()
            self.model = None

    def rerank(self, query: str, documents: List[Document], top_k: int = 4) -> List[Document]:
        if not documents:
            return []
        if self.model is None:
            print("  [重排] 模型未加载，使用原排序")
            return documents[:top_k]
        # 1. 简单问题跳过重排
        if len(query) < 10:
            return documents[:top_k]
        
        # 2. 只重排前 5 个
        candidates = documents[:5]
        try:
            pairs = [[query, d.page_content] for d in candidates]
            scores = self.model.predict(pairs, show_progress_bar=False)
            scores = list(scores)  # numpy → list
            doc_with_scores = list(zip(candidates, scores))
            doc_with_scores.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in doc_with_scores[:top_k]]
        except Exception as e:
            print(f"重排失败: {e}")
            import traceback; traceback.print_exc()
            return documents[:top_k]


# ==================== 1. 文档加载 ====================
def load_documents(directory: str):
    """加载目录下的所有文档（PDF + CIMD数据集）"""
    documents = []
    
    # 1. 加载原有 PDF/TXT/DOCX/MD 文档
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
                docs = loader.load()
                print(f"  [{filename}] {len(docs)} 页")
                for doc in docs:
                    doc.metadata["source"] = filename
                documents.extend(docs)
                print(f"  ✓ 加载PDF: {filename}")
            elif filename.endswith(".txt") or filename.endswith(".md"):
                loader = TextLoader(filepath, encoding="utf-8")
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = filename
                documents.extend(docs)
                print(f"  ✓ 加载文本: {filename}")
            elif filename.endswith(".docx"):
                loader = Docx2txtLoader(filepath)
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = filename
                documents.extend(docs)
                print(f"  ✓ 加载Word: {filename}")
        except Exception as e:
            print(f"  ✗ 加载失败 {filename}: {e}")
    
    # 2. 加载 CIMD 政策数据集
    cimd_path = "./CIMD/data/corpus/reference_governance/train.jsonl"
    if os.path.exists(cimd_path):
        print(f"\n📚 正在加载 CIMD 数据集...")
        cimd_docs = load_cimd_dataset(cimd_path, max_records=5000)
        documents.extend(cimd_docs)
        print(f"  ✓ 加载CIMD数据: {len(cimd_docs)} 条")
    else:
        print(f"\n⚠️ CIMD 数据集不存在: {cimd_path}")
    
    return documents

def load_cimd_dataset(file_path: str, max_records: int = 5000) -> List[Document]:
    """加载 CIMD 数据集"""
    import json
    from langchain.schema import Document
    
    documents = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_records:
                    break
                
                try:
                    data = json.loads(line)
                    title = data.get("title", "")
                    content = data.get("raw_chunk", "")
                    
                    if not content:
                        continue
                    
                    # 构建文档内容
                    full_content = f"【标题】{title}\n【正文】{content}"
                    
                    # 构建元数据
                    metadata = {
                        "source": "CIMD_policy",
                        "title": title,
                        "source_type": data.get("source_type", ""),
                        "original_time": data.get("original_time", "")
                    }
                    
                    doc = Document(page_content=full_content, metadata=metadata)
                    documents.append(doc)
                    
                except json.JSONDecodeError:
                    continue
                
                if (i + 1) % 1000 == 0:
                    print(f"    已加载 {i+1} 条...")
                    
    except Exception as e:
        print(f"  ✗ 加载CIMD失败: {e}")
    
    return documents
# ==================== 2. 智能分块（带缓存，只对新文件分块） ====================
CHUNKS_CACHE_FILE = "_chunks_cache.pkl"
CHUNKS_INDEX_FILE = "_chunked_files.json"


def _chunks_cache_path():
    return os.path.join(VECTOR_DB_DIR, CHUNKS_CACHE_FILE)


def _chunks_index_path():
    return os.path.join(VECTOR_DB_DIR, CHUNKS_INDEX_FILE)


def get_chunked_files() -> set:
    """读取已分块的文件列表"""
    path = _chunks_index_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_chunked_files(file_set: set):
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    with open(_chunks_index_path(), "w", encoding="utf-8") as f:
        json.dump(sorted(file_set), f, ensure_ascii=False, indent=2)


def load_cached_chunks() -> List[Document]:
    """从磁盘加载已缓存的 chunks"""
    path = _chunks_cache_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return []


def save_chunks_cache(chunks: List[Document]):
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    with open(_chunks_cache_path(), "wb") as f:
        pickle.dump(chunks, f)


def split_documents(documents: List[Document]) -> List[Document]:
    """对所有文档进行标题层级语义分块"""
    splitter = HierarchicalTextSplitter()
    chunks = splitter.split_documents(documents)
    print(f"切分成 {len(chunks)} 个文本块")
    return chunks


def chunk_only_new_files(all_files: set, directory: str,
                         existing_chunks: List[Document] = None) -> List[Document]:
    """
    只对新增的文件分块，与已有 chunks 合并返回。
    all_files: 当前 documents/ 中所有 PDF/TXT 文件名
    directory: documents 目录路径
    existing_chunks: 已缓存的 chunks（为 None 时从磁盘加载）
    """
    chunked_files = get_chunked_files()
    new_files = all_files - chunked_files

    if not new_files:
        # 没有新文件，直接从缓存加载
        cached = existing_chunks if existing_chunks is not None else load_cached_chunks()
        if cached:
            print(f"从缓存加载 {len(cached)} 个已有文本块（无需重新分块）")
            return cached
        # 缓存丢失，全量重建
        print("⚠️ 缓存丢失，重新全量分块...")

    # 有缓存就从缓存起步，否则从空列表起步
    chunks = list(existing_chunks) if existing_chunks else load_cached_chunks()
    if not chunks and not new_files:
        chunks = []

    if new_files:
        print(f"🆕 只对 {len(new_files)} 个新文件分块: {', '.join(sorted(new_files))}")
        new_docs = []
        for fname in sorted(new_files):
            filepath = os.path.join(directory, fname)
            try:
                if fname.endswith(".pdf"):
                    loader = PyPDFLoader(filepath)
                elif fname.endswith(".txt") or fname.endswith(".md"):
                    loader = TextLoader(filepath, encoding="utf-8")
                elif fname.endswith(".docx"):
                    loader = Docx2txtLoader(filepath)
                else:
                    continue
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = fname
                new_docs.extend(docs)
            except Exception as e:
                print(f"  ✗ 加载失败 {fname}: {e}")

        if new_docs:
            splitter = HierarchicalTextSplitter()
            new_chunks = splitter.split_documents(new_docs)
            print(f"  新分块: {len(new_chunks)} 个 → 合并后共 {len(chunks) + len(new_chunks)} 个块")
            chunks.extend(new_chunks)

        # 更新索引
        chunked_files |= new_files
        save_chunked_files(chunked_files)

    # 保存缓存
    save_chunks_cache(chunks)
    return chunks


# ==================== 3. 创建向量库 ====================
def create_vector_store(chunks: List[Document]):
    print("正在初始化 Embedding 模型...")
    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    print("正在生成向量并存储...")
    try:
        vector_store = Chroma.from_documents(
            documents=chunks, embedding=embeddings, persist_directory=VECTOR_DB_DIR
        )
        print(f"✅ 向量库已存储到 {VECTOR_DB_DIR}")
        return vector_store
    except Exception as e:
        print(f"创建向量库失败: {e}")
        traceback.print_exc()
        return None


# ==================== 4. 增量索引 ====================
INDEX_FILE = "indexed_files.json"


def _index_record_path():
    return os.path.join(VECTOR_DB_DIR, INDEX_FILE)


def get_indexed_files() -> set:
    if os.path.exists(_index_record_path()):
        with open(_index_record_path(), "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_indexed_files(file_set: set):
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    with open(_index_record_path(), "w", encoding="utf-8") as f:
        json.dump(sorted(file_set), f, ensure_ascii=False, indent=2)


def load_vector_store():
    print("加载已有向量库...")
    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    try:
        vector_store = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)
        print("✅ 向量库加载成功")
        return vector_store
    except Exception as e:
        print(f"加载向量库失败: {e}")
        traceback.print_exc()
        return None


def initialize_rag_components():
    """
    统一的 RAG 组件初始化函数
    返回: (vector_store, hybrid_retriever, reranker) 或 (None, None, None)
    """
    try:
        vector_store = load_vector_store()
        if vector_store is None:
            print("[WARN] 向量库为空，RAG 不可用")
            return None, None, None

        # 从向量库加载所有文档
        all_docs = []
        for collection_name in vector_store._client.list_collections():
            collection = vector_store._client.get_collection(collection_name)
            if collection.count() > 0:
                data = collection.get(include=["documents", "metadatas"])
                from langchain.schema import Document
                for doc, meta in zip(data["documents"], data["metadatas"]):
                    all_docs.append(Document(page_content=doc, metadata=meta))

        if not all_docs:
            print("[WARN] 向量库中没有文档")
            return None, None, None

        # 创建 BM25 检索器
        bm25_retriever = BM25Retriever(all_docs)

        # 创建混合检索器
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            bm25_retriever=bm25_retriever
        )

        # 加载重排模型
        try:
            reranker = BGEReranker(model_path="./bge_reranker_v2_m3")
        except Exception as e:
            print(f"[WARN] Reranker 加载失败: {e}")
            reranker = None

        print(f"[OK] RAG 初始化完成: {len(all_docs)} chunks")
        return vector_store, hybrid_retriever, reranker

    except Exception as e:
        print(f"[WARN] RAG 初始化失败: {e}")
        traceback.print_exc()
        return None, None, None


def add_new_documents_to_store(vector_store, new_chunks):
    if not new_chunks:
        return vector_store
    print(f"  正在为新文件生成 {len(new_chunks)} 个块的向量...")
    try:
        batch_size = 5000
        for i in range(0, len(new_chunks), batch_size):
            batch = new_chunks[i:i+batch_size]
            vector_store.add_documents(batch)
            print(f"  ✅ 批次 {i//batch_size+1}: 已写入 {len(batch)} 个块 ({i+1}-{min(i+batch_size, len(new_chunks))}/{len(new_chunks)})")
        print(f"  ✅ 全部 {len(new_chunks)} 个新块已追加到向量库")
        return vector_store
    except Exception as e:
        print(f"  ⚠️ 增量添加失败: {e}")
        traceback.print_exc()
        return None


# ==================== 5. 构建问答链 ====================
def build_qa_chain(vector_store, chunks):
    """构建带混合检索 + 重排 + 反向澄清 + Redis 缓存的 RAG 问答链"""
    
    global hybrid_retriever, reranker  # 👈 新增：声明要修改全局变量

    PROMPT_TEMPLATE = """你是知智，企业级智能知识助手。请根据以下参考资料回答用户问题。

【参考资料】
{context}

【用户问题】
{question}

【要求】
- 只根据参考资料回答，不确定就说"资料中没有相关信息"
- 引用具体的文档来源
- 用通俗语言解释专业术语
- 回答要完整，不要截断，不要省略

【回答】"""

    PROMPT = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])

    llm = ChatOpenAI(
        model=QWEN_MODEL,
        temperature=0.3,
        streaming=True,
        model_kwargs={"max_tokens": 1024},
        openai_api_key=DASHSCOPE_API_KEY,
        openai_api_base=QWEN_BASE_URL,
    )

    print("正在初始化 BM25 检索器...")
    bm25_retriever = BM25Retriever(chunks)

    print("正在初始化混合检索器...")
    hybrid_retriever = HybridRetriever(vector_store, bm25_retriever)  # 👈 赋值给全局变量

    print("正在初始化重排器(BGE-Reranker-v2-m3)...")
    reranker = BGEReranker(model_path="./bge_reranker_v2_m3")  # 👈 赋值给全局变量

    # ==================== 反向澄清（三层流水线：规则 → LLM消解 → 动态反问）====================
    clarify = ClarifySkill(llm=llm)

    # ==================== 主问答函数 ====================
    def qa_function(question: str) -> dict:
        try:
            # ---- 0. Redis 缓存 ----
            if redis_client:
                ck = _cache_key(question)
                cached = redis_client.get(ck)
                if cached:
                    print("\n💾 [缓存命中] 直接返回")
                    data = json.loads(cached)
                    return {"answer": data["answer"], "sources": data["sources"], "from_cache": True}
            else:
                ck = None
            # ---- 1. 检索（短查询自动扩展优化）----
            tokens = [w for w in jieba.lcut(question) if len(w) >= 2]
            if len(question.strip()) <= 4 or len(tokens) <= 1:
                print("\n🚀 [QueryOptimizer] 检测到短查询，正在优化...")
                from skills.query_optimizer import optimize_query
                candidates = optimize_query(question, llm)
                print(f"   扩展候选: {candidates}")
                all_docs = []
                for q in candidates:
                    all_docs.extend(hybrid_retriever.similarity_search(q, k=10))
                seen_keys = set()
                docs = []
                for d in all_docs:
                    key = d.page_content[:100]
                    if key not in seen_keys:
                        seen_keys.add(key)
                        docs.append(d)
                docs = docs[:40]
            else:
                docs = hybrid_retriever.similarity_search(question, k=30)

            if not docs:
                return {"answer": "资料中没有找到相关信息。", "sources": []}
            # ---- 2. 反向澄清（三层流水线：规则 → LLM消解 → 动态反问）----
            doc_names = sorted(set(
                c.metadata.get("source", "") for c in chunks if c.metadata.get("source")
            ))
            result = clarify.execute({
                "query": question, "doc_names": doc_names,
                "history": [],      # 当前未记录多轮历史，后续可扩展
                "enable_llm": True,
            })
            if result["needs_clarify"]:
                print(f"\n💡 [反向澄清] 检测到模糊问题，{result['method']}层触发，正在生成反问...")
                return {
                    "answer": f"🤔 {result['message']}",
                    "sources": [], "need_clarification": True,
                }
            # ---- 3. 源定向增强：问题提到具体文件 → boost 该文件 ----
            mentioned_source = None
            if doc_names:
                doc_short_names = [n.rsplit(".", 1)[0] for n in doc_names]
                for short_name in doc_short_names:
                    if short_name in question:
                        for fn in doc_names:
                            if fn.rsplit(".", 1)[0] == short_name:
                                mentioned_source = fn
                                break
                        break
                if mentioned_source:
                    print(f"  🎯 检测到指定文件: {mentioned_source}，定向增强检索...")
                    file_chunks = [c for c in chunks if c.metadata.get("source") == mentioned_source]
                    if file_chunks:
                        file_bm25 = BM25Retriever(file_chunks)
                        file_results = file_bm25.similarity_search(question, k=8)
                        existing_keys = {d.page_content[:100] for d in docs}
                        boosted = [
                            d for d in file_results
                            if d.page_content[:100] not in existing_keys
                        ]
                        if boosted:
                            docs = boosted + docs
                            print(f"  🎯 从 {mentioned_source} 补充了 {len(boosted)} 个定向结果")

            # ---- 4. 重排 ----
            print(f"🔄 正在对 {len(docs)} 个结果进行重排...")
            reranked_docs = reranker.rerank(question, docs, top_k=8)
            # ========== 👇 在这里加入 Source Ranker ==========
            if USE_SOURCE_RANKER:  # 需要在配置中定义这个开关
                from skills.source_ranker import rerank_by_authority
                reranked_docs = rerank_by_authority(reranked_docs)
                print("  📊 [SourceRanker] 已按权威性重排序")
            # ---- 5. 源多样性过滤 ----
            max_per_file = 2 if mentioned_source else 1
            diverse_docs = []
            file_counts: dict[str, int] = {}
            for doc in reranked_docs:
                src = doc.metadata.get("source", "")
                cnt = file_counts.get(src, 0)
                allowed = max_per_file if src == mentioned_source else 1
                if cnt < allowed:
                    diverse_docs.append(doc)
                    file_counts[src] = cnt + 1
                if len(diverse_docs) >= 3:
                    break
            reranked_docs = diverse_docs

            # ---- 6. 构建上下文 & LLM 生成 ----
            context_parts = []
            sources_set: set[str] = set()
            for i, doc in enumerate(reranked_docs):
                src = doc.metadata.get("source", "未知")
                section = doc.metadata.get("section_title", "")
                sources_set.add(src)
                header = f"【来源{i + 1}: {src}"
                if section:
                    header += f" | 章节: {section}"
                header += "】"
                context_parts.append(f"{header}\n{doc.page_content[:300]}")

            context = "\n".join(context_parts)
            formatted_prompt = PROMPT.format(context=context, question=question)
            print()  # 空行分隔
            answer = ""
            for chunk in llm.stream(formatted_prompt):
                token = chunk.content
                if token:
                    print(token, end="", flush=True)
                    answer += token
            print()  # 最终换行
            sources = sorted(sources_set)
            print(f"📊 输出长度: {len(answer)} 字符")

            # ---- 7. 存入缓存 ----
            if redis_client and ck:
                try:
                    redis_client.setex(
                        ck, CACHE_TTL,
                        json.dumps({"answer": answer, "sources": sources}, ensure_ascii=False),
                    )
                    print(f"💾 [已缓存] 有效期 {CACHE_TTL} 秒")
                except Exception as e:
                    print(f"⚠️ 缓存写入失败: {e}")

            return {"answer": answer, "sources": sources, "need_clarification": False}

        except Exception as e:
            print(f"❌ qa_function 内部错误: {e}")
            traceback.print_exc()
            return {"answer": f"系统错误: {e}", "sources": []}

    return qa_function


# ==================== 6. 交互问答 ====================
def interactive_qa(qa_func):
    print("\n" + "=" * 50)
    print("知智 KnowHub — 企业级智能知识助手（向量检索 + Qwen3.7-Plus）")
    print("输入 'exit' 退出，输入 'clear' 清屏")
    print("=" * 50 + "\n")
    print("📚 提示：你可以问文档里的具体内容，例如：")
    print("  - 'XX政策的主要内容是什么？'")
    print("  - '需要准备哪些材料？'")
    print()

    while True:
        try:
            question = input("📝 请提问: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if question.lower() == 'exit':
            print("再见！")
            break
        elif question.lower() == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            continue
        elif not question:
            continue

        print("🤔 思考中...")

        try:
            result = qa_func(question)
            print("\n✅ 回答:")
            print("-" * 40)
            if isinstance(result, dict):
                print(result.get("answer", str(result)))
                print("-" * 40)
                sources = result.get("sources", [])
                if sources:
                    print(f"📚 来源: {', '.join(sources)}")
            else:
                print(result)
                print("-" * 40)
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            traceback.print_exc()
            print()


# ==================== 7. 主流程 ====================
def main():
    if DASHSCOPE_API_KEY == "your-dashscope-api-key-here":
        print("❌ 请先设置 DASHSCOPE_API_KEY")
        return

    if not os.path.exists(DOCUMENTS_DIR):
        os.makedirs(DOCUMENTS_DIR)
        print(f"✅ 已创建 {DOCUMENTS_DIR} 文件夹，请放入 PDF/TXT 后重新运行")
        return

    files = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(('.pdf', '.txt', '.docx', '.md'))]
    if not files:
        print(f"📁 {DOCUMENTS_DIR} 文件夹为空，请放入 PDF、Word、Markdown 或 TXT 文档")
        return

    print(f"发现 {len(files)} 个文档: {', '.join(files)}\n")
    current_files = set(files)

    # ---- 检测增量 ----
    vector_db_exists = os.path.exists(VECTOR_DB_DIR) and os.listdir(VECTOR_DB_DIR)
    if vector_db_exists:
        indexed_files = get_indexed_files()
        new_files = current_files - indexed_files
        deleted_files = indexed_files - current_files
        if new_files:
            print(f"🆕 检测到 {len(new_files)} 个新文件: {', '.join(new_files)}")
        if deleted_files:
            print(f"🗑️  检测到 {len(deleted_files)} 个文件已删除")
    else:
        indexed_files, new_files = set(), current_files

    # ---- 加载 & 分块（只对新文件分块，已有文件的 chunks 从缓存加载）----
    chunks = chunk_only_new_files(current_files, DOCUMENTS_DIR)
    if not chunks:
        print("没有可用的文本块")
        return

    # ---- 向量库初始化 / 增量更新 ----
    if not vector_db_exists:
        print("\n开始构建向量库（首次）...")
        vector_store = create_vector_store(chunks)
        if vector_store is not None:
            save_indexed_files(current_files)
    else:
        vector_store = load_vector_store()
        if vector_store is None:
            print("❌ 加载失败，将重建向量库...")
            vector_store = create_vector_store(chunks)

        if new_files:
            new_chunks = [c for c in chunks if c.metadata.get("source") in new_files]
            print(f"\n📥 增量索引: 为新文件生成向量（{len(new_chunks)} 个块）...")
            updated = add_new_documents_to_store(vector_store, new_chunks)
            if updated is not None:
                save_indexed_files(current_files)
            else:
                print("⚠️ 增量失败，重建整个向量库...")
                shutil.rmtree(VECTOR_DB_DIR, ignore_errors=True)
                vector_store = create_vector_store(chunks)
                if vector_store is not None:
                    save_indexed_files(current_files)
        elif deleted_files:
            save_indexed_files(current_files)
        else:
            print("✅ 向量库已是最新，无需更新")

    if vector_store is None:
        print("❌ 向量库初始化失败，无法继续")
        return

    # ---- 启动 ----
    print("\n正在初始化 Qwen 模型...")
    qa_func = build_qa_chain(vector_store, chunks)
    print("\n✅ 系统就绪！")
    interactive_qa(qa_func)


if __name__ == "__main__":
    main()
