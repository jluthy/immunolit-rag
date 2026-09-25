from ingest.chunk import chunk_text, chunk_records

def test_chunk_text_short_text_single_chunk():
    text = "word " * 50
    chunks = chunk_text(text, target_words=250, overlap_words=30)
    assert len(chunks) == 1

def test_chunk_text_long_text_multiple_chunks_with_overlap():
    text = "word " * 600
    chunks = chunk_text(text, target_words=250, overlap_words=30)
    assert len(chunks) >= 2
    # verify overlap: last 30 words of chunk 0 appear at start of chunk 1
    words0 = chunks[0].split()
    words1 = chunks[1].split()
    assert words0[-30:] == words1[:30]

def test_chunk_records_produces_one_chunk_id_per_abstract_chunk():
    records = [{"pmid": "1", "title": "T", "abstract": "word " * 50, "query": "q"}]
    result = chunk_records(records, target_words=250, overlap_words=30)
    assert len(result) == 1
    assert result[0]["chunk_id"] == "1_0"
    assert result[0]["pmid"] == "1"
