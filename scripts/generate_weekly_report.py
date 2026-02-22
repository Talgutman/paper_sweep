#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "paper-sweep-weekly-agent/1.0"
TIMEZONE = ZoneInfo("Asia/Jerusalem")

LANE_QUERIES = {
    "cancer": (
        "(("
        "cancer[Title/Abstract] OR oncology[Title/Abstract] OR neoplasm[Title/Abstract] "
        'OR "liquid biopsy"[Title/Abstract] OR immunotherapy[Title/Abstract] '
        'OR "cell therapy"[Title/Abstract] OR "antibody-drug conjugate"[Title/Abstract]'
        ") AND ("
        '"N Engl J Med"[Journal] OR "Lancet Oncol"[Journal] OR "J Clin Oncol"[Journal] '
        'OR "Cancer Discov"[Journal] OR "Ann Oncol"[Journal] OR "JAMA Oncol"[Journal] '
        'OR "Nature Cancer"[Journal] OR "Nat Med"[Journal]'
        ")) AND {date_clause}"
    ),
    "computational_biology": (
        "(("
        '"computational biology"[Title/Abstract] OR "machine learning"[Title/Abstract] '
        'OR "deep learning"[Title/Abstract] OR "single-cell"[Title/Abstract] '
        'OR "spatial transcriptomics"[Title/Abstract] OR "genome editing"[Title/Abstract] '
        "OR CRISPR[Title/Abstract]"
        ") AND ("
        '"Nature Methods"[Journal] OR "Nat Biotechnol"[Journal] OR "Genome Biol"[Journal] '
        'OR "Bioinformatics"[Journal] OR "PLoS Comput Biol"[Journal] '
        'OR "Cell Syst"[Journal] OR "Nat Comput Sci"[Journal]'
        ")) AND {date_clause}"
    ),
    "exceptional_medicine": (
        "("
        'alzheimer*[Title/Abstract] OR crohn*[Title/Abstract] OR parkinson*[Title/Abstract] '
        'OR "heart failure"[Title/Abstract] OR stroke[Title/Abstract] OR diabetes[Title/Abstract] '
        'OR "gene therapy"[Title/Abstract] OR "first-in-class"[Title/Abstract] '
        'OR "phase III"[Title/Abstract] OR "phase 3"[Title/Abstract]'
        ") AND "
        '("N Engl J Med"[Journal] OR Lancet[Journal] OR JAMA[Journal] OR "Nat Med"[Journal]) '
        "AND {date_clause} AND NOT "
        "(cancer[Title/Abstract] OR oncology[Title/Abstract] OR tumor[Title/Abstract])"
    ),
}

SECTION_META = {
    "cancer": {"title": "Cancer", "min": 5, "max": 8},
    "computational_biology": {"title": "Computational Biology", "min": 4, "max": 6},
    "exceptional_medicine": {"title": "Exceptional Non-Cancer Medicine", "min": 1, "max": 3},
}

TOP_JOURNAL_HINTS = (
    "new england journal of medicine",
    "nejm",
    "lancet",
    "jama",
    "nature",
    "cell",
    "science",
    "annals of oncology",
    "journal of clinical oncology",
    "cancer discovery",
)

INCLUSION_SCORE = {
    "cancer": 65,
    "computational_biology": 62,
    "exceptional_medicine": 75,
}

LOW_SIGNAL_TITLE_TERMS = (
    "study protocol",
    "trial protocol",
    "protocol for",
    "rationale and design",
    "scoping review",
    "narrative review",
    "author correction",
    "corrigendum",
    "commentary",
    "editorial",
)

ONCOLOGY_TERMS = (
    "cancer",
    "oncology",
    "tumor",
    "neoplasm",
    "metast",
    "carcinoma",
    "leukemia",
    "lymphoma",
    "myeloma",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly research report markdown.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown path. Defaults to reports/weekly-YYYY-MM-DD.md (Israel date).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback window in days.",
    )
    parser.add_argument(
        "--retmax",
        type=int,
        default=40,
        help="Maximum PubMed candidates fetched per lane before ranking.",
    )
    parser.add_argument(
        "--ncbi-email",
        default=None,
        help="Optional contact email for NCBI requests.",
    )
    return parser.parse_args()


