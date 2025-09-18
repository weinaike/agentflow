# coderag/index.py
import os
import faiss
import numpy as np
from coderag.config import EMBEDDING_DIM, FAISS_INDEX_FILE, WATCHED_DIR

# global index + metadata (list aligned to index order)
_index = None  # faiss index
_metadata = []  # list of dicts

META_FILE = "metadata.npy"

def _init_index():
    global _index, _metadata
    if _index is None:
        if os.path.exists(FAISS_INDEX_FILE):
            try:
                _index = faiss.read_index(FAISS_INDEX_FILE)
            except Exception as e:
                print(f"[index] failed to read existing faiss index: {e}, creating new.")
                _index = faiss.IndexFlatL2(EMBEDDING_DIM)
        else:
            _index = faiss.IndexFlatL2(EMBEDDING_DIM)

    if os.path.exists(META_FILE):
        try:
            _metadata = np.load(META_FILE, allow_pickle=True).tolist()
        except Exception as e:
            print(f"[index] failed to load metadata file: {e}, starting with empty metadata")
            _metadata = []
    else:
        _metadata = []

_init_index()

def clear_index():
    """Delete FAISS index and metadata (files) and reinit"""
    global _index, _metadata
    if os.path.exists(FAISS_INDEX_FILE):
        os.remove(FAISS_INDEX_FILE)
        print(f"Deleted FAISS index file: {FAISS_INDEX_FILE}")
    if os.path.exists(META_FILE):
        os.remove(META_FILE)
        print(f"Deleted metadata file: {META_FILE}")
    _index = faiss.IndexFlatL2(EMBEDDING_DIM)
    _metadata = []

def add_to_index(embeddings, full_content, filename, filepath, extra_meta=None):
    """
    Add single embedding (1 x dim) or batch (n x dim) to faiss index.
    embeddings: np.ndarray with shape (1, dim) or (n, dim)
    full_content, filename, filepath: used to populate metadata for each vector
    extra_meta: dict or List[dict] — if provided and batch, should match length
    """
    global _index, _metadata
    if embeddings is None:
        return
    emb = np.asarray(embeddings, dtype="float32")
    if emb.ndim == 1:
        emb = emb.reshape(1, -1)

    if emb.shape[1] != EMBEDDING_DIM:
        raise ValueError(f"Embedding dimension mismatch: got {emb.shape[1]}, expected {EMBEDDING_DIM}")

    _index.add(emb)

    # append metadata for each vector
    n = emb.shape[0]

    # If single content used for all entries (common), repeat; else if extra_meta provided as list, use it
    if extra_meta is None:
        for i in range(n):
            _metadata.append({"content": full_content, "filename": filename, "filepath": os.path.relpath(filepath, WATCHED_DIR)})
    else:
        # if provided single dict, repeat
        if isinstance(extra_meta, dict):
            for i in range(n):
                md = dict(extra_meta)
                md.update({"content": full_content, "filename": filename, "filepath": os.path.relpath(filepath, WATCHED_DIR)})
                _metadata.append(md)
        elif isinstance(extra_meta, (list, tuple)):
            if len(extra_meta) != n:
                raise ValueError("Length of extra_meta must equal number of embeddings")
            for md in extra_meta:
                # ensure filepath/filename/content not overwritten if missing
                meta_copy = dict(md)
                meta_copy.setdefault("content", full_content)
                meta_copy.setdefault("filename", filename)
                meta_copy.setdefault("filepath", os.path.relpath(filepath, WATCHED_DIR))
                _metadata.append(meta_copy)
        else:
            raise ValueError("extra_meta must be dict or list of dicts")

def save_index():
    global _index, _metadata
    if _index is None:
        print("[index] no index to save")
        return
    try:
        faiss.write_index(_index, FAISS_INDEX_FILE)
    except Exception as e:
        print(f"[index] faiss write error: {e}")
    try:
        with open(META_FILE, "wb") as f:
            np.save(f, np.array(_metadata, dtype=object), allow_pickle=True)
    except Exception as e:
        print(f"[index] metadata save error: {e}")

def load_index():
    """Return faiss index; will error if FAISS_INDEX_FILE missing"""
    global _index, _metadata
    if _index is None:
        _init_index()
    return _index

def get_metadata():
    global _metadata
    return _metadata

def index_size():
    global _index
    return int(_index.ntotal) if _index else 0

def reconstruct_vector(i):
    global _index
    return _index.reconstruct(i)
