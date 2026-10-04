"""Record actual resource readiness, reported costs, and deployed source hashes."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import zipfile

import boto3
import yaml

root = Path(__file__).resolve().parents[1]
state = json.loads((root / "infrastructure-state.json").read_text())
config = yaml.safe_load((root / "starter/.bedrock_agentcore.yaml").read_text())
configured = config["agents"][config["default_agent"]]
session = boto3.Session(region_name=state["region"])
if session.client("sts").get_caller_identity()["Account"] != state["account"]:
    raise ValueError("Sandbox account mismatch")
control = session.client("bedrock-agentcore-control")
runtime = control.get_agent_runtime(agentRuntimeId=configured["bedrock_agentcore"]["agent_id"])
status = {"captured_utc": datetime.now(timezone.utc).isoformat(), "region": state["region"],
          "runtime": runtime["status"],
          "gateway": control.get_gateway(gatewayIdentifier=state["gateway_id"])["status"],
          "memory": control.get_memory(memoryId=state["memory_id"])["memory"]["status"],
          "knowledge_base": session.client("bedrock-agent").get_knowledge_base(
              knowledgeBaseId=state["kb_id"])["knowledgeBase"]["status"]}
for label in ("order_target", "refund_target"):
    status[label] = control.get_gateway_target(gatewayIdentifier=state["gateway_id"], targetId=state[label])["status"]
for label in ("order_tracker", "refund_processor"):
    status[label] = session.client("lambda").get_function_configuration(FunctionName=state[label])["State"]
(root / "evidence/resource-status.json").write_text(json.dumps(status, indent=2))
if any(value not in {"READY", "ACTIVE", "Active"} for key, value in status.items()
       if key not in {"captured_utc", "region"}):
    raise RuntimeError("A project resource is not ready")

location = runtime["agentRuntimeArtifact"]["codeConfiguration"]["code"]["s3"]
get_args = {"Bucket": location["bucket"], "Key": location["prefix"]}
if location.get("versionId"):
    get_args["VersionId"] = location["versionId"]
archive = session.client("s3").get_object(**get_args)["Body"].read()
with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
    deployed_main = bundle.read("main.py")
local_main = (root / "starter/main.py").read_bytes()
source = {"captured_utc": status["captured_utc"], "runtime_version": runtime["agentRuntimeVersion"],
          "runtime": runtime["agentRuntimeArtifact"]["codeConfiguration"]["runtime"],
          "entry_point": runtime["agentRuntimeArtifact"]["codeConfiguration"]["entryPoint"],
          "workspace_main_sha256": hashlib.sha256(local_main).hexdigest(),
          "deployed_main_sha256": hashlib.sha256(deployed_main).hexdigest(),
          "deployed_source_matches": deployed_main == local_main,
          "working_gateway_restored": runtime.get("environmentVariables", {}).get("GATEWAY_URL") == state["gateway_url"]}
(root / "evidence/source-verification.json").write_text(json.dumps(source, indent=2))
if not source["deployed_source_matches"] or not source["working_gateway_restored"]:
    raise RuntimeError("Deployed source or Gateway configuration mismatch")

now = datetime.now(timezone.utc)
cost = session.client("ce").get_cost_and_usage(TimePeriod={"Start": now.strftime("%Y-%m-01"),
    "End": (now + timedelta(days=1)).strftime("%Y-%m-%d")}, Granularity="MONTHLY", Metrics=["UnblendedCost"])
(root / "evidence/cost-after-tests.json").write_text(json.dumps(cost, indent=2))
amount = sum(float(item["Total"]["UnblendedCost"]["Amount"]) for item in cost["ResultsByTime"])
print("RESOURCES_READY DEPLOYED_SOURCE_MATCHES WORKING_GATEWAY_RESTORED", flush=True)
print(f"REPORTED_SANDBOX_ACCOUNT_COST_USD {amount:.6f} (billing may lag)", flush=True)
if amount >= 15:
    raise RuntimeError("Reported sandbox cost reached the $15 working limit; stop new spending")
