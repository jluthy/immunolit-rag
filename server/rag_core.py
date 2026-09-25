"""Shared retrieval + prompt + generation logic used by the API server."""
import re

import lancedb
import requests

from ingest.embed import embed_text, resolve_active_table


def get_context(query: str, cfg: dict, k: int) -> list[dict]:
    vector = embed_text(query, cfg["model"]["ollama_url"], cfg["model"]["embedding"])
    table_name = resolve_active_table(
        cfg["paths"]["lancedb_dir"], cfg["paths"]["active_table_marker"], cfg["rag"]["db_table_name"]
    )
    db = lancedb.connect(cfg["paths"]["lancedb_dir"])
    table = db.open_table(table_name)
    results = table.search(vector).limit(k).to_list()
    return [
        {
            "chunk_id": r["chunk_id"],
            "pmid": r["pmid"],
            "title": r["title"],
            "text": r["text"],
            "score": r.get("_distance", 0.0),
        }
        for r in results
    ]


def format_context_block(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[PMID {c['pmid']}] {c['title']}\n{c['text']}")
    return "\n\n".join(parts)


def build_system_prompt(cfg: dict) -> str:
    return cfg["app"]["system_prompt"]


def chat(query: str, cfg: dict) -> dict:
    chunks = get_context(query, cfg, cfg["rag"]["retrieval_k"])
    context_block = format_context_block(chunks)
    system_prompt = build_system_prompt(cfg)

    resp = requests.post(
        f"{cfg['model']['ollama_url']}/api/chat",
        json={
            "model": cfg["model"]["llm"],
            "think": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {query}"},
            ],
            "stream": False,
            "options": {"temperature": 0.4},
        },
        timeout=60,
    )
    resp.raise_for_status()
    answer = resp.json()["message"]["content"]

    cited_pmids = set(re.findall(r"PMID\s*(\d+)", answer))
    retrieved_pmids = {c["pmid"] for c in chunks}
    citations = sorted(cited_pmids & retrieved_pmids) or sorted(retrieved_pmids)

    return {"answer": answer, "citations": citations, "retrieved": chunks}
