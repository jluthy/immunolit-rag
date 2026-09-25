"""Pure, deterministic eval scoring functions. No LLM judge, by design:
cheaper, reproducible, and easier to defend as a rigorous artifact."""
import re

import numpy as np


def citation_format_score(answer: str) -> float:
    """Fraction of citation-shaped mentions that match the expected 'PMID <digits>' format.
    If there are no citation-like mentions at all, returns 0.0 (an answer making
    factual claims with zero citations is a failure for this use case)."""
    well_formed = re.findall(r"PMID\s*\d+", answer)
    malformed_markers = re.findall(r"\bPMID\b(?!\s*\d)", answer)
    total = len(well_formed) + len(malformed_markers)
    if total == 0:
        return 0.0
    return len(well_formed) / total


def citation_grounding_ratio(citations: list[str], retrieved_pmids: list[str]) -> float:
    """Fraction of cited PMIDs that were actually among the retrieved chunks —
    an anti-hallucination check for citations that name a source not in context."""
    if not citations:
        return 0.0
    retrieved_set = set(retrieved_pmids)
    grounded = sum(1 for c in citations if c in retrieved_set)
    return grounded / len(citations)


def answer_similarity(answer_vector: list[float], reference_vector: list[float]) -> float:
    a = np.array(answer_vector)
    b = np.array(reference_vector)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
