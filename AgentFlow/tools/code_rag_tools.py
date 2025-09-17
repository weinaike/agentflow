import os
import sys
import logging
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from autogen_core.tools import FunctionTool
from pydantic import BaseModel, Field

# 添加CodeRAG路径
sys.path.insert(0, "/home/www/AgentFlow/CodeRAG")
from coderag.ts_splitter import chunk_file_by_syntax, get_python_parser
from coderag.embeddings import generate_embeddings
from coderag.index import clear_index, add_to_index, save_index, load_index, get_metadata, index_size
from coderag.search import search_code
from coderag.config import WATCHED_DIR, FAISS_INDEX_FILE, EMBEDDING_DIM

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 数据模型定义 ====================

class CodeChunkingInput(BaseModel):
    """代码分割输入参数"""
    repo_path: str = Field(..., description="代码仓库路径")
    max_chunk_chars: int = Field(default=20000, description="最大代码块字符数")

class CodeChunkingOutput(BaseModel):
    """代码分割输出结果"""
    total_files: int = Field(..., description="处理的文件总数")
    total_chunks: int = Field(..., description="生成的代码块总数")
    chunk_info: List[Dict[str, Any]] = Field(..., description="代码块详细信息")
    processing_time: float = Field(..., description="处理时间（秒）")

class IndexBuildingInput(BaseModel):
    """向量索引构建输入参数"""
    repo_path: str = Field(..., description="代码仓库路径")
    chunk_info: List[Dict[str, Any]] = Field(..., description="代码块信息列表，从code_chunking工具获取")
    batch_size: int = Field(default=32, description="批处理大小")

class IndexBuildingOutput(BaseModel):
    """索引构建输出结果"""
    index_size: int = Field(..., description="索引大小")
    embedding_dim: int = Field(..., description="向量维度")
    processing_time: float = Field(..., description="处理时间（秒）")

class SummaryGenerationInput(BaseModel):
    """综述生成输入参数"""
    repo_path: str = Field(..., description="代码仓库路径")
    index_path: str = Field(..., description="向量索引路径")
    summary_type: str = Field(default="comprehensive", description="综述类型：comprehensive/detailed/brief")

class SummaryGenerationOutput(BaseModel):
    """综述生成输出结果"""
    summary: str = Field(..., description="代码仓库综述文档")
    key_modules: List[str] = Field(..., description="关键模块列表")
    statistics: Dict[str, Any] = Field(..., description="统计信息")

class QASystemInput(BaseModel):
    """问答系统输入参数"""
    question: str = Field(..., description="用户问题")
    index_path: str = Field(..., description="向量索引路径")
    top_k: int = Field(default=5, description="检索top-k结果")
    alpha: float = Field(default=0.7, description="语义相似度权重")
    beta: float = Field(default=0.3, description="排名权重")

class QASystemOutput(BaseModel):
    """问答系统输出结果"""
    answer: str = Field(..., description="生成的答案")
    sources: List[Dict[str, Any]] = Field(..., description="检索到的相关代码片段")
    confidence: float = Field(..., description="答案置信度")

class ProjectStatsOutput(BaseModel):
    """项目统计信息输出"""
    total_files: int = Field(..., description="文件总数")
    total_lines: int = Field(..., description="代码行数")
    file_types: Dict[str, int] = Field(..., description="文件类型统计")
    directory_count: int = Field(..., description="目录数量")
    largest_files: List[Dict[str, Any]] = Field(..., description="最大的文件列表")
    code_files: Dict[str, int] = Field(..., description="代码文件统计")
    total_size: int = Field(..., description="项目总大小（字节）")


# ==================== 工具函数实现 ====================

def make_chunk_id(file_path: str, start_line: int, end_line: int) -> str:
    """生成代码块唯一ID"""
    return hashlib.sha1(f"{file_path}:{start_line}-{end_line}".encode("utf8")).hexdigest()

def should_ignore_path(file_path: str) -> bool:
    """判断是否应该忽略该文件路径"""
    ignore_patterns = [
        '.git', '__pycache__', '.venv', 'node_modules', 
        '.pytest_cache', '.coverage', '*.pyc', '*.pyo',
        'build', 'dist', '.eggs', '*.egg-info'
    ]
    
    file_path_lower = file_path.lower()
    for pattern in ignore_patterns:
        if pattern in file_path_lower:
            return True
    return False

def get_supported_file_extensions() -> List[str]:
    """获取支持的文件扩展名"""
    return ['.py', '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx', '.java', '.js', '.ts', '.go', '.rs']

def code_chunking(repo_path: str, max_chunk_chars: int = 20000) -> CodeChunkingOutput:
    """
    对代码仓库进行智能分割，使用tree-sitter进行语法感知分割
    
    Args:
        repo_path: 代码仓库路径
        max_chunk_chars: 最大代码块字符数
        
    Returns:
        CodeChunkingOutput: 分割结果
    """
    start_time = time.time()
    logger.info(f"开始处理代码仓库: {repo_path}")
    
    if not os.path.exists(repo_path):
        raise ValueError(f"代码仓库路径不存在: {repo_path}")
    
    # 获取所有支持的文件
    supported_extensions = get_supported_file_extensions()
    files_to_process = []
    
    for root, dirs, files in os.walk(repo_path):
        # 过滤掉需要忽略的目录
        dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(root, d))]
        
        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore_path(file_path):
                continue
                
            _, ext = os.path.splitext(file)
            if ext.lower() in supported_extensions:
                files_to_process.append(file_path)
    
    logger.info(f"找到 {len(files_to_process)} 个文件需要处理")
    
    # 处理文件并生成代码块
    all_chunks = []
    processed_files = 0
    
    for file_path in files_to_process:
        try:
            # 使用tree-sitter进行语法感知分割
            chunks = chunk_file_by_syntax(file_path, parser=None, max_chars=max_chunk_chars)
            
            for chunk in chunks:
                chunk_id = make_chunk_id(file_path, chunk["start_line"], chunk["end_line"])
                chunk_info = {
                    "chunk_id": chunk_id,
                    "file_path": file_path,
                    "relative_path": os.path.relpath(file_path, repo_path),
                    "filename": os.path.basename(file_path),
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "text": chunk["text"],
                    "name": chunk.get("name", ""),
                    "kind": chunk.get("kind", "chunk"),
                    "char_count": len(chunk["text"])
                }
                all_chunks.append(chunk_info)
            
            processed_files += 1
            if processed_files % 100 == 0:
                logger.info(f"已处理 {processed_files}/{len(files_to_process)} 个文件")
                
        except Exception as e:
            logger.warning(f"处理文件失败 {file_path}: {e}")
            continue
    
    processing_time = time.time() - start_time
    logger.info(f"代码分割完成: 处理了 {processed_files} 个文件，生成 {len(all_chunks)} 个代码块，耗时 {processing_time:.2f} 秒")
    
    return CodeChunkingOutput(
        total_files=processed_files,
        total_chunks=len(all_chunks),
        chunk_info=all_chunks,
        processing_time=processing_time
    )

