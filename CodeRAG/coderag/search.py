import numpy as np
from coderag.index import load_index, get_metadata, index_size
from coderag.embeddings import generate_embeddings

def _dist_to_sim(dist):
    # FAISS returns L2 distance; convert to similarity in (0,1], simple transform
    return 1.0 / (1.0 + float(dist))

def search_code(query, k=5, alpha=0.7, beta=0.3, fetch_k=200):
    """
    Search the FAISS index using query, then rerank by combined score:
      combined = alpha * semantic_score + beta * normalized_rank
    metadata is expected to contain a 'rank' numeric field (if absent default 0).
    """
    index = load_index()
    if index is None:
        print("[search] FAISS index not initialized")
        return []

    q_emb = generate_embeddings(query)
    if q_emb is None:
        print("[search] failed to generate query embedding")
        return []

    # ensure q_emb has shape (1, dim)
    if q_emb.ndim == 1:
        q_emb = q_emb.reshape(1, -1)

    fetch_k = min(fetch_k, max(10, index.ntotal)) if index.ntotal > 0 else fetch_k

    D, I = index.search(q_emb.astype("float32"), fetch_k)
    D = D[0].tolist()
    I = I[0].tolist()

    metas = get_metadata()
    results = []
    sims = []
    ranks = []
    for dist, idx in zip(D, I):
        if idx < 0:
            continue
        sim = _dist_to_sim(dist)
        meta = metas[idx] if idx < len(metas) else {}
        rank_val = float(meta.get("rank", 0.0))
        sims.append(sim)
        ranks.append(rank_val)
        results.append({"idx": idx, "dist": dist, "sim": sim, "meta": meta})

    if not results:
        return []

    # normalize sims and ranks to 0..1
    smin, smax = min(sims), max(sims)
    rmin, rmax = min(ranks), max(ranks)
    norm_sims = [ (s - smin) / (smax - smin + 1e-12) for s in sims ]
    norm_ranks = [ (r - rmin) / (rmax - rmin + 1e-12) for r in ranks ]

    # combine
    combined = []
    for i, r in enumerate(results):
        score = alpha * norm_sims[i] + beta * norm_ranks[i]
        combined.append((score, r["meta"], r["sim"], norm_ranks[i], r["idx"]))

    combined.sort(key=lambda x: -x[0])
    out = []
    seen = set()
    for score, meta, sim, nrank, idx in combined[:k*3]:
        key = (meta.get("filepath"), meta.get("filename"), meta.get("start_line"), meta.get("end_line"))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "score": round(score, 4),
            "semantic_score": round(sim, 4),
            "norm_rank": round(nrank, 4),
            "filename": meta.get("filename"),
            "filepath": meta.get("filepath"),
            "content": meta.get("content"),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "rank": meta.get("rank", 0.0)
        })
        if len(out) >= k:
            break
    return out
