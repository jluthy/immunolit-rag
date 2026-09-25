# tests/test_embed.py
import json
import os
from unittest.mock import patch, MagicMock
from ingest.embed import resolve_active_table, publish_active_table, load_config

def test_publish_and_resolve_active_table_roundtrip(tmp_path):
    marker = str(tmp_path / "active_table.json")
    publish_active_table(marker, "immunolit_abstracts_20260924_120000")
    result = resolve_active_table(str(tmp_path), marker, default_table="fallback")
    assert result == "immunolit_abstracts_20260924_120000"

def test_resolve_active_table_falls_back_when_marker_missing(tmp_path):
    marker = str(tmp_path / "does_not_exist.json")
    result = resolve_active_table(str(tmp_path), marker, default_table="fallback_table")
    assert result == "fallback_table"

def test_load_config_reads_yaml(tmp_path):
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text("paths:\n  raw_dir: data/raw\n")
    cfg = load_config(str(cfg_path))
    assert cfg["paths"]["raw_dir"] == "data/raw"