def build_vector_index(repo_path: str, chunk_info: List[Dict[str, Any]], batch_size: int = 32) -> IndexBuildingOutput:
    """
    构建向量索引，使用FAISS存储代码块向量
    
    Args:
        repo_path: 代码仓库路径
        chunk_info: 代码块信息列表，从code_chunking工具获取
        batch_size: 批处理大小
        
    Returns:
        IndexBuildingOutput: 索引构建结果
    """
    start_time = time.time()
    logger.info(f"开始构建向量索引，共 {len(chunk_info)} 个代码块")
    
    # 清空现有索引
    clear_index()
    
    # 设置工作目录
    global WATCHED_DIR
    WATCHED_DIR = repo_path
    
    # 分批处理代码块
    total_chunks = len(chunk_info)
    processed_chunks = 0
    
    for i in range(0, total_chunks, batch_size):
        batch_chunks = chunk_info[i:i + batch_size]
        
        # 准备批处理数据
        texts = []
        metadatas = []
        
        for chunk in batch_chunks:
            texts.append(chunk["text"])
            metadata = {
                "content": chunk["text"],
                "filename": chunk["filename"],
                "filepath": chunk["relative_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "kind": chunk["kind"],
                "name": chunk["name"],
                "chunk_id": chunk["chunk_id"],
                "rank": 1.0  # 默认排名
            }
            metadatas.append(metadata)
        
        # 生成embeddings
        try:
            embeddings = generate_embeddings(texts)
            if embeddings is not None:
                # 添加到索引
                for j, (emb, meta) in enumerate(zip(embeddings, metadatas)):
                    add_to_index(
                        emb.reshape(1, -1),
                        meta["content"],
                        meta["filename"],
                        os.path.join(repo_path, meta["filepath"]),
                        extra_meta=meta
                    )
                processed_chunks += len(batch_chunks)
            else:
                logger.warning(f"批次 {i//batch_size + 1} 的embedding生成失败")
        except Exception as e:
            logger.error(f"处理批次 {i//batch_size + 1} 时出错: {e}")
            continue
        
        if (i // batch_size + 1) % 10 == 0:
            logger.info(f"已处理 {processed_chunks}/{total_chunks} 个代码块")
    
    # 保存索引
    save_index()
    
    processing_time = time.time() - start_time
    index_size_val = index_size()
    
    logger.info(f"向量索引构建完成: 索引大小 {index_size_val}，耗时 {processing_time:.2f} 秒")
    
    return IndexBuildingOutput(
        index_size=index_size_val,
        embedding_dim=EMBEDDING_DIM,
        processing_time=processing_time
    )

def get_project_stats(repo_path: str) -> ProjectStatsOutput:
    """
    获取项目基础统计信息（轻量级工具）
    
    Args:
        repo_path: 代码仓库路径
        
    Returns:
        ProjectStatsOutput: 项目统计信息
    """
    import os
    from pathlib import Path
    
    logger.info(f"开始统计项目信息: {repo_path}")
    
    stats = {
        "total_files": 0,
        "total_lines": 0,
        "file_types": {},
        "directory_count": 0,
        "largest_files": [],
        "code_files": {},
        "total_size": 0
    }
    
    file_sizes = []
    code_extensions = {'.py', '.js', '.ts', '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx', 
                      '.java', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala',
                      '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd'}
    
    try:
        for root, dirs, files in os.walk(repo_path):
            # 跳过隐藏目录和常见的不需要统计的目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'build', 'dist', 'target']]
            
            stats["directory_count"] += len(dirs)
            
            for file in files:
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                stats["total_files"] += 1
                
                try:
                    # 获取文件大小
                    file_size = os.path.getsize(file_path)
                    stats["total_size"] += file_size
                    
                    # 文件类型统计
                    ext = Path(file).suffix.lower()
                    if not ext:
                        ext = "no_extension"
                    stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
                    
                    # 代码文件统计
                    if ext in code_extensions:
                        stats["code_files"][ext] = stats["code_files"].get(ext, 0) + 1
                        
                        # 统计代码行数
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = len(f.readlines())
                                stats["total_lines"] += lines
                                file_sizes.append({
                                    "path": file_path.replace(repo_path, "").lstrip("/"),
                                    "size": file_size,
                                    "lines": lines,
                                    "extension": ext
                                })
                        except Exception as e:
                            logger.warning(f"无法读取文件 {file_path}: {e}")
                            file_sizes.append({
                                "path": file_path.replace(repo_path, "").lstrip("/"),
                                "size": file_size,
                                "lines": 0,
                                "extension": ext
                            })
                    else:
                        file_sizes.append({
                            "path": file_path.replace(repo_path, "").lstrip("/"),
                            "size": file_size,
                            "lines": 0,
                            "extension": ext
                        })
                        
                except Exception as e:
                    logger.warning(f"无法处理文件 {file_path}: {e}")
                    continue
        
        # 获取最大的文件（按大小排序，最多10个）
        stats["largest_files"] = sorted(file_sizes, key=lambda x: x["size"], reverse=True)[:10]
        
        logger.info(f"项目统计完成: {stats['total_files']} 文件, {stats['total_lines']} 行代码")
        
        return ProjectStatsOutput(**stats)
        
    except Exception as e:
        logger.error(f"统计项目信息失败: {e}")
        raise ValueError(f"无法统计项目信息: {e}")

def rag_qa_system(question: str, index_path: str, top_k: int = 5, alpha: float = 0.7, beta: float = 0.3) -> QASystemOutput:
    """
    基于RAG的智能问答系统
    
    Args:
        question: 用户问题
        index_path: 向量索引路径
        top_k: 检索top-k结果
        alpha: 语义相似度权重
        beta: 排名权重
        
    Returns:
        QASystemOutput: 问答结果
    """
    logger.info(f"处理用户问题: {question}")
    
    # 加载索引
    try:
        index = load_index()
        if index is None:
            raise ValueError("向量索引未初始化")
    except Exception as e:
        logger.error(f"加载索引失败: {e}")
        raise ValueError(f"无法加载向量索引: {e}")
    
    # 执行搜索
    try:
        search_results = search_code(question, k=top_k, alpha=alpha, beta=beta)
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise ValueError(f"搜索执行失败: {e}")
    
    if not search_results:
        return QASystemOutput(
            answer="抱歉，没有找到与您问题相关的代码片段。",
            sources=[],
            confidence=0.0
        )
    
    # 生成答案
    answer_parts = []
    answer_parts.append(f"基于代码仓库分析，我来回答您的问题：\n\n")
    
    # 分析搜索结果
    sources = []
    for i, result in enumerate(search_results, 1):
        source_info = {
            "rank": i,
            "score": result["score"],
            "filename": result["filename"],
            "filepath": result["filepath"],
            "start_line": result["start_line"],
            "end_line": result["end_line"],
            "content": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"]
        }
        sources.append(source_info)
        
        answer_parts.append(f"**相关代码片段 {i}** (相似度: {result['score']:.3f})\n")
        answer_parts.append(f"文件: {result['filepath']} (第{result['start_line']}-{result['end_line']}行)\n")
        answer_parts.append(f"```\n{result['content'][:300]}{'...' if len(result['content']) > 300 else ''}\n```\n\n")
    
    # 添加总结
    answer_parts.append("**总结**: 以上代码片段与您的问题最相关。如果您需要更详细的分析或有其他问题，请随时询问。")
    
    answer = "".join(answer_parts)
    
    # 计算置信度（基于最高相似度分数）
    confidence = search_results[0]["score"] if search_results else 0.0
    
    logger.info(f"问答完成，置信度: {confidence:.3f}")
    
    return QASystemOutput(
        answer=answer,
        sources=sources,
        confidence=confidence
    )

# ==================== 工具实例创建 ====================

code_chunking_tool = FunctionTool(
    func=code_chunking,
    name="code_chunking",
    description="对代码仓库进行智能分割，使用tree-sitter进行语法感知分割"
)

build_index_tool = FunctionTool(
    func=build_vector_index,
    name="build_vector_index", 
    description="构建向量索引，使用FAISS存储代码块向量。需要先使用code_chunking工具获取chunk_info参数。"
)


rag_qa_tool = FunctionTool(
    func=rag_qa_system,
    name="rag_qa_system",
    description="基于RAG的智能问答系统"
)

# 创建工具实例
get_project_stats_tool = FunctionTool(
    func=get_project_stats,
    name="get_project_stats",
    description="获取代码仓库的基础统计信息，包括文件数量、代码行数、文件类型分布等"
)

# 导出所有工具
__all__ = [
    "code_chunking_tool",
    "build_index_tool", 
    "rag_qa_tool",
    "code_chunking",
    "build_vector_index",
    "rag_qa_system",
    "get_project_stats_tool"
]