"""Single entrypoint for the ingest pipeline: fetch -> chunk -> embed -> graph -> publish."""
import argparse
import os
import sys

from ingest.fetch_pubmed import fetch_all, PUBMED_QUERIES, SEED_PMIDS
from ingest.chunk import chunk_all
from ingest.embed import load_config, build_table, publish_active_table, resolve_active_table
from ingest.graph_cluster import build_graph_summary


def cmd_fetch(cfg):
    path = fetch_all(PUBMED_QUERIES, cfg["paths"]["raw_dir"], seed_pmids=SEED_PMIDS)
    print(f"[fetch] wrote {path}")


def cmd_chunk(cfg):
    in_path = os.path.join(cfg["paths"]["raw_dir"], "abstracts_raw.json")
    path = chunk_all(in_path, cfg["paths"]["chunks_dir"], cfg["rag"]["chunk_target_words"], cfg["rag"]["chunk_overlap_words"])
    print(f"[chunk] wrote {path}")


def cmd_embed(cfg):
    chunks_path = os.path.join(cfg["paths"]["chunks_dir"], "chunks.json")
    table_name = build_table(
        chunks_path, cfg["paths"]["lancedb_dir"], cfg["rag"]["db_table_name"],
        cfg["model"]["ollama_url"], cfg["model"]["embedding"],
    )
    print(f"[embed] built table {table_name} (not yet published)")
    return table_name


def cmd_graph(cfg, table_name=None):
    chunks_path = os.path.join(cfg["paths"]["chunks_dir"], "chunks.json")
    active = table_name or resolve_active_table(
        cfg["paths"]["lancedb_dir"], cfg["paths"]["active_table_marker"], cfg["rag"]["db_table_name"]
    )
    path = build_graph_summary(chunks_path, cfg["paths"]["lancedb_dir"], active, cfg["paths"]["graph_dir"])
    print(f"[graph] wrote {path}")


def cmd_publish(cfg, table_name):
    publish_active_table(cfg["paths"]["active_table_marker"], table_name)
    print(f"[publish] active table is now {table_name}")


def cmd_status(cfg):
    active = resolve_active_table(
        cfg["paths"]["lancedb_dir"], cfg["paths"]["active_table_marker"], cfg["rag"]["db_table_name"]
    )
    print(f"[status] active table: {active}")


def main():
    parser = argparse.ArgumentParser(description="immunolit-rag ingest pipeline")
    parser.add_argument("verb", choices=["fetch", "chunk", "embed", "graph", "publish", "status", "all"])
    parser.add_argument("--table-name", help="required for `publish` verb")
    args = parser.parse_args()

    cfg = load_config()

    if args.verb == "fetch":
        cmd_fetch(cfg)
    elif args.verb == "chunk":
        cmd_chunk(cfg)
    elif args.verb == "embed":
        cmd_embed(cfg)
    elif args.verb == "graph":
        cmd_graph(cfg)
    elif args.verb == "publish":
        if not args.table_name:
            print("error: --table-name required for publish", file=sys.stderr)
            sys.exit(1)
        cmd_publish(cfg, args.table_name)
    elif args.verb == "status":
        cmd_status(cfg)
    elif args.verb == "all":
        cmd_fetch(cfg)
        cmd_chunk(cfg)
        table_name = cmd_embed(cfg)
        cmd_graph(cfg, table_name=table_name)
        cmd_publish(cfg, table_name)


if __name__ == "__main__":
    main()
