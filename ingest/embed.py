"""Embed chunks via Ollama and write a timestamped LanceDB table, publishing
it as the active table via an atomic marker-file swap (zero-downtime re-index
pattern: the API server always reads the marker, never a hardcoded table name)."""
import json
import os
from datetime import datetime
from pathlib import Path

import lancedb
import requests
import yaml


def load_config(path: str = "config.yml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def embed_text(text: str, ollama_url: str, model: str) -> list[float]:
    resp = requests.post(
        f"{ollama_url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def build_table(chunks_path: str, lancedb_dir: str, table_name: str, ollama_url: str, embed_model: str) -> str:
    with open(chunks_path) as f:
        chunks = json.load(f)

    rows = []
    for c in chunks:
        vector = embed_text(c["text"], ollama_url, embed_model)
        rows.append({
            "chunk_id": c["chunk_id"],
            "pmid": c["pmid"],
            "title": c["title"],
            "text": c["text"],
            "vector": vector,
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_name = f"{table_name}_{timestamp}"

    db = lancedb.connect(lancedb_dir)
    db.create_table(versioned_name, data=rows)
    return versioned_name


def publish_active_table(marker_path: str, table_name: str) -> None:
    Path(os.path.dirname(marker_path)).mkdir(parents=True, exist_ok=True)
    tmp_path = f"{marker_path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump({"active_table": table_name}, f)
    os.replace(tmp_path, marker_path)


def resolve_active_table(lancedb_dir: str, marker_path: str, default_table: str) -> str:
    if os.path.exists(marker_path):
        with open(marker_path) as f:
            data = json.load(f)
        return data.get("active_table", default_table)
    return default_table


if __name__ == "__main__":
    cfg = load_config()
    chunks_path = os.path.join(cfg["paths"]["chunks_dir"], "chunks.json")
    table_name = build_table(
        chunks_path,
        cfg["paths"]["lancedb_dir"],
        cfg["rag"]["db_table_name"],
        cfg["model"]["ollama_url"],
        cfg["model"]["embedding"],
    )
    publish_active_table(cfg["paths"]["active_table_marker"], table_name)
    print(f"Published active table: {table_name}")
