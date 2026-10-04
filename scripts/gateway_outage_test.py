"""Verify the deployed Runtime's response during an intentional Gateway outage.

Deploy with deploy.py --gateway-url https://example.invalid/mcp first. Restore
the saved working endpoint by running deploy.py without the override afterward.
This is outage evidence, never a successful order/refund demonstration.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess

from live_tests import sanitize

root = Path(__file__).resolve().parents[1]
payload = {"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123",
           "session_id": "intentional-gateway-outage"}
command = ["agentcore", "invoke", json.dumps(payload)]
print("$ " + shlex.join(command), flush=True)
result = subprocess.run(command, cwd=root / "starter", stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, timeout=180)
transcript = ("Intentional outage: Runtime configured with https://example.invalid/mcp\n"
              "Captured UTC: " + datetime.now(timezone.utc).isoformat() + "\n"
              "$ " + shlex.join(command) + "\n" + result.stdout
              + f"\nCLI exit code: {result.returncode}\n")
(root / "private/gateway-outage.txt").write_text(transcript)
(root / "evidence/gateway-outage.txt").write_text(sanitize(transcript))
print(sanitize(result.stdout), flush=True)
if result.returncode or "trouble reaching the order/refund service" not in result.stdout:
    raise RuntimeError("Expected graceful Gateway outage response was not observed")
print("EXPECTED_GATEWAY_OUTAGE_CONFIRMED", flush=True)
