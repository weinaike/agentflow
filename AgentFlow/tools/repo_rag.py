import os
import logging
from pathlib import Path
from collections import defaultdict
from langchain.document_loaders import (
    TextLoader,
    UnstructuredFileLoader
)
from langchain.docstore.document import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
import mimetypes
import sys
from dotenv import load_dotenv
sys.path.insert(0, "/root/wang/csst/RepoUnderstanding/code-chunker")
from Chunker import CodeChunker
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.basicConfig(level=logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# --------- 加载本地文件并自动判断 loader ----------
def load_all_local_files(root_dir: str):
    documents = []
    for path in Path(root_dir).rglob("*"):
        if path.is_file():
            try:
                mime_type, _ = mimetypes.guess_type(str(path))
                if mime_type and mime_type.startswith("text"):
                    loader = TextLoader(str(path), encoding="utf-8")
                else:
                    loader = UnstructuredFileLoader(str(path))
                documents.extend(loader.load())
            except Exception as e:
                #print(f"❌ 跳过 {path}: {e}")
                pass
    return documents


# --------- 文本和代码分割器 ----------
class MultiTypeSplitter:
    def __init__(self, code_chunk_size: int = 1000, text_chunk_size: int = 1000, text_overlap: int = 200):
        self.code_chunk_size = code_chunk_size
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=text_chunk_size,
            chunk_overlap=text_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", "、", "：", " ", "", "\.\s|\!\s|\?\s", "；|;\s", "，|,\s"]
        )

    def split_documents(self, docs):
        out = []
        for doc in docs:
            path = Path(doc.metadata["source"])
            ext = path.suffix.lower().lstrip(".")
            text = doc.page_content

            try:
                chunks = self._split_code(text, ext, doc.metadata)
                if not chunks:  # 如果代码分块失败或返回空，就尝试文本切分
                    chunks = self._split_text(text, doc.metadata)
            except Exception as e:
                #print(f"❌ 文件 {path.name} 分割失败：{e}")
                chunks = self._split_text(text, doc.metadata)

            out.extend(chunks)
        return out

    def _make_doc(self, content, metadata):
        return Document(page_content=content, metadata=metadata)

    def _split_code(self, code_text, ext, metadata):
        chunker = CodeChunker(file_extension=ext, encoding_name="gpt-4")
        raw_chunks = chunker.chunk(code_text, token_limit=self.code_chunk_size)
        return [Document(page_content=code, metadata={**metadata, "chunk_type": "code", "chunk_index": idx})
                for idx, code in raw_chunks.items()]

    def _split_text(self, text, metadata):
        return self.text_splitter.create_documents([text], metadatas=[metadata])


def batch_embed_and_add(chunks, vector_store, embeddings, batch_size=200, max_workers=4):
    """
    分批为 chunks 生成 embeddings 并写入 Chroma，同时显示进度条。
    - batch_size: 每个批次处理的文档块数
    - max_workers: 并行线程数
    """
    total = len(chunks)
    pbar = tqdm(total=total, desc="🧮 Embedding 和 写入", unit="doc")
    
    def process_batch(batch):
        # 1) 批量生成 embedding
        texts = [doc.page_content for doc in batch]
        embs = embeddings.embed_documents(texts)
        # 2) 构造 metadata 和 ids
        metadatas = [doc.metadata for doc in batch]
        # 3) 写入 Chroma
        vector_store.add_embeddings(
            embeddings=embs,
            metadatas=metadatas,
            documents=None  # 如需也可填入原文
        )
        return len(batch)
    
    # 用线程池并行多个批次
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(0, total, batch_size):
            batch = chunks[i:i+batch_size]
            futures.append(executor.submit(process_batch, batch))
        for fut in as_completed(futures):
            processed = fut.result()
            pbar.update(processed)
    pbar.close()

