import json
import os

import lancedb
import numpy as np
from ingest.graph_cluster import extract_concepts, build_cooccurrence_graph, reduce_and_cluster, build_graph_summary

def test_extract_concepts_returns_top_terms_per_document():
    texts = [
        "myeloid derived suppressor cells sepsis immune dysfunction",
        "invariant NKT cells liver hepacivirus infection",
    ]
    result = extract_concepts(texts, top_k=3)
    assert len(result) == 2
    assert all(len(terms) <= 3 for terms in result)
    assert all(isinstance(terms, list) for terms in result)

def test_build_cooccurrence_graph_creates_edges_for_shared_concepts():
    pmid_concepts = {
        "1": ["mdsc", "sepsis", "flow"],
        "2": ["mdsc", "sepsis", "cytometry"],
        "3": ["inkt", "liver"],
    }
    graph = build_cooccurrence_graph(pmid_concepts)
    assert "nodes" in graph and "edges" in graph
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "mdsc" in node_ids and "sepsis" in node_ids
    mdsc_sepsis_edge = next(
        (e for e in graph["edges"] if {e["source"], e["target"]} == {"mdsc", "sepsis"}), None
    )
    assert mdsc_sepsis_edge is not None
    assert mdsc_sepsis_edge["weight"] == 2

def test_reduce_and_cluster_returns_2d_coords_and_labels():
    rng = np.random.RandomState(0)
    vectors = rng.rand(20, 32).tolist()
    pmids = [str(i) for i in range(20)]
    result = reduce_and_cluster(vectors, pmids)
    assert len(result) == 20
    for pmid in pmids:
        assert pmid in result
        assert "x" in result[pmid] and "y" in result[pmid] and "cluster" in result[pmid]

def test_build_graph_summary_writes_layout_and_graph(tmp_path):
    # Tiny fake corpus: matches the schema ingest/embed.py's build_table writes
    # (chunk_id, pmid, title, text, vector), plus a chunks.json for the pmid/text/title lookup.
    rng = np.random.RandomState(0)
    base_texts = [
        "myeloid derived suppressor cells sepsis immune",
        "invariant NKT cells liver hepacivirus infection",
        "flow cytometry immunophenotyping clustering",
        "CD8 T cell exhaustion chronic infection",
        "UMAP high dimensional single cell analysis",
        "cytokine signaling immune regulation pathway",
        "hepatitis C virus T cell response immunity",
        "Th1 Th2 cytokine balance infection response",
    ]
    chunks = [
        {"chunk_id": f"{i+1}_0", "pmid": str(i + 1), "title": f"Paper {i+1}", "text": text}
        for i, text in enumerate(base_texts)
    ]
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(json.dumps(chunks))

    rows = [
        {**c, "vector": rng.rand(16).tolist()}
        for c in chunks
    ]
    lancedb_dir = str(tmp_path / "lancedb")
    db = lancedb.connect(lancedb_dir)
    db.create_table("test_table", data=rows)

    out_dir = str(tmp_path / "graph_out")
    out_path = build_graph_summary(str(chunks_path), lancedb_dir, "test_table", out_dir)

    assert os.path.exists(out_path)
    with open(out_path) as f:
        summary = json.load(f)

    assert "graph" in summary and "layout" in summary
    assert set(summary["layout"].keys()) == {str(i + 1) for i in range(len(base_texts))}
    for pmid, entry in summary["layout"].items():
        assert "x" in entry and "y" in entry and "cluster" in entry
        assert "title" in entry and "concepts" in entry
