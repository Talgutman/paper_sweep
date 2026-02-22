#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path
import urllib.request

PRICING_URL = "https://resend.com/pricing"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect changes on Resend pricing page.")
    parser.add_argument(
        "--snapshot",
        default="state/resend_pricing_snapshot.json",
        help="Path to local snapshot file.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_text(raw_html: str) -> str:
    no_code = re.sub(
        r"(?is)<(script|style|noscript).*?>.*?</\1>",
        " ",
        raw_html,
    )
    no_tags = re.sub(r"(?is)<[^>]+>", " ", no_code)
    return html.unescape(no_tags)


def extract_free_section(text: str) -> str:
    low = text.lower()
    idx = low.find("free")
    if idx == -1:
        return text[:2000]
    return text[idx : idx + 2400]


def extract_daily_limit(section: str) -> str | None:
    patterns = (
        r"daily\s+limit\s+(\d[\d,]*)",
        r"(\d[\d,]*)\s*emails?\s*(?:/|per)\s*day",
    )
    for pattern in patterns:
        match = re.search(pattern, section, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
    return None


def extract_monthly_limit(section: str) -> str | None:
    patterns = (
        r"monthly\s+limit\s+(\d[\d,]*)",
        r"(\d[\d,]*)\s*emails?\s*(?:/|per)\s*month",
    )
    for pattern in patterns:
        match = re.search(pattern, section, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
    return None


def load_snapshot(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_github_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}<<EOF\n{value}\nEOF\n")


def main() -> None:
    args = parse_args()
    snapshot_path = Path(args.snapshot)

    request = urllib.request.Request(PRICING_URL, headers={"User-Agent": "paper-sweep-weekly-agent/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw_html = response.read().decode("utf-8", errors="replace")

    page_text = normalize_text(html_to_text(raw_html))
    free_section = normalize_text(extract_free_section(page_text))

    current = {
        "url": PRICING_URL,
        "free_day_limit": extract_daily_limit(free_section),
        "free_month_limit": extract_monthly_limit(free_section),
        "free_section_hash": hashlib.sha256(free_section.encode("utf-8")).hexdigest(),
    }

    previous = load_snapshot(snapshot_path)
    reasons: list[str] = []

    if not previous:
        reasons.append("No prior snapshot found. Created baseline snapshot.")
    else:
        for field in ("free_day_limit", "free_month_limit"):
            if previous.get(field) != current.get(field):
                reasons.append(
                    f"{field} changed: {previous.get(field)} -> {current.get(field)}"
                )
        if previous.get("free_section_hash") != current.get("free_section_hash"):
            reasons.append("Free-plan section text changed; review pricing page manually.")

    changed = len(reasons) > 0 and not reasons[0].startswith("No prior snapshot")

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_lines = [
        f"Checked: {PRICING_URL}",
        f"Current daily limit: {current.get('free_day_limit') or 'not parsed'}",
        f"Current monthly limit: {current.get('free_month_limit') or 'not parsed'}",
    ]
    if reasons:
        summary_lines.append("Change notes:")
        summary_lines.extend([f"- {r}" for r in reasons])

    summary = "\n".join(summary_lines)
    status = "changed" if changed else "unchanged"
    print(json.dumps({"status": status, "summary": summary}))

    write_github_output("changed", "true" if changed else "false")
    write_github_output("summary", summary)


if __name__ == "__main__":
    main()
