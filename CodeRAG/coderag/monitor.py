import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from coderag.index import add_to_index, save_index, get_metadata, clear_index, index_size
from coderag.embeddings import generate_embeddings
from coderag.config import WATCHED_DIR, IGNORE_PATHS
from coderag.ts_splitter import chunk_file_by_syntax
import logging
import math
import itertools
import threading

BATCH_SIZE = 32  # 批量 re-embed 大小

def should_ignore_path(path):
    """Check if the given path should be ignored based on the IGNORE_PATHS list."""
    for ignore_path in IGNORE_PATHS:
        if path.startswith(ignore_path):
            return True
    return False

def _rebuild_index_with_new_meta(remaining_meta, new_meta_chunks):
    """
    Strategy:
      - clear_index()
      - 先将 remaining_meta 分批 embed 并 add_to_index
      - 再将 new_meta_chunks embed 并 add_to_index
      - save_index()
    remaining_meta / new_meta_chunks: list of dict, each dict must contain 'content','filename','filepath' and may contain other fields
    """
    logging.info(f"Rebuilding index: remaining_meta={len(remaining_meta)}, new_chunks={len(new_meta_chunks)}")
    # wipe index
    clear_index()

    # helper to batch-embed-and-add: accepts list of meta entries (with 'content' key)
    def batch_process(meta_list):
        for i in range(0, len(meta_list), BATCH_SIZE):
            batch = meta_list[i:i+BATCH_SIZE]
            texts = [m["content"] for m in batch]
            embs = generate_embeddings(texts)
            if embs is None:
                logging.error("Embedding failed for a batch during rebuild; skipping this batch.")
                continue
            # embs shape (n, dim)
            # add_to_index expects embeddings (n,dim), full_content, filename, filepath, extra_meta=list
            # We'll pass first item's content/filename/filepath as full_content and provide extra_meta=batch
            add_to_index(embs, batch[0].get("content",""), batch[0].get("filename",""), batch[0].get("filepath",""), extra_meta=batch)

    # re-add remaining metadata (old entries)
    if remaining_meta:
        batch_process(remaining_meta)

    # add new chunks (changed file)
    if new_meta_chunks:
        batch_process(new_meta_chunks)

    save_index()
    logging.info("Rebuild complete. Current index size: %d" % index_size())

class CodeChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or should_ignore_path(event.src_path):
            return

        _, ext = os.path.splitext(event.src_path)
        if ext.lower() != ".py":
            return

        logging.info(f"Detected change in file: {event.src_path}")

        # chunk the file into chunks
        try:
            chunks = chunk_file_by_syntax(event.src_path)
        except Exception as e:
            logging.error(f"Chunking failed for {event.src_path}: {e}")
            chunks = []

        # prepare new_meta_chunks
        relpath = os.path.relpath(event.src_path, WATCHED_DIR)
        new_meta_chunks = []
        for ch in chunks:
            meta = {
                "content": ch["text"],
                "filename": os.path.basename(event.src_path),
                "filepath": relpath,
                "start_line": ch.get("start_line"),
                "end_line": ch.get("end_line"),
                "kind": ch.get("kind"),
                # 'rank' may not be known here; keep 0 or you can supply a default
                "rank": ch.get("rank", 0.0)
            }
            new_meta_chunks.append(meta)

        # get existing metadata and filter out entries for this file
        existing = get_metadata()
        remaining = [m for m in existing if m.get("filepath") != relpath]

        # do rebuild in background thread to avoid blocking watchdog loop
        t = threading.Thread(target=_rebuild_index_with_new_meta, args=(remaining, new_meta_chunks), daemon=True)
        t.start()

def start_monitoring():
    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCHED_DIR, recursive=True)
    observer.start()
    logging.info(f"Started monitoring {WATCHED_DIR}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
