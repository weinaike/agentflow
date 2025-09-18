from openai import OpenAI
import numpy as np
from coderag.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api2.road2all.com/v1")

def _call_openai_embeddings(texts):
    """
    texts: List[str]
    Returns np.ndarray shape (n, dim) float32
    """
    try:
        resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
        embs = [r.embedding for r in resp.data]
        arr = np.array(embs, dtype="float32")
        return arr
    except Exception as e:
        print(f"[embeddings] OpenAI embedding error: {e}")
        return None

def generate_embeddings(text_or_texts):
    """
    兼容单条或多条输入：
      - 如果输入是 str -> 返回 np.ndarray shape (1, dim)
      - 如果输入是 List[str] -> 返回 np.ndarray shape (n, dim)
    """
    if text_or_texts is None:
        return None
    if isinstance(text_or_texts, str):
        texts = [text_or_texts]
    elif isinstance(text_or_texts, (list, tuple)):
        texts = list(text_or_texts)
    else:
        raise ValueError("generate_embeddings expects str or List[str]")

    # optionally: perform splitting for super-long single item - skip automatic split here to keep control
    try:
        arr = _call_openai_embeddings(texts)
        return arr
    except Exception as e:
        print(f"[embeddings] unexpected error: {e}")
        return None
