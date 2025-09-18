from tree_sitter import Language, Parser
import tree_sitter_python
import os
import bisect
from typing import List, Dict, Any, Optional

def get_python_parser() -> Parser:
    """
    使用 tree-sitter + tree_sitter_python 提供 Python 解析器
    """
    PY_LANGUAGE = Language(tree_sitter_python.language())
    parser = Parser(PY_LANGUAGE)
    return parser

def _build_line_starts(text: str):
    """构建行起始位置映射"""
    lines = text.splitlines(keepends=True)
    starts = [0]
    s = 0
    for ln in lines:
        s += len(ln)
        starts.append(s)
    return starts

def _byte_to_line(byte_off: int, line_starts: List[int]) -> int:
    """字节位置转行号"""
    i = bisect.bisect_right(line_starts, byte_off) - 1
    return i + 1  # 1-based

def split_text_into_segments(text: str, max_chars: int = 20000) -> List[str]:
    """
    将 text 切分为多个段落（<= max_chars），按行边界优先。
    返回 List[str]
    """
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    
    lines = text.splitlines(True)
    segs = []
    cur = ""
    for ln in lines:
        if len(cur) + len(ln) > max_chars and cur:
            segs.append(cur)
            cur = ln
        else:
            cur += ln
    if cur:
        segs.append(cur)
    return segs

def chunk_file_by_syntax(abs_path: str, parser: Optional[Parser] = None, max_chars: int = 20000) -> List[Dict[str, Any]]:
    """
    用 Python 的 tree-sitter parser 切分大文件，按 function/class 切块。
    返回 list of dict: {start_line, end_line, text, name, kind}
    """
    text = ""
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []

    # 如果文件内容不超过最大字符数，直接返回整个文件作为一个chunk
    if len(text) <= max_chars:
        return [{
            "start_line": 1, 
            "end_line": text.count("\n") + 1, 
            "text": text, 
            "name": os.path.basename(abs_path), 
            "kind": "module"
        }]

    if parser is None:
        parser = get_python_parser()

    try:
        tree = parser.parse(bytes(text, "utf8"))
    except Exception:
        return [{"start_line": 1, "end_line": text.count("\n")+1, "text": text, "name": os.path.basename(abs_path), "kind": "module"}]

    root = tree.root_node
    line_starts = _build_line_starts(text)

    chunks = []
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type in ("function_definition", "class_definition"):
            st = _byte_to_line(n.start_byte, line_starts)
            ed = _byte_to_line(n.end_byte, line_starts)
            
            # 查找标识符（函数名或类名）
            name = None
            for c in n.children:
                if c.type == "identifier":
                    try:
                        name = text[c.start_byte:c.end_byte]
                    except Exception:
                        name = None
                    break
            
            kind = "function" if n.type == "function_definition" else "class"
            snippet = text[n.start_byte:n.end_byte]
            
            if len(snippet) > max_chars:
                # 如果代码块超过最大字符数，进一步切分
                segs = split_text_into_segments(snippet, max_chars=max_chars)
                cur_line = st
                for seg in segs:
                    seg_lines = seg.count("\n") + 1
                    chunks.append({
                        "start_line": cur_line, 
                        "end_line": cur_line + seg_lines - 1, 
                        "text": seg, 
                        "name": name or "(anon)", 
                        "kind": kind
                    })
                    cur_line += seg_lines
            else:
                # 直接添加完整的代码块
                chunks.append({
                    "start_line": st, 
                    "end_line": ed, 
                    "text": snippet, 
                    "name": name or "(anon)", 
                    "kind": kind
                })
        else:
            # 继续遍历子节点
            for c in reversed(n.children):
                stack.append(c)

    if not chunks:
        chunks.append({"start_line": 1, "end_line": text.count("\n")+1, "text": text, "name": os.path.basename(abs_path), "kind": "module"})
    
    return chunks

def smart_split_python_file(file_path: str, max_chars: int = 20000) -> List[Dict[str, Any]]:
    """
    智能切分Python文件的便捷接口
    结合语法解析和文本切分，返回结构化的代码块
    """
    return chunk_file_by_syntax(file_path, max_chars=max_chars) 