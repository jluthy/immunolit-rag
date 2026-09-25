import json
from unittest.mock import patch, MagicMock
from ingest.fetch_pubmed import parse_esummary_response, dedupe_records

def test_parse_esummary_response_extracts_title_and_pmid():
    fake_json = {
        "result": {
            "uids": ["12345"],
            "12345": {"uid": "12345", "title": "A Test Paper Title."}
        }
    }
    result = parse_esummary_response(fake_json)
    assert result == [{"pmid": "12345", "title": "A Test Paper Title."}]

def test_dedupe_records_removes_duplicate_pmids():
    records = [
        {"pmid": "1", "title": "A", "abstract": "x", "query": "q1"},
        {"pmid": "1", "title": "A", "abstract": "x", "query": "q2"},
        {"pmid": "2", "title": "B", "abstract": "y", "query": "q1"},
    ]
    result = dedupe_records(records)
    assert len(result) == 2
    assert {r["pmid"] for r in result} == {"1", "2"}
