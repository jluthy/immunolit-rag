# eval/eval_harness.py
"""Runs the golden QA set through the live RAG pipeline and scores each answer."""
import json
import os
from datetime import datetime
from pathlib import Path

from eval.eval_scoring import citation_format_score, citation_grounding_ratio, answer_similarity
from ingest.embed import embed_text, load_config
from server.rag_core import chat


def run_eval(golden_path: str, cfg: dict) -> list[dict]:
    with open(golden_path) as f:
        golden_items = json.load(f)

    results = []
    for item in golden_items:
        result = chat(item["query"], cfg)
        retrieved_pmids = [c["pmid"] for c in result["retrieved"]]

        answer_vec = embed_text(result["answer"], cfg["model"]["ollama_url"], cfg["model"]["embedding"])
        ref_vec = embed_text(item["reference_answer"], cfg["model"]["ollama_url"], cfg["model"]["embedding"])

        results.append({
            "query": item["query"],
            "answer": result["answer"],
            "citations": result["citations"],
            "citation_format_score": citation_format_score(result["answer"]),
            "citation_grounding_ratio": citation_grounding_ratio(result["citations"], retrieved_pmids),
            "answer_similarity": answer_similarity(answer_vec, ref_vec),
        })
    return results


def write_report(results: list[dict], out_path: str) -> None:
    Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)
    avg = lambda key: sum(r[key] for r in results) / len(results) if results else 0.0

    lines = [
        f"# Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Items: {len(results)}",
        f"- Avg citation format score: {avg('citation_format_score'):.2f}",
        f"- Avg citation grounding ratio: {avg('citation_grounding_ratio'):.2f}",
        f"- Avg answer similarity: {avg('answer_similarity'):.2f}",
        "",
        "## Per-item results",
        "",
    ]
    for r in results:
        lines.append(f"### {r['query']}")
        lines.append(f"- Citation format: {r['citation_format_score']:.2f}")
        lines.append(f"- Grounding ratio: {r['citation_grounding_ratio']:.2f}")
        lines.append(f"- Answer similarity: {r['answer_similarity']:.2f}")
        lines.append(f"- Answer: {r['answer'][:300]}...")
        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    cfg = load_config()
    results = run_eval("eval/golden_qa.json", cfg)
    write_report(results, "eval/reports/latest_eval_report.md")
    print(f"Wrote eval/reports/latest_eval_report.md ({len(results)} items)")
