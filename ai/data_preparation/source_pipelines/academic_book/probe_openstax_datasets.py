import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from datasets import load_dataset
from huggingface_hub import HfApi


HERE = os.path.dirname(os.path.abspath(__file__))


def _norm_ws(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def _word_count(s: str) -> int:
    s = _norm_ws(s)
    return 0 if not s else len(s.split())


def _safe_get(d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _dataset_card_info(repo_id: str) -> Dict[str, Any]:
    api = HfApi()
    info = api.dataset_info(repo_id=repo_id)
    card_raw = getattr(info, "cardData", None) or {}
    # huggingface_hub returns DatasetCardData (mapping-like), not always a plain dict
    try:
        card = dict(card_raw)
    except Exception:
        card = card_raw if isinstance(card_raw, dict) else {}
    return {
        "repo_id": repo_id,
        "sha": getattr(info, "sha", None),
        "last_modified": (
            getattr(info, "lastModified", None).isoformat()
            if hasattr(getattr(info, "lastModified", None), "isoformat")
            else getattr(info, "lastModified", None)
        ),
        "license": card.get("license") or card.get("licenses") or None,
        "source": card.get("source") or card.get("sources") or None,
        "homepage": card.get("homepage") or None,
        "citation": card.get("citation") or None,
        "cardData_keys": sorted(list(card.keys())),
    }


def _infer_text_and_id(repo_id: str, row: Dict[str, Any], row_idx: int) -> Tuple[Optional[str], str, Dict[str, Any]]:
    """
    Returns: (text, article_id, extra_metadata)
    NOTE: This is only for probing, not final extraction.
    """
    # Common candidates
    text = _safe_get(
        row,
        [
            "text",
            "content",
            "paragraph",
            "paragraph_text",
            "body",
            "html",
            "plain_text",
        ],
    )
    title = _safe_get(row, ["title", "section_title", "heading", "name"])
    book = _safe_get(row, ["book", "book_title"])
    chapter = _safe_get(row, ["chapter", "chapter_title", "chapter_name", "chapter_number"])
    section = _safe_get(row, ["section", "section_id", "section_number"])

    parts = [str(x) for x in [repo_id, book, chapter, section, title, row.get("id"), row.get("uid"), row_idx] if x not in (None, "")]
    article_id = "|".join(parts)

    meta = {
        "title": title,
        "book": book,
        "chapter": chapter,
        "section": section,
        "url": _safe_get(row, ["url", "source_url", "link"]),
    }
    return (text if isinstance(text, str) else None), article_id, meta


def _bucket(wc: int) -> Optional[str]:
    if 250 <= wc <= 499:
        return "short_250_499"
    if 500 <= wc <= 800:
        return "medium_500_800"
    if 801 <= wc <= 1200:
        return "long_801_1200"
    return None


def probe_dataset(repo_id: str, max_scan_per_split: int = 20000) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "repo_id": repo_id,
        "splits": {},
        "card": _dataset_card_info(repo_id),
    }

    ds_dict = load_dataset(repo_id)
    for split in ds_dict.keys():
        # For very large datasets, use streaming to avoid full materialization.
        # We only need a bounded scan for probing.
        try:
            ds_stream = load_dataset(repo_id, split=split, streaming=True)
            ds = ds_stream
            scan_n = max_scan_per_split
            fields = None
            iter_rows = enumerate(ds)
        except Exception:
            ds = ds_dict[split]
            scan_n = min(max_scan_per_split, len(ds)) if hasattr(ds, "__len__") else max_scan_per_split
            fields = list(ds.features.keys()) if hasattr(ds, "features") else None
            iter_rows = ((i, ds[i]) for i in range(scan_n))

        buckets = {"short_250_499": 0, "medium_500_800": 0, "long_801_1200": 0}
        nonempty = 0
        examples: List[Dict[str, Any]] = []

        for i, row in iter_rows:
            if i >= scan_n:
                break
            text, article_id, meta = _infer_text_and_id(repo_id, row, i)
            wc = _word_count(text or "")
            if wc > 0:
                nonempty += 1
            b = _bucket(wc)
            if b:
                buckets[b] += 1
            if len(examples) < 3 and wc >= 200:
                examples.append(
                    {
                        "row_idx": i,
                        "article_id": article_id,
                        "word_count": wc,
                        "meta": meta,
                        "text_preview": _norm_ws((text or "")[:400]),
                    }
                )

        out["splits"][split] = {
            "num_rows": len(ds_dict[split]) if split in ds_dict and hasattr(ds_dict[split], "__len__") else None,
            "scan_n": scan_n,
            "fields": fields,
            "nonempty_rows_in_scan": nonempty,
            "bucket_counts_in_scan": buckets,
            "examples": examples,
        }

    return out


def main():
    targets = [
        "crumb/openstax-text",
        "HuggingFaceTB/openstax_paragraphs",
    ]

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cwd": os.getcwd(),
        "targets": targets,
        "results": [],
    }

    for repo_id in targets:
        try:
            report["results"].append(probe_dataset(repo_id))
        except Exception as e:
            report["results"].append({"repo_id": repo_id, "error": repr(e)})

    report_path = os.path.join(HERE, "probe_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Human-readable license/source note
    md_lines = [
        "## Sources and licenses (from HuggingFace dataset cards)",
        "",
        f"- Generated at: `{report['generated_at']}`",
        "",
    ]
    for r in report["results"]:
        repo_id = r.get("repo_id")
        if r.get("error"):
            md_lines += [f"### {repo_id}", "", f"- **Error**: `{r['error']}`", ""]
            continue
        card = r.get("card", {})
        md_lines += [
            f"### {repo_id}",
            "",
            f"- **HuggingFace**: `{('https://huggingface.co/datasets/' + repo_id)}`",
            f"- **License (cardData)**: `{card.get('license')}`",
            f"- **Homepage (cardData)**: `{card.get('homepage')}`",
            f"- **Source (cardData)**: `{card.get('source')}`",
            "",
        ]
    md_path = os.path.join(HERE, "sources_licenses.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines).strip() + "\n")

    print(f"Wrote: {report_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
