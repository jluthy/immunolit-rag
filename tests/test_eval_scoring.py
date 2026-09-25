from eval.eval_scoring import citation_format_score, citation_grounding_ratio, answer_similarity

def test_citation_format_score_full_marks_when_all_citations_well_formed():
    answer = "iNKT cells regulate liver injury (PMID 36159876)."
    assert citation_format_score(answer) == 1.0

def test_citation_format_score_zero_when_no_citations_present():
    answer = "iNKT cells regulate liver injury."
    assert citation_format_score(answer) == 0.0

def test_citation_grounding_ratio_penalizes_hallucinated_citation():
    citations = ["1", "2", "999999"]
    retrieved = ["1", "2", "3"]
    ratio = citation_grounding_ratio(citations, retrieved)
    assert abs(ratio - (2 / 3)) < 1e-6

def test_citation_grounding_ratio_full_marks_when_all_grounded():
    assert citation_grounding_ratio(["1", "2"], ["1", "2", "3"]) == 1.0

def test_answer_similarity_identical_vectors_returns_one():
    v = [1.0, 0.0, 0.0]
    assert abs(answer_similarity(v, v) - 1.0) < 1e-6

def test_answer_similarity_orthogonal_vectors_returns_zero():
    assert abs(answer_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6