def run_rag(
    repo_path: str,
    questions: list[str],
    embedding_model: str = "text-embedding-3-small",
    llm_model: str = "gpt-4o-2024-08-06",
    chroma_dir: str = "./chroma_db",
    code_chunk_size: int = 1000,
    text_chunk_size: int = 800,
    text_overlap: int = 100,
) -> dict:
    """
    对指定本地仓库执行 RAG 流程，并返回项目摘要及问答结果。

    Args:
        repo_path (str): 本地仓库路径，绝对或相对都可。
        questions (List[str]): 用户提出的问题列表。
        embedding_model (str): 用于生成 embeddings 的模型，默认为 text-embedding-3-small。
        llm_model (str): 用于摘要和问答的 LLM 模型，默认为 gpt-4o-2024-08-06。
        chroma_dir (str): Chroma 向量库持久化目录。
        code_chunk_size (int): 代码分块时的 token 限制。
        text_chunk_size (int): 文本分块时的 chunk 大小。
        text_overlap (int): 文本分块时的 overlap 大小。

    Returns:
        dict: 包含以下字段：
            project_summary (str): 项目级整体摘要。
            qa (List[dict]): 问答结果列表，每项包含:
                - question (str)
                - answer (str)
                - sources (List[str])
    """
    # 1. 加载 & 分割
    docs = load_all_local_files(repo_path)
    splitter = MultiTypeSplitter(
        code_chunk_size=code_chunk_size,
        text_chunk_size=text_chunk_size,
        text_overlap=text_overlap
    )
    chunks = splitter.split_documents(docs)

    # 2. Embedding & 向量库
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base="https://api2.road2all.com/v1",
        model=embedding_model
    )
    vector_store = Chroma(
        collection_name="repo_chunks",
        embedding_function=embeddings,
        persist_directory=chroma_dir
    )
    # 分批写入
    batch_size = 200
    for i in range(0, len(chunks), batch_size):
        vector_store.add_documents(chunks[i : i + batch_size])

    # 3. 项目级摘要
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api2.road2all.com/v1",
        model=llm_model,
        temperature=0.2
    )
    # 重用你在模块顶层定义的 prompt_template
    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        verbose=False,
        map_prompt=prompt_template,
        combine_prompt=prompt_template
    )
    project_summary = chain.invoke(chunks)["output_text"]

    # 4. 针对每个问题执行检索式问答
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True
    )
    chat_history = []
    qa_results = []
    for q in questions:
        res = qa_chain({"question": q, "chat_history": chat_history})
        qa_results.append({
            "question": q,
            "answer": res["answer"],
            "sources": [doc.metadata["source"] for doc in res["source_documents"]]
        })
        chat_history.append((q, res["answer"]))

    return {
        "project_summary": project_summary,
        "qa": qa_results
    }



# --------- 主流程入口 ----------
def main():
    repo_path = "/root/wang/csst/Galsim"  # clone到本地的代码库路径

    print("\n📂 正在加载文件...")
    documents = load_all_local_files(repo_path)
    print(f"✅ 加载完成，共 {len(documents)} 个文件\n")

    splitter = MultiTypeSplitter(code_chunk_size=1000, text_chunk_size=800, text_overlap=150)
    chunks = splitter.split_documents(documents)
    print(f"🧩 分割完成，共 {len(chunks)} 个文档块\n")

    print("🔗 正在生成 Embedding...")
    load_dotenv()
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_base="https://api2.road2all.com/v1",
        model="text-embedding-3-small"
    )

    vector_store = Chroma(collection_name="repo_chunks", embedding_function=embeddings, persist_directory="./chroma_db")
    batch_size = 200
    for i in tqdm(range(0, len(chunks), batch_size), desc="🧮 Embedding+写入", unit="chunk"):
        vector_store.add_documents(chunks[i : i + batch_size])

    # Summarization
    logging.getLogger("langchain").setLevel(logging.WARNING)
    llm = ChatOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://api2.road2all.com/v1",
        model="gpt-4o-2024-08-06",
        temperature=0.2
    )

    prompt_template = PromptTemplate(
        input_variables=["text"],
        template="""
            你是一名专业的代码分析助手，目标是帮助用户理解 GitHub 开源代码仓库。
            以下是代码仓库的文件结构和部分代码片段：
            {text}

            你的任务是：
            1. 总结代码仓库的整体概述和功能目标。
            2. 提炼出代码结构、代码中的核心类和模块，分析它们之间的关系，并说明它们的作用。
            3. 提炼出实现核心功能的主要流程及其涉及的相关内容。

            请生成一个清晰的项目级摘要。
            """
    )

    summarize_chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        verbose=False,
        map_prompt=prompt_template,
        combine_prompt=prompt_template
    )

    print("📝 正在生成项目级摘要...")
    summary = summarize_chain.invoke(chunks)
    print("\n### 📘 项目级摘要：\n")
    print(summary["output_text"])

    # QA Chat
    print("\n🤖 进入问答模式（输入 exit 或 quit 退出）")
    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True
    )

    chat_history = []
    while True:
        query = input("\n用户：")
        if query.strip().lower() in ("exit", "quit"):
            break
        result = qa({"question": query, "chat_history": chat_history})
        print("\n助手：", result["answer"])
        chat_history.append((query, result["answer"]))


if __name__ == "__main__":
    main()
