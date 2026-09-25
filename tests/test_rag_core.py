from unittest.mock import patch, MagicMock
from server.rag_core import build_system_prompt, format_context_block

def test_build_system_prompt_includes_citation_instruction():
    cfg = {"app": {"system_prompt": "You are a research assistant. Cite PubMed IDs."}}
    prompt = build_system_prompt(cfg)
    assert "Cite PubMed IDs" in prompt

def test_format_context_block_includes_pmid_and_text():
    chunks = [{"pmid": "123", "title": "Test Paper", "text": "Some finding.", "chunk_id": "123_0", "score": 0.9}]
    block = format_context_block(chunks)
    assert "123" in block
    assert "Test Paper" in block
    assert "Some finding." in block
