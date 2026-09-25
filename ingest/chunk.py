"""Chunk abstracts into overlapping word windows. Abstracts are short, so most
will be a single chunk; the windowing only matters for a handful of longer ones."""
import json
import os
from pathlib import Path


def chunk_text(text: str, target_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if len(words) <= target_words:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


def chunk_records(records: list[dict], target_words: int, overlap_words: int) -> list[dict]:
    out = []
    for r in records:
        pieces = chunk_text(r["abstract"], target_words, overlap_words)
        for i, piece in enumerate(pieces):
            out.append({
                "chunk_id": f"{r['pmid']}_{i}",
                "pmid": r["pmid"],
                "title": r["title"],
                "text": piece,
            })
    return out


def chunk_all(in_path: str, out_dir: str, target_words: int, overlap_words: int) -> str:
    with open(in_path) as f:
        records = json.load(f)
    chunks = chunk_records(records, target_words, overlap_words)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(out_dir, "chunks.json")
    with open(out_path, "w") as f:
        json.dump(chunks, f, indent=2)
    return out_path


if __name__ == "__main__":
    import yaml
    with open("config.yml") as f:
        cfg = yaml.safe_load(f)
    in_path = os.path.join(cfg["paths"]["raw_dir"], "abstracts_raw.json")
    path = chunk_all(
        in_path,
        cfg["paths"]["chunks_dir"],
        cfg["rag"]["chunk_target_words"],
        cfg["rag"]["chunk_overlap_words"],
    )
    print(f"Wrote {path}")
