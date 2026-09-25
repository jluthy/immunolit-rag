"""Build a concept co-occurrence graph and a UMAP+cluster layout from the
embedded corpus. This is the differentiating layer: retrieval answers a
specific question, this answers "what does the whole corpus look like."""
import json
import os
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import umap
import hdbscan
import lancedb


def extract_concepts(texts: list[str], top_k: int = 8) -> list[list[str]]:
    vectorizer = TfidfVectorizer(max_features=500, stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(texts)
    terms = np.array(vectorizer.get_feature_names_out())
    results = []
    for row in matrix.toarray():
        top_idx = row.argsort()[::-1][:top_k]
        top_idx = [i for i in top_idx if row[i] > 0]
        results.append(list(terms[top_idx]))
    return results


def build_cooccurrence_graph(pmid_concepts: dict[str, list[str]]) -> dict:
    edge_counts = Counter()
    node_pmids = {}
    for pmid, concepts in pmid_concepts.items():
        for concept in concepts:
            node_pmids.setdefault(concept, set()).add(pmid)
        for a, b in combinations(sorted(set(concepts)), 2):
            edge_counts[(a, b)] += 1

    nodes = [{"id": concept, "paper_count": len(pmids)} for concept, pmids in node_pmids.items()]
    edges = [
        {"source": a, "target": b, "weight": weight}
        for (a, b), weight in edge_counts.items()
    ]
    return {"nodes": nodes, "edges": edges}


def reduce_and_cluster(vectors: list[list[float]], pmids: list[str]) -> dict:
    arr = np.array(vectors)
    n_neighbors = min(15, max(2, len(arr) - 1))
    reducer = umap.UMAP(n_components=2, n_neighbors=n_neighbors, random_state=42)
    coords_2d = reducer.fit_transform(arr)

    min_cluster_size = max(3, len(arr) // 20)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(coords_2d)

    return {
        pmid: {"x": float(coords_2d[i][0]), "y": float(coords_2d[i][1]), "cluster": int(labels[i])}
        for i, pmid in enumerate(pmids)
    }


def build_graph_summary(chunks_path: str, lancedb_dir: str, table_name: str, out_dir: str) -> str:
    with open(chunks_path) as f:
        chunks = json.load(f)

    # One text blob per pmid (concatenate its chunks) for concept extraction
    by_pmid_text: dict[str, list[str]] = {}
    by_pmid_title: dict[str, str] = {}
    for c in chunks:
        by_pmid_text.setdefault(c["pmid"], []).append(c["text"])
        by_pmid_title[c["pmid"]] = c["title"]
    pmids = list(by_pmid_text.keys())
    texts = [" ".join(by_pmid_text[p]) for p in pmids]

    concepts_per_doc = extract_concepts(texts, top_k=8)
    pmid_concepts = dict(zip(pmids, concepts_per_doc))
    graph = build_cooccurrence_graph(pmid_concepts)

    db = lancedb.connect(lancedb_dir)
    table = db.open_table(table_name)
    rows = table.to_pandas()
    # average chunk vectors per pmid to get one vector per paper
    vectors, ordered_pmids = [], []
    for pmid in pmids:
        pmid_rows = rows[rows["pmid"] == pmid]
        if len(pmid_rows) == 0:
            continue
        avg_vec = np.mean(np.stack(pmid_rows["vector"].to_list()), axis=0)
        vectors.append(avg_vec.tolist())
        ordered_pmids.append(pmid)

    layout = reduce_and_cluster(vectors, ordered_pmids)

    summary = {
        "graph": graph,
        "layout": {
            pmid: {**layout[pmid], "title": by_pmid_title[pmid], "concepts": pmid_concepts[pmid]}
            for pmid in ordered_pmids
        },
    }

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(out_dir, "graph_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    return out_path


if __name__ == "__main__":
    from ingest.embed import load_config, resolve_active_table
    cfg = load_config()
    chunks_path = os.path.join(cfg["paths"]["chunks_dir"], "chunks.json")
    table_name = resolve_active_table(
        cfg["paths"]["lancedb_dir"], cfg["paths"]["active_table_marker"], cfg["rag"]["db_table_name"]
    )
    path = build_graph_summary(chunks_path, cfg["paths"]["lancedb_dir"], table_name, cfg["paths"]["graph_dir"])
    print(f"Wrote {path}")
