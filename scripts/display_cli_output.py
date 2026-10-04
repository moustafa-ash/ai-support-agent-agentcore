"""Sanitize actual piped CLI output for a direct terminal invocation screenshot."""
from pathlib import Path
import sys

from live_tests import sanitize

root = Path(__file__).resolve().parents[1]
raw = sys.stdin.read()
(root / "private/direct-runtime-cli.txt").write_text(raw)
safe = sanitize(raw)
(root / "evidence/runtime-invoke-proof.txt").write_text(safe)
if "Response:" not in safe:
    print(safe)
    raise SystemExit("CLI returned no agent response")
response = safe.split("Response:", 1)[1].strip()
print("Response (actual CLI output; deployment metadata omitted):")
print(response)
if not response or any(marker in response.lower() for marker in ("invocation failed", "trouble reaching", "no text response")):
    raise SystemExit("Agent response was unsuccessful")
