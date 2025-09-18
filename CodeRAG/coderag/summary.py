import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from coderag.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL, WATCHED_DIR, NLTK_DATA

# 禁用NLTK警告
warnings.filterwarnings("ignore", category=UserWarning, module="nltk")

# 配置并发参数
MAX_WORKERS = 10
REQUEST_DELAY = 0.05

# 模型上下文限制
MAX_MODEL_TOKENS = 128000
TOKEN_SAFETY_MARGIN = 0.9
MAX_PROCESSABLE_TOKENS = int(MAX_MODEL_TOKENS * TOKEN_SAFETY_MARGIN)

llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api2.road2all.com/v1",
    model=OPENAI_CHAT_MODEL, 
    temperature=0.2
)

OVERVIEW_PROMPT = PromptTemplate(
    input_variables=["text"],
    template="""
你是一名经验丰富的软件架构师，擅长分析开源项目。请根据以下提供的代码仓库信息，用中文撰写一篇清晰、有条理的项目概述。

### 项目信息
{text}

### 任务要求
1. **项目整体概述**：用简洁的语言描述项目的核心功能、目标用户和主要应用场景。
2. **架构设计**：分析项目的整体架构，包括采用的设计模式、分层结构和技术栈选择。
3. **核心模块详解**：识别并详细解释项目中的关键模块或组件，说明它们的职责和交互方式。
4. **技术亮点**：指出项目中独特或值得注意的技术实现，如算法优化、性能调优等。
5. **文件结构分析**：概述项目的目录结构和主要文件的作用，帮助读者快速理解代码组织方式。

请确保内容逻辑清晰，避免冗长的代码细节，突出项目的整体设计思路和技术价值。
"""
)

SUPPORTED_EXTS = [
    "py", "js", "ts", "md", "yml", "yaml", "cpp", "h",
    "txt", "c", "rs", "go", "sol"
]

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=6000,
    chunk_overlap=400,
    separators=["\n\n# ", "\n\n## ", "\n\n### ", "\n\n", "\n", " ", ""]
)

def estimate_tokens(text: str) -> int:
    return len(text) // 4

def load_project_files() -> str:
    project_content = []
    for ext in SUPPORTED_EXTS:
        loader = DirectoryLoader(WATCHED_DIR, glob=f"**/*.{ext}")
        documents = loader.load()
        for doc in documents:
            rel_path = os.path.relpath(doc.metadata['source'], WATCHED_DIR)
            if not doc.page_content.strip():
                continue
            max_file_size = 60000
            if len(doc.page_content) > max_file_size:
                content = doc.page_content[:max_file_size] + "\n\n... [内容过长，已截断]"
            else:
                content = doc.page_content
            file_content = f"\n\n# 文件: {rel_path}\n\n{content}"
            project_content.append(file_content)
    return "\n\n".join(project_content)

def process_chunk(chunk, index, total):
    """处理单个文档块，确保返回字符串"""
    print(f"开始处理块 {index+1}/{total} ({estimate_tokens(chunk.page_content):,} 估计tokens)")
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=OVERVIEW_PROMPT)
    time.sleep(REQUEST_DELAY)
    
    try:
        # 显式提取字符串结果
        result = chain.invoke([chunk])
        # 如果返回的是dict，提取output_text；否则直接使用字符串
        if isinstance(result, dict):
            result = result.get("output_text", f"[块 {index+1} 无有效内容]")
        print(f"成功完成块 {index+1}/{total}")
        return result  # 确保返回str
    except Exception as e:
        print(f"处理块 {index+1}/{total} 时出错: {str(e)}")
        # 子块处理同样确保返回str
        smaller_splitter = RecursiveCharacterTextSplitter(chunk_size=6000, chunk_overlap=400)
        sub_chunks = smaller_splitter.split_documents([chunk])
        sub_results = []
        for i, sub_chunk in enumerate(sub_chunks):
            try:
                sub_chain = load_summarize_chain(llm, chain_type="stuff", prompt=OVERVIEW_PROMPT)
                sub_result = sub_chain.invoke([sub_chunk])
                # 同样处理可能的dict结果
                if isinstance(sub_result, dict):
                    sub_result = sub_result.get("output_text", f"[子块 {i+1} 无有效内容]")
                sub_results.append(sub_result)
            except Exception as e2:
                sub_results.append(f"[子块 {i+1} 处理失败: {str(e2)}]")
        return "\n\n---\n\n".join(sub_results)  # 确保返回str

def recursive_summarize(text: str, level: int = 1) -> str:
    print(f"递归摘要级别 {level}: {estimate_tokens(text):,} 估计tokens")
    if estimate_tokens(text) <= MAX_PROCESSABLE_TOKENS:
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(
            llm, chain_type="map_reduce",
            map_prompt=OVERVIEW_PROMPT, combine_prompt=OVERVIEW_PROMPT
        )
        result = chain.invoke(docs)
        # 提取可能的dict结果
        if isinstance(result, dict):
            return result.get("output_text", "[无有效摘要内容]")
        return result
    
    docs = text_splitter.create_documents([text])
    processed_chunks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_index = {executor.submit(process_chunk, chunk, i, len(docs)): i for i, chunk in enumerate(docs)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                res = future.result()
                # 确保结果是str（过滤可能的非str类型）
                if not isinstance(res, str):
                    res = f"[块 {index+1} 结果类型错误: {type(res)}]"
                processed_chunks.append((index, res))
            except Exception as e:
                processed_chunks.append((index, f"[块 {index+1} 处理异常: {str(e)}]"))
    
    processed_chunks.sort(key=lambda x: x[0])
    sorted_results = [result for _, result in processed_chunks]  # 此时应为纯str列表
    combined_result = "\n\n---\n\n".join(sorted_results)  # 现在可以安全拼接
    return recursive_summarize(combined_result, level + 1)

def generate_project_overview() -> str:
    start_time = time.time()
    print(f"开始分析项目: {WATCHED_DIR}")
    project_content = load_project_files()
    total_tokens = estimate_tokens(project_content)
    print(f"已加载项目文件，总长度: {len(project_content):,} 字符 ({total_tokens:,} 估计tokens)")
    overview = recursive_summarize(project_content)
    end_time = time.time()
    print(f"项目整体解读生成完成，耗时: {end_time - start_time:.2f} 秒")
    return overview

_cached_overview: str | None = None
def get_project_summary() -> str:
    global _cached_overview
    if _cached_overview is None:
        _cached_overview = generate_project_overview()
    return _cached_overview

if __name__ == "__main__":
    summary = get_project_summary()
    print("Project Summary:")
    print(summary)