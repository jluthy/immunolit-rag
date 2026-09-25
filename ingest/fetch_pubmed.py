"""Fetch open-access PubMed abstracts for a curated set of immunology queries."""
import json
import os
import time
from pathlib import Path

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_TOOL = "immunolit-rag"
NCBI_EMAIL = "jluthy123@gmail.com"

PUBMED_QUERIES = [
    "myeloid-derived suppressor cells sepsis",
    "PMN-MDSC critical illness",
    "MDSC flow cytometry immunophenotyping",
    "FlowSOM clustering immune cells",
    "UMAP high-dimensional flow cytometry",
    "immune dysfunction sepsis critical illness",
    "immunosuppression septic shock",
    "invariant NKT cells liver",
    "iNKT cells type 2 immunity",
    "hepatic immune regulation",
    "hepacivirus infection immunity",
    "hepatitis C virus T cell response",
    "CD8 T cell exhaustion chronic infection",
    "liver injury immune regulation",
    "CD1d restricted NKT cells",
    "Th1 Th2 cytokine balance infection",
    "T cell receptor antigen recognition",
    "high-dimensional flow cytometry immunology",
    "cytokine signaling immune regulation",
    "antiviral CD8 T cell immunity",
]

SEED_PMIDS = ["36466851", "36159876"]  # Josh's own 2 published papers


def _get_with_retry(url: str, params: dict, timeout: int = 30, max_attempts: int = 3):
    """GET with simple exponential backoff for transient failures."""
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException:
            if attempt >= max_attempts:
                raise
            time.sleep(2 ** attempt)


def esearch(query: str, retmax: int = 40) -> list[str]:
    resp = _get_with_retry(
        f"{EUTILS_BASE}/esearch.fcgi",
        params={
            "db": "pubmed", "term": query, "retmax": retmax, "retmode": "json",
            "tool": NCBI_TOOL, "email": NCBI_EMAIL,
        },
    )
    return resp.json()["esearchresult"]["idlist"]


def efetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Returns {pmid: abstract_text}. Skips PMIDs with no abstract."""
    if not pmids:
        return {}
    resp = _get_with_retry(
        f"{EUTILS_BASE}/efetch.fcgi",
        params={
            "db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml",
            "tool": NCBI_TOOL, "email": NCBI_EMAIL,
        },
    )
    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp.text)
    out = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None:
            continue
        pmid = pmid_el.text
        abstract_parts = article.findall(".//AbstractText")
        if not abstract_parts:
            continue
        sections = []
        for el in abstract_parts:
            text = "".join(el.itertext())
            label = el.get("Label")
            if label:
                text = f"{label}: {text}"
            sections.append(text)
        out[pmid] = " ".join(sections)
    return out


def parse_esummary_response(data: dict) -> list[dict]:
    uids = data["result"]["uids"]
    return [{"pmid": uid, "title": data["result"][uid]["title"]} for uid in uids]


def esummary_titles(pmids: list[str]) -> dict[str, str]:
    if not pmids:
        return {}
    resp = _get_with_retry(
        f"{EUTILS_BASE}/esummary.fcgi",
        params={
            "db": "pubmed", "id": ",".join(pmids), "retmode": "json",
            "tool": NCBI_TOOL, "email": NCBI_EMAIL,
        },
    )
    parsed = parse_esummary_response(resp.json())
    return {r["pmid"]: r["title"] for r in parsed}


def dedupe_records(records: list[dict]) -> list[dict]:
    seen = {}
    for r in records:
        seen[r["pmid"]] = r
    return list(seen.values())


def fetch_all(queries: list[str], out_dir: str, seed_pmids: list[str] | None = None) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(out_dir, "abstracts_raw.json")

    all_records = []

    def _write_progress():
        deduped = dedupe_records(all_records)
        with open(out_path, "w") as f:
            json.dump(deduped, f, indent=2)

    for query in queries:
        pmids = esearch(query)
        titles = esummary_titles(pmids)
        abstracts = efetch_abstracts(pmids)
        for pmid in pmids:
            abstract = abstracts.get(pmid, "")
            if pmid in abstracts and len(abstract.split()) >= 20:
                all_records.append({
                    "pmid": pmid,
                    "title": titles.get(pmid, ""),
                    "abstract": abstract,
                    "query": query,
                })
        time.sleep(0.4)  # NCBI rate limit courtesy
        _write_progress()  # incremental write so a late failure doesn't lose earlier progress

    if seed_pmids:
        titles = esummary_titles(seed_pmids)
        abstracts = efetch_abstracts(seed_pmids)
        for pmid in seed_pmids:
            abstract = abstracts.get(pmid, "")
            if pmid in abstracts and len(abstract.split()) >= 20:
                all_records.append({
                    "pmid": pmid,
                    "title": titles.get(pmid, ""),
                    "abstract": abstract,
                    "query": "seed:josh-luthy-publication",
                })
        _write_progress()

    return out_path


if __name__ == "__main__":
    import yaml
    with open("config.yml") as f:
        cfg = yaml.safe_load(f)
    path = fetch_all(PUBMED_QUERIES, cfg["paths"]["raw_dir"], seed_pmids=SEED_PMIDS)
    print(f"Wrote {path}")