def ncbi_request(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    query = {"tool": "paper_sweep", **params}
    query_str = urllib.parse.urlencode(query)
    url = f"{API_BASE}/{endpoint}?{query_str}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    if params.get("retmode") == "xml":
        return {"xml": body}
    return json.loads(body)


def build_date_clause(days: int) -> tuple[str, dt.date, dt.date]:
    end = dt.datetime.now(tz=TIMEZONE).date()
    start = end - dt.timedelta(days=days)
    clause = f'("{start:%Y/%m/%d}"[Date - Publication] : "{end:%Y/%m/%d}"[Date - Publication])'
    return clause, start, end


def pubmed_search(query: str, retmax: int, ncbi_email: str | None) -> list[str]:
    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "pub+date",
    }
    if ncbi_email:
        params["email"] = ncbi_email
    payload = ncbi_request("esearch.fcgi", params)
    return payload.get("esearchresult", {}).get("idlist", [])


def pubmed_summaries(pmids: list[str], ncbi_email: str | None) -> dict[str, dict[str, Any]]:
    if not pmids:
        return {}
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if ncbi_email:
        params["email"] = ncbi_email
    payload = ncbi_request("esummary.fcgi", params)
    result = payload.get("result", {})
    return {pmid: result.get(pmid, {}) for pmid in pmids}


def pubmed_abstracts(pmids: list[str], ncbi_email: str | None) -> dict[str, str]:
    if not pmids:
        return {}
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    if ncbi_email:
        params["email"] = ncbi_email
    xml_text = ncbi_request("efetch.fcgi", params)["xml"]

    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    abstracts: dict[str, str] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        if pmid_elem is None or not pmid_elem.text:
            continue
        pmid = pmid_elem.text.strip()
        abstract_parts: list[str] = []
        for part in article.findall(".//Abstract/AbstractText"):
            text = "".join(part.itertext()).strip()
            if text:
                abstract_parts.append(text)
        abstracts[pmid] = " ".join(abstract_parts)
    return abstracts


def extract_doi(summary: dict[str, Any]) -> str | None:
    article_ids = summary.get("articleids", [])
    for item in article_ids:
        if item.get("idtype") == "doi":
            value = item.get("value")
            if value:
                return value
    return None


def sentence(text: str) -> str:
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0].strip()


def infer_evidence_level(title: str, abstract_text: str) -> str:
    haystack = f"{title} {abstract_text}".lower()
    if "guideline" in haystack or "approval" in haystack:
        return "Regulatory/Guideline"
    if "phase iii" in haystack or "phase 3" in haystack or "randomized" in haystack:
        return "Phase III/Randomized"
    if "phase ii" in haystack or "phase 2" in haystack:
        return "Phase II"
    if "preprint" in haystack:
        return "Preprint"
    return "Observational/Other"


def score_item(lane: str, title: str, journal: str, abstract_text: str, pubtypes: list[str]) -> int:
    haystack = f"{title} {abstract_text}".lower()
    journal_l = journal.lower()
    score = 50

    if any(hint in journal_l for hint in TOP_JOURNAL_HINTS):
        score += 15
    if "phase iii" in haystack or "phase 3" in haystack:
        score += 20
    if "randomized" in haystack:
        score += 10
    if "trial" in haystack:
        score += 8
    if "first-in-class" in haystack:
        score += 12
    if "liquid biopsy" in haystack:
        score += 8
    if "single-cell" in haystack or "spatial transcriptomics" in haystack:
        score += 8
    if "crispr" in haystack or "genome editing" in haystack:
        score += 8

    if lane == "exceptional_medicine":
        score += 5

    pubtypes_l = " ".join(pubtypes).lower()
    if "review" in pubtypes_l or "meta-analysis" in pubtypes_l:
        score -= 20
    if "protocol" in haystack:
        score -= 25
    if not abstract_text:
        score -= 6

    return max(0, min(100, score))


def is_low_signal_item(title: str, pubtypes: list[str]) -> bool:
    title_l = title.lower()
    pubtypes_l = " ".join(pubtypes).lower()
    if any(term in title_l for term in LOW_SIGNAL_TITLE_TERMS):
        return True
    if "protocol" in title_l:
        return True
    if "review" in pubtypes_l and "systematic review" not in pubtypes_l:
        return True
    return False


def is_oncology_item(title: str, abstract_text: str) -> bool:
    haystack = f"{title} {abstract_text}".lower()
    return any(term in haystack for term in ONCOLOGY_TERMS)


def build_why_matters(lane: str, title: str, abstract_text: str) -> list[str]:
    haystack = f"{title} {abstract_text}".lower()
    points: list[str] = []

    if lane == "cancer":
        points.append("Potential downstream relevance for oncology diagnostics, treatment, or patient stratification.")
    elif lane == "computational_biology":
        points.append("Could influence computational biology workflows, model design, or multi-omics interpretation.")
    else:
        points.append("Signals potential impact beyond oncology with broad translational relevance.")

    if "phase iii" in haystack or "phase 3" in haystack or "randomized" in haystack:
        points.append("Late-stage or randomized evidence may have near-term implications for practice.")
    if "single-cell" in haystack or "spatial transcriptomics" in haystack:
        points.append("Advances single-cell/spatial analysis capabilities with broad reuse potential.")
    if "crispr" in haystack or "genome editing" in haystack:
        points.append("Genome-editing progress may reshape therapeutic and functional genomics pipelines.")
    if "liquid biopsy" in haystack:
        points.append("Non-invasive detection signal may expand early diagnosis and monitoring options.")
    if len(points) < 2:
        points.append("Worth tracking for follow-up validation, replication, and implementation details.")
    return points[:4]


def build_caveats(title: str, abstract_text: str, evidence_level: str) -> list[str]:
    caveats: list[str] = []
    haystack = f"{title} {abstract_text}".lower()
    if not abstract_text:
        caveats.append("Abstract unavailable from PubMed metadata; interpret impact cautiously.")
    if evidence_level in {"Phase II", "Observational/Other", "Preprint"}:
        caveats.append("Evidence is not definitive for immediate clinical adoption.")
    if "protocol" in haystack or "design" in haystack:
        caveats.append("May describe planned methodology rather than completed outcomes.")
    if "review" in haystack:
        caveats.append("Review-type content summarizes prior work and may not represent a new finding.")
    if not caveats:
        caveats.append("Full-text methods and subgroup details should be checked before action.")
    return caveats[:3]


