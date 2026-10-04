"""Collect real service-side tool traces for this project's deployed Runtime."""
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
import yaml
from live_tests import sanitize

root = Path(__file__).resolve().parents[1]
config = yaml.safe_load((root / "starter/.bedrock_agentcore.yaml").read_text())
agent = config["agents"][config["default_agent"]]
runtime_id = agent["bedrock_agentcore"]["agent_id"]
session = boto3.Session(region_name=agent["aws"]["region"])
logs = session.client("logs")
group = f"/aws/bedrock-agentcore/runtimes/{runtime_id}-DEFAULT"
events = []
for page in logs.get_paginator("filter_log_events").paginate(logGroupName=group):
    events.extend(page.get("events", []))
private = root / "private"
private.mkdir(exist_ok=True)
(private / "cloudwatch-events.json").write_text(json.dumps(events))
selected = []
outage = []
start_file = root / "private/live/suite-start-ms.txt"
suite_start = int(start_file.read_text()) if start_file.exists() else 0
for event in events:
    message = event["message"]
    if "TOOL_EVIDENCE" in message or "MEMORY_" in message or "CSAI_Agent" in message:
        line = json.dumps({"timestamp_utc": datetime.fromtimestamp(event["timestamp"] / 1000,
            timezone.utc).isoformat(), "message": sanitize(message)})
        if event["timestamp"] >= suite_start:
            selected.append(line)
        else:
            outage.append(line)
(root / "evidence/tool-events.jsonl").write_text("\n".join(selected) + "\n")
if outage:
    (root / "evidence/gateway-outage-events.jsonl").write_text("\n".join(outage) + "\n")
print(f"Collected {len(selected)} actual service log events; review before publication.")
