import os
import logging
import time
import argparse
import hashlib
from tracemalloc import start
from coderag.index import clear_index, add_to_index, save_index
from coderag.embeddings import generate_embeddings
from coderag.config import WATCHED_DIR
from coderag.ts_splitter import chunk_file_by_syntax
from coderag.monitor import start_monitoring, should_ignore_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BATCH_SIZE = 32
MAX_CHUNK_CHARS = 20000

def make_chunk_id(file_path, start_line, end_line):
    return hashlib.sha1(f"{file_path}:{start_line}-{end_line}".encode("utf8")).hexdigest()

def parse_repomap_text(path):
    ranks = {}
    import re
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    cur = None
    for ln in lines:
        ln_strip = ln.strip()
        m = re.match(r'^([^\s:]+):\s*$', ln_strip)
        if m:
            cur = m.group(1)
            continue
        m2 = re.search(r'Rank value:\s*([0-9.]+)', ln_strip)
        if m2 and cur:
            ranks[cur] = float(m2.group(1))
            cur = None
    return ranks

def full_reindex(repo_root, repomap_output_path):
    """
    完整重建索引（按 repomap 排序切块并批量插入）
    """
    clear_index()
    start = time.time()
    logging.info("Parsing repomap output...")
    rank_map = parse_repomap_text(repomap_output_path)
    files = []
    for fname, rank in rank_map.items():
        p = fname if os.path.isabs(fname) else os.path.join(repo_root, fname)
        if os.path.isfile(p):
            files.append((p, float(rank)))
    files.sort(key=lambda x: -x[1])

    pending_texts = []
    pending_meta = []
    total_chunks = 0
    ignore_files = 0

    for file_path, rank in files:
        if should_ignore_path(file_path):
            logging.info(f"Ignoring file: {file_path}")
            ignore_files +=1
            continue

        chunks = chunk_file_by_syntax(file_path, parser=None, max_chars=MAX_CHUNK_CHARS)
        for ch in chunks:
            cid = make_chunk_id(file_path, ch["start_line"], ch["end_line"])
            meta = {
                "content": ch["text"],
                "filename": os.path.basename(file_path),
                "filepath": os.path.relpath(file_path, repo_root),
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "kind": ch.get("kind","chunk"),
                "name": ch.get("name"),
                "rank": rank,
                "chunk_id": cid
            }
            pending_texts.append(ch["text"])
            pending_meta.append(meta)
            total_chunks += 1

            if len(pending_texts) >= BATCH_SIZE:
                embs = generate_embeddings(pending_texts)
                if embs is None:
                    logging.error("Embedding failed for a batch; skipping")
                else:
                    add_to_index(embs, pending_texts[0], pending_meta[0]["filename"], pending_meta[0]["filepath"], extra_meta=pending_meta)
                pending_texts = []
                pending_meta = []

    # flush
    if pending_texts:
        embs = generate_embeddings(pending_texts)
        if embs is not None:
            add_to_index(embs, pending_texts[0], pending_meta[0]["filename"], pending_meta[0]["filepath"], extra_meta=pending_meta)

    save_index()
    elapsed = time.time() - start
    logging.info(f"Full reindex complete: files={len(files)}, chunks={total_chunks}, ignored={ignore_files}, time={elapsed:.1f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--repomap-output", required=True)
    args = parser.parse_args()
    full_reindex(args.repo_root, args.repomap_output)
    start_monitoring()
