#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

RESEND_API_URL = "https://api.resend.com/emails"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send email with Resend API.")
    parser.add_argument("--subject", required=True, help="Email subject.")
    parser.add_argument("--to", default=os.environ.get("REPORT_RECIPIENT"), help="Recipient email.")
    parser.add_argument(
        "--from",
        dest="from_email",
        default=os.environ.get("REPORT_SENDER", "onboarding@resend.dev"),
        help="Sender email.",
    )
    parser.add_argument("--reply-to", default=os.environ.get("REPORT_REPLY_TO"), help="Reply-to email.")
    parser.add_argument("--input", help="Path to markdown/text file used as email body.")
    parser.add_argument("--text", help="Plain-text body.")
    return parser.parse_args()


def read_body(path: str | None, text: str | None) -> str:
    if text:
        return text
    if path:
        return Path(path).read_text(encoding="utf-8")
    raise ValueError("Provide either --input or --text for message body.")


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set.")
    if not args.to:
        raise RuntimeError("Recipient not set. Use --to or REPORT_RECIPIENT env var.")

    body_text = read_body(args.input, args.text)

    payload: dict[str, object] = {
        "from": args.from_email,
        "to": [args.to],
        "subject": args.subject,
        "text": body_text,
    }
    if args.reply_to:
        payload["reply_to"] = args.reply_to

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        RESEND_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API failed ({exc.code}): {error_body}") from exc

    result = json.loads(response_body or "{}")
    print(json.dumps({"status": "sent", "id": result.get("id")}))


if __name__ == "__main__":
    main()
