"""Check actual sandbox identity, six Gateway tools, catalog retrieval and Memory."""
import json
from pathlib import Path
import boto3
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

root = Path(__file__).resolve().parents[1]
settings = json.loads((root / "starter/runtime_settings.json").read_text())
session = boto3.Session(region_name=settings["REGION"])
session.client("sts").get_caller_identity()
print("AWS_IDENTITY_VERIFIED", flush=True)
with MCPClient(lambda: streamable_http_client(settings["GATEWAY_URL"])) as gateway:
    tools = gateway.list_tools_sync()
    names = [t.tool_name for t in tools]
    print("GATEWAY_TOOLS " + json.dumps(names), flush=True)
    required = {"get_order", "get_customer_orders", "get_customer", "initiate_refund", "check_refund_status", "get_return_label"}
    if not required <= {name.split("___")[-1] for name in names}:
        raise RuntimeError("Missing required Gateway tools")
result = session.client("bedrock-agent-runtime").retrieve(knowledgeBaseId=settings["KB_ID"],
    retrievalQuery={"text": "What is the return policy for electronics?"},
    retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": 5}})
text = "\n".join(r.get("content", {}).get("text", "") for r in result.get("retrievalResults", []))
if "15 days" not in text and "15-day" not in text:
    raise RuntimeError("Catalog retrieval did not return the electronics return policy")
print("CATALOG_RETRIEVAL_VERIFIED", flush=True)
memory = session.client("bedrock-agentcore-control").get_memory(memoryId=settings["MEMORY_ID"])["memory"]
if memory["status"] != "ACTIVE":
    raise RuntimeError("Memory is not ACTIVE")
print("MEMORY_ACTIVE", flush=True)
