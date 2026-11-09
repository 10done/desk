#!/usr/bin/env python3
"""Record one streamed reply. Reads ANTHROPIC_API_KEY from the environment and does not store it."""

import json
import os
import platform
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "claude-haiku-4-5-20251001"
URL = "https://api.anthropic.com/v1/messages"


def machine():
    cpu = platform.machine()
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        pass
    name = platform.node()
    try:
        name = subprocess.check_output(["scutil", "--get", "ComputerName"], text=True).strip()
    except Exception:
        pass
    return f"{name}, {platform.system()} {platform.release()} {platform.machine()}, {cpu}, Python {platform.python_version()}"


def main():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key.startswith("your_"):
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    corpus = json.loads((ROOT / "corpus.json").read_text())
    q = corpus["questions"][0]
    page = next(p for p in corpus["pages"] if p["id"] == q["page"])
    prompt = (
        "Use only this Harborline runbook page. Answer in one sentence.\n\n"
        f"{page['title']}\n{page['body']}\n\n"
        f"Question: {q['q']}"
    )
    payload = {
        "model": MODEL,
        "max_tokens": 80,
        "temperature": 0,
        "stream": True,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    tokens = []
    model = MODEL
    usage = {}
    stream_end = None
    t0 = time.perf_counter()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"HTTP {err.code}: {detail}")
    with resp:
        for raw in resp:
            now = (time.perf_counter() - t0) * 1000
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = json.loads(line.split(":", 1)[1].strip())
            kind = data.get("type")
            if kind == "message_start":
                msg = data.get("message") or {}
                model = msg.get("model") or model
                usage.update(msg.get("usage") or {})
            elif kind == "content_block_delta":
                text = (data.get("delta") or {}).get("text") or ""
                if text:
                    tokens.append({"t_ms": round(now, 3), "text": text})
            elif kind == "message_delta":
                usage.update(data.get("usage") or {})
            elif kind == "message_stop":
                stream_end = round(now, 3)
    if not tokens:
        raise SystemExit("stream had no text")
    if stream_end is None:
        stream_end = tokens[-1]["t_ms"]
    out = {
        "series": "one run",
        "command": "ANTHROPIC_API_KEY is read from the environment and is not stored. python3 scripts/record_first_token.py",
        "machine": machine(),
        "model": model,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question_id": q["id"],
        "page_id": page["id"],
        "prompt": prompt,
        "usage": usage,
        "stream_end_ms": stream_end,
        "tokens": tokens,
        "clock": "perf_counter on this machine from just before the HTTP request until each content_block_delta and message_stop. Includes network and queue. Not a GPU profiler.",
    }
    dest = ROOT / "data" / "first-token.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    text = "".join(tok["text"] for tok in tokens)
    print(f"pieces={len(tokens)} ttft_ms={tokens[0]['t_ms']} end_ms={stream_end} output_tokens={usage.get('output_tokens')} model={model}")
    print(text)


if __name__ == "__main__":
    main()
