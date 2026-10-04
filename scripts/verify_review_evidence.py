"""Check genuine captured CLI output against CloudWatch Gateway tool results."""
from datetime import datetime
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = root / "evidence"
names = ("01-order", "02-refund", "03-rag", "04-memory-a", "04-memory-b", "05-discount", "06-browser")
responses = {}
times = {}
for name in names:
    text = (evidence / (name + ".txt")).read_text()
    if "$ agentcore invoke " not in text or "CLI exit code: 0" not in text or "Response:" not in text:
        raise ValueError(f"{name}: missing command, successful exit, or response")
    response = text.split("Response:", 1)[1].split("CLI exit code:", 1)[0].strip()
    if not response or any(marker in response.lower() for marker in
        ("invocation failed", "trouble reaching", "configuration incomplete", "invalid request", "no text response")):
        raise ValueError(f"{name}: unsuccessful or empty agent response")
    responses[name] = response
    captured = next(line.removeprefix("Captured UTC: ") for line in text.splitlines() if line.startswith("Captured UTC:"))
    times[name] = datetime.fromisoformat(captured)
gap = (times["04-memory-b"] - times["04-memory-a"]).total_seconds()
if gap < 30 or not all(word in responses["04-memory-b"].lower() for word in ("jane", "concise")):
    raise ValueError("Memory recall did not establish the required delayed cross-session facts")
if not all(value in responses["05-discount"] for value in ("4,000", "10%", "$99.00", "349", "code_interpreter")):
    raise ValueError("Discount evidence does not contain the exact required sandbox result")

gateway_events = []
for line in (evidence / "tool-events.jsonl").read_text().splitlines():
    record = json.loads(line)
    if "TOOL_EVIDENCE " not in record["message"]:
        continue
    event = json.loads(record["message"].split("TOOL_EVIDENCE ", 1)[1])
    if not event["name"].startswith(("order-tracker___", "refund-processor___")):
        continue
    result = event["result"]
    if result.get("status") != "success" or result.get("isError"):
        raise ValueError("A Gateway call failed in the positive scenario suite")
    data = json.loads("\n".join(block.get("text", "") for block in result.get("content", [])))
    if not isinstance(data, dict) or not data or data.get("error"):
        raise ValueError("A Gateway call returned invalid or empty data")
    gateway_events.append({"timestamp_utc": record["timestamp_utc"], "tool_name": event["name"],
                           "status": result["status"], "response": data})
orders = [e for e in gateway_events if e["tool_name"] == "order-tracker___get_order" and e["response"].get("order_id") == "ORD-001"]
refunds = [e for e in gateway_events if e["tool_name"] == "refund-processor___initiate_refund"]
if not orders or not refunds:
    raise ValueError("Missing distinct successful API order and Lambda refund tool evidence")
for item in refunds:
    data = item["response"]
    if data.get("status") != "APPROVED" or data.get("amount") != 139.99 or data.get("refund_id", "") not in responses["02-refund"]:
        raise ValueError("Refund trace does not match the customer-facing approval")
(evidence / "gateway-success.json").write_text(json.dumps(gateway_events, indent=2))
report = {"all_seven_cli_invocations_exit_zero": True, "all_six_scenarios_have_nonempty_responses": True,
          "api_order_and_lambda_refund_verified": True, "positive_gateway_calls": len(gateway_events),
          "memory_session_gap_seconds": gap, "gold_example_exact": True,
          "note": "Structural checks supplement human review; local fixtures cannot establish cloud evidence."}
(evidence / "review-verification.json").write_text(json.dumps(report, indent=2))
print("REVIEW_EVIDENCE_CHECKS_PASSED " + json.dumps(report), flush=True)
