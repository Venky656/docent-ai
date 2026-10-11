#!/usr/bin/env python3
"""Smoke test: upload a sample PDF and ask one question. Server must be running."""
import os
import sys

import requests

BASE = os.getenv("APP_URL", "http://127.0.0.1:8080")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "samples", "test_document.pdf")
SID = "smoketest0001"

r = requests.get(f"{BASE}/status", headers={"X-Session-ID": SID}, timeout=10)
r.raise_for_status()
print(f"Server OK: {r.json()}")

with open(SAMPLE, "rb") as f:
    r = requests.post(f"{BASE}/upload", files={"file": ("test_document.pdf", f, "application/pdf")},
                      headers={"X-Session-ID": SID}, timeout=60)
r.raise_for_status()
data = r.json()
assert data.get("chunks", 0) > 0, f"no chunks indexed: {data}"
print(f"Upload OK: {data['message']} | suggestions: {len(data.get('suggestions', []))}")

r = requests.post(f"{BASE}/ask_stream", json={"query": "What is this document about?"},
                  headers={"X-Session-ID": SID}, timeout=120)
r.raise_for_status()
events = [line for line in r.text.splitlines() if line.startswith("event:")]
assert "event: done" in events, f"stream did not finish: {events[-3:]}"
print(f"Ask OK: events={sorted(set(e.split()[1] for e in events))}")

print("\nAll smoke tests passed.")
sys.exit(0)
