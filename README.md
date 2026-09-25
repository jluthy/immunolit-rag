# immunolit-rag

RAG + concept-graph search over open immunology literature. Ask a question, get a grounded, cited answer — and see how the underlying papers cluster.

**Live demo:** embedded on [jluthy.github.io](https://jluthy.github.io)

## Why RAG + graph, not just RAG

A plain RAG demo answers one question at a time. This project pairs retrieval with a second view: a UMAP + clustering layout of the entire corpus (the same dimensionality-reduction technique used in single-cell genomics analysis, applied here to literature embeddings), with the papers cited in your answer highlighted on the map. Retrieval answers "what does this paper say"; the graph answers "where does that sit relative to everything else in the corpus."

## Architecture

```
Browser (chat widget + cluster view, embedded on jluthy.github.io)
    │ HTTPS
    ▼
FastAPI backend (small cloud VM, running alongside Ollama)
    │
    ├── LanceDB — vector store for retrieval
    └── Ollama — qwen3:8b (generation) + nomic-embed-text (embeddings)

Offline ingest pipeline (run on demand, not per-request):
PubMed E-utilities → chunk → embed → concept co-occurrence graph + UMAP/cluster → publish
```

Corpus: ~300-800 curated PubMed abstracts (title + abstract only — no full-text scraping, no non-open-access sources), scoped to a fixed list of immunology search terms drawn from my own two published papers, plus the papers themselves as seed documents.

## Eval

No LLM-judge — a 20-25 item hand-curated golden QA set is scored with pure, deterministic functions: citation-format compliance, citation-grounding ratio (anti-hallucination — did the model cite a paper it actually retrieved), and embedding similarity against a reference answer. Latest report: `eval/reports/latest_eval_report.md`.

## Related work

I built a production version of this same architecture at my day job (Becton Dickinson/FlowJo) — a RAG Slack bot over FlowJo's technical documentation, in active use by our support team. That system's content is proprietary and isn't public, so this project rebuilds the same engineering pattern (LanceDB retrieval, zero-downtime table publishing, Ollama-served generation) against open literature instead.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.dev.txt
ollama pull qwen3:8b && ollama pull nomic-embed-text
python -m ingest.cli all
uvicorn server.api:app --reload --port 8000
pytest
```
