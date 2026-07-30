import re
from typing import List, Dict, Set
from collections import Counter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


class HierarchicalTextSplitter:
    """
    基于标题层级的语义分块器
    兼容：红头文件、政策条文、学术论文
    """

    def __init__(self):
        # ---- 标题层级正则 ----
        self.title_patterns = {
            1: r'^(第[一二三四五六七八九十百千零\d]+章|第一章|第二章|第三章|第四章|第五章|第六章|第七章|第八章|第九章|第十章)',
            2: r'^(第[一二三四五六七八九十百千零\d]+条|第一条|第二条|第三条|第四条|第五条|第六条|第七条|第八条|第九条|第十条)',
            3: r'^[一二三四五六七八九十]+[、]',
            4: r'^\d+(?:\.\d+)*[\s\.]+\w+',        # "1 Introduction" "2.1. Conv Layer"
            5: r'^[IVX]+\.\s+\w+',               # "I. Introduction"
        }

        # ---- 学术论文独立标题 ----
        self.academic_section_titles = {
            "abstract", "introduction", "conclusion", "conclusions",
            "acknowledgments", "acknowledgement", "references",
            "keywords", "appendix", "appendices",
            "motivation", "background", "discussion",
            "future work", "limitations", "method", "methods",
            "experiments", "experiment", "results", "result",
            "related work", "preliminaries",
        }

        # ---- 列表项（不切分）----
        self.list_item_patterns = [
            r'^[（(][一二三四五六七八九十]+[）)]',
            r'^[（(]\d+[）)]',
            r'^\d+[\)\.]\s',
        ]

        # ---- 误判排除（非标题行）----
        self.false_title_patterns = re.compile(
            r'@|'                              # email
            r'et\s+al|'                        # "et al."
            r'journal\s+of|'                   # journal name
            r'issn\s|'                         # ISSN
            r'vol\.?\s*\d+|'                    # "Vol. 2"
            r'pp\.?\s*\d+|'                     # "pp. 739"
            r'https?://|'                       # URL
            r'corresponding\s+author|'
            r'\bdoi\b',                         # DOI
            re.IGNORECASE
        )

        # ---- 兜底切分器 ----
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3072,
            chunk_overlap=512,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
        )

    # ==================== 页眉页脚检测 ====================

    def _is_page_number(self, line: str) -> bool:
        line = line.strip()
        if not line:
            return False
        for pat in [
            r'^\d+$', r'^[-—]\s*\d+\s*[-—]$', r'^\d+\s*[/共]\s*\d+',
            r'^第?\d+\s*页\s*[/共]\s*\d+\s*页?', r'^Page\s+\d+\s+of\s+\d+',
        ]:
            if re.match(pat, line, re.IGNORECASE):
                return True
        return False

    def _build_repeating_line_filter(self, text: str) -> Set[str]:
        lines = [l.strip() for l in text.split('\n')]
        lines = [l for l in lines if l and len(l) > 1]
        line_counts = Counter(lines)
        total_pages_estimate = max(1, len(lines) // 40)
        threshold = max(3, total_pages_estimate // 3)
        repeating = {l for l, c in line_counts.items() if c >= threshold}
        if repeating:
            print(f"  检测到 {len(repeating)} 行重复页眉/页脚（出现 >= {threshold} 次）")
        return repeating

    def _is_header_or_footer(self, line: str, repeating_lines: Set[str] = None) -> bool:
        line = line.strip()
        if not line:
            return False
        if self._is_page_number(line):
            return True
        if repeating_lines and line in repeating_lines:
            return True
        return False

    # ==================== 结构解析 ====================

    def extract_structure(self, text: str, repeating_lines: Set[str] = None) -> List[Dict]:
        lines = text.split('\n')
        structure = []
        current_section = {"level": 0, "title": "", "content": ""}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if self._is_header_or_footer(line, repeating_lines):
                continue

            matched_level = self._match_title_level(line)

            # 列表项不切分
            is_list_item = False
            if not matched_level:
                for pat in self.list_item_patterns:
                    if re.match(pat, line):
                        is_list_item = True
                        break

            if matched_level > 0 and not is_list_item:
                if current_section["content"]:
                    structure.append(current_section.copy())
                current_section = {
                    "level": matched_level,
                    "title": line,
                    "content": line + "\n",
                }
            else:
                current_section["content"] += line + "\n"

        if current_section["content"]:
            structure.append(current_section)
        return structure

    def _match_title_level(self, line: str) -> int:
        """判断行的标题层级，返回 0 表示不是标题"""
        stripped_lower = line.strip().lower()

        # ---- 排除明显不是标题的行 ----
        if self.false_title_patterns.search(stripped_lower):
            return 0

        # 太长 / 含过多标点 → 正文，非标题
        if len(stripped_lower) > 80 or stripped_lower.count(',') > 3:
            return 0

        # ---- 标题正则 ----
        for level, pattern in self.title_patterns.items():
            if re.match(pattern, line):
                return level

        # ---- 学术论文独立标题 ----
        clean = stripped_lower.rstrip(".")
        if 3 <= len(clean) <= 40:
            if clean in self.academic_section_titles:
                return 4
            for title in self.academic_section_titles:
                if clean.startswith(title) and len(clean) <= 60:
                    return 4

        return 0

    # ==================== 分块入口 ====================

    def split_documents(self, documents: List[Document]) -> List[Document]:
        MAX_SECTION_SIZE = 3072

        from collections import defaultdict
        # 按 source 分组，同时保留原始 metadata（如 user_id）
        merged_texts = defaultdict(lambda: {"texts": [], "metadata": {}})
        for doc in documents:
            source = doc.metadata.get("source", "未知")
            merged_texts[source]["texts"].append(doc.page_content)
            # 保留 user_id 等关键字段
            if "user_id" in doc.metadata:
                merged_texts[source]["metadata"]["user_id"] = doc.metadata["user_id"]

        chunks = []
        stats = {"single_section": 0, "split_section": 0}

        for source, data in merged_texts.items():
            page_texts = data["texts"]
            original_metadata = data["metadata"]
            full_text = "\n".join(page_texts)
            source_short = source.rsplit('.', 1)[0] if '.' in source else source
            source_tag = f"【文档: {source_short}】\n"

            repeating_lines = self._build_repeating_line_filter(full_text)
            structure = self.extract_structure(full_text, repeating_lines)

            if not structure:
                full_doc = Document(page_content=full_text, metadata={"source": source})
                sub_chunks = self.fallback_splitter.split_documents([full_doc])
                for c in sub_chunks:
                    c.metadata["source"] = source
                    c.metadata["section_title"] = ""
                    # 保留 user_id
                    c.metadata.update(original_metadata)
                    c.page_content = source_tag + c.page_content
                chunks.extend(sub_chunks)
                continue

            for i, sec in enumerate(structure):
                content = sec["content"].strip()
                if not content:
                    continue

                title = sec["title"]
                level = sec["level"]

                # 合并 metadata：基础字段 + 原始用户信息
                base_metadata = {
                    "source": source,
                    "section_title": title,
                    "section_level": level,
                }
                base_metadata.update(original_metadata)

                if len(content) <= MAX_SECTION_SIZE:
                    chunks.append(Document(
                        page_content=source_tag + content,
                        metadata=base_metadata,
                    ))
                    stats["single_section"] += 1
                else:
                    sub_chunks = self.fallback_splitter.split_documents([Document(
                        page_content=content, metadata={"source": source},
                    )])
                    for c in sub_chunks:
                        c.page_content = source_tag + f"【{title}】\n" + c.page_content
                        c.metadata["section_title"] = title
                        c.metadata["section_level"] = level
                        # 保留 user_id
                        c.metadata.update(original_metadata)
                    chunks.extend(sub_chunks)
                    stats["split_section"] += 1

        print(f"  层级分块统计: {stats['single_section']} 个完整节, "
              f"{stats['split_section']} 个长节被细分")
        return chunks


def split_documents_with_hierarchy(documents):
    splitter = HierarchicalTextSplitter()
    return splitter.split_documents(documents)