def fetch_lane_items(lane: str, query: str, retmax: int, ncbi_email: str | None) -> list[dict[str, Any]]:
    pmids = pubmed_search(query, retmax=retmax, ncbi_email=ncbi_email)
    summaries = pubmed_summaries(pmids, ncbi_email=ncbi_email)
    abstracts = pubmed_abstracts(pmids, ncbi_email=ncbi_email)

    items: list[dict[str, Any]] = []
    for pmid in pmids:
        summary = summaries.get(pmid, {})
        title = summary.get("title", "").strip()
        if not title:
            continue
        journal = summary.get("fulljournalname", "Unknown journal")
        pubtypes = summary.get("pubtype", []) or []
        if is_low_signal_item(title, pubtypes):
            continue
        abstract_text = abstracts.get(pmid, "")
        if lane == "exceptional_medicine" and is_oncology_item(title, abstract_text):
            continue
        doi = extract_doi(summary)
        score = score_item(lane, title, journal, abstract_text, pubtypes)
        evidence_level = infer_evidence_level(title, abstract_text)
        finding = sentence(abstract_text) or sentence(title)
        items.append(
            {
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "pubdate": summary.get("pubdate", "Unknown date"),
                "doi": doi,
                "score": score,
                "evidence_level": evidence_level,
                "finding": finding,
                "why_matters": build_why_matters(lane, title, abstract_text),
                "caveats": build_caveats(title, abstract_text, evidence_level),
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def render_item(index: int, item: dict[str, Any]) -> list[str]:
    lines = [
        f"### {index}. {item['title']}",
        f"- One-sentence finding: {item['finding']}",
        "- Why it matters:",
    ]
    lines.extend([f"  - {p}" for p in item["why_matters"]])
    lines.append(f"- Evidence level: {item['evidence_level']}")
    lines.append("- Caveats:")
    lines.extend([f"  - {c}" for c in item["caveats"]])
    lines.append(f"- Score: {item['score']}/100")
    lines.append("- Source links:")
    lines.append(f"  - PubMed: {item['pubmed_url']}")
    if item["doi"]:
        lines.append(f"  - DOI: https://doi.org/{item['doi']}")
    lines.append("")
    return lines


def generate_report(output_path: Path, days: int, retmax: int, ncbi_email: str | None) -> None:
    date_clause, start_date, end_date = build_date_clause(days)
    now = dt.datetime.now(tz=TIMEZONE)

    lane_results: dict[str, list[dict[str, Any]]] = {}
    for lane, query_template in LANE_QUERIES.items():
        query = query_template.format(date_clause=date_clause)
        lane_results[lane] = fetch_lane_items(lane, query=query, retmax=retmax, ncbi_email=ncbi_email)

    selected: dict[str, list[dict[str, Any]]] = {}
    for lane, meta in SECTION_META.items():
        thresholded = [item for item in lane_results[lane] if item["score"] >= INCLUSION_SCORE[lane]]
        selected[lane] = thresholded[: meta["max"]]

    report_lines: list[str] = [
        "# Weekly Research Intelligence Report",
        "",
        f"- Generated: {now:%Y-%m-%d %H:%M %Z}",
        f"- Window: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}",
        "- Scope weights: Cancer 50%, Computational Biology 35%, Exceptional Medicine 15%",
        "- Method note: Automated first-pass from PubMed. Manually verify practice-changing claims.",
        "",
        "## Executive Summary",
    ]

    summary_bullets: list[str] = []
    for lane in ("cancer", "computational_biology", "exceptional_medicine"):
        lane_items = selected[lane]
        if not lane_items:
            summary_bullets.append(f"- {SECTION_META[lane]['title']}: no qualifying items found in this run.")
            continue
        top = lane_items[0]
        summary_bullets.append(
            f"- {SECTION_META[lane]['title']}: top signal in {top['journal']} -> {top['title']} (score {top['score']}/100)."
        )
    report_lines.extend(summary_bullets)
    report_lines.append("")

    for lane in ("cancer", "computational_biology", "exceptional_medicine"):
        report_lines.append(f"## {SECTION_META[lane]['title']}")
        lane_items = selected[lane]
        if not lane_items:
            report_lines.append("- No items selected this week.")
            report_lines.append("")
            continue
        for idx, item in enumerate(lane_items, start=1):
            report_lines.extend(render_item(idx, item))

    report_lines.extend(
        [
            "## Watchlist",
            "- Track large congress releases (ASCO/ESMO/AACR) with strict practice-change filters.",
            "- Track regulator updates (FDA/EMA) for approvals affecting oncology and adjacent fields.",
            "- Track high-impact preprints only when methodological rigor and downstream relevance are clear.",
            "",
            "## References",
            "- PubMed E-utilities API: https://www.ncbi.nlm.nih.gov/books/NBK25501/",
            "- Source registry: config/sources.yaml",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    today = dt.datetime.now(tz=TIMEZONE).date()
    output = Path(args.output or f"reports/weekly-{today:%Y-%m-%d}.md")
    generate_report(output_path=output, days=args.days, retmax=args.retmax, ncbi_email=args.ncbi_email)
    print(json.dumps({"report_path": str(output)}))


if __name__ == "__main__":
    main()
