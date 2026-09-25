import numpy as np
from ingest.graph_cluster import extract_concepts, build_cooccurrence_graph, reduce_and_cluster

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
