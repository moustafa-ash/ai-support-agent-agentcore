"""Provision only this fictional-data project in the approved Udacity sandbox.

State is recorded after each creation so failures are reviewable and resumable.
Run from the repository using starter's Python environment. No credentials in state.
"""
import argparse
import io
import json
from pathlib import Path
import time
import uuid
import zipfile
import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "infrastructure-state.json"
REGION = "us-east-1"

def policy(actions, resources):
    return {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": actions, "Resource": resources}]}

def wait(fetch, field="status", desired="READY", timeout=600):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = fetch()
        if value[field] == desired:
            return value
        if value[field] in {"FAILED", "CREATE_FAILED", "UPDATE_FAILED"}:
            raise RuntimeError(f"Resource failed: {value}")
        time.sleep(10)
    raise TimeoutError(f"Resource did not become {desired}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Preview: Lambda x2, REST API, MCP Gateway x2 targets, S3 catalog, managed KB, Memory. Region us-east-1.")
        return
    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {"account": account, "region": REGION, "suffix": uuid.uuid4().hex[:8]}
    if state["account"] != account or state["region"] != REGION:
        raise ValueError("Account or region mismatch; refusing to modify another deployment")
    prefix = "ai-support-" + state["suffix"]
    def record(key, value):
        state[key] = value
        STATE.write_text(json.dumps(state, indent=2))
        print("Recorded " + key, flush=True)
    record("prefix", prefix)
    iam = session.client("iam")
    def role(label, service, access):
        key = label + "_role"
        if key in state:
            return state[key]
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
        result = iam.create_role(RoleName=prefix + "-" + label, AssumeRolePolicyDocument=json.dumps(trust))
        arn = result["Role"]["Arn"]
        record(key, arn)
        iam.put_role_policy(RoleName=prefix + "-" + label, PolicyName="ProjectAccess", PolicyDocument=json.dumps(access))
        time.sleep(15)
        return arn
    lam = session.client("lambda")
    lambda_role = role("lambda", "lambda.amazonaws.com", policy(["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], f"arn:aws:logs:{REGION}:{account}:log-group:/aws/lambda/{prefix}-*:*") )
    for name in ("order_tracker", "refund_processor"):
        if name in state:
            continue
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.write(ROOT / "starter/lambda" / (name + ".py"), name + ".py")
        result = lam.create_function(FunctionName=prefix + "-" + name.replace("_", "-"), Runtime="python3.12",
                                     Role=lambda_role, Handler=name + ".lambda_handler", Code={"ZipFile": buffer.getvalue()}, Timeout=30)
        record(name, result["FunctionArn"])
        lam.get_waiter("function_active_v2").wait(FunctionName=result["FunctionArn"])
    api = session.client("apigateway")
    routes = [("/orders/{order_id}", "get_order"), ("/customers/{customer_id}/orders", "get_customer_orders"),
              ("/customers/{customer_id}", "get_customer")]
    if "api_id" not in state:
        record("api_id", api.create_rest_api(name=prefix + "-orders", endpointConfiguration={"types": ["REGIONAL"]})["id"])
    if "api_ready" not in state:
        resources = {r["path"]: r["id"] for r in api.get_resources(restApiId=state["api_id"], limit=500)["items"]}
        for path, operation in routes:
            parent, current = resources["/"], ""
            for part in path.strip("/").split("/"):
                current += "/" + part
                if current not in resources:
                    resources[current] = api.create_resource(restApiId=state["api_id"], parentId=parent, pathPart=part)["id"]
                parent = resources[current]
            existing = api.get_resource(restApiId=state["api_id"], resourceId=parent).get("resourceMethods", {})
            if "GET" not in existing:
                api.put_method(restApiId=state["api_id"], resourceId=parent, httpMethod="GET", authorizationType="NONE", operationName=operation,
                               requestParameters={f"method.request.path.{p}": True for p in ("order_id", "customer_id") if "{" + p + "}" in path})
            api.put_integration(restApiId=state["api_id"], resourceId=parent, httpMethod="GET", type="AWS_PROXY", integrationHttpMethod="POST",
                uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{state['order_tracker']}/invocations")
        try:
            lam.add_permission(FunctionName=state["order_tracker"], StatementId="AllowProjectApi", Action="lambda:InvokeFunction",
                               Principal="apigateway.amazonaws.com", SourceArn=f"arn:aws:execute-api:{REGION}:{account}:{state['api_id']}/*/GET/*")
        except lam.exceptions.ResourceConflictException:
            pass
        api.create_deployment(restApiId=state["api_id"], stageName="prod")
        record("api_ready", True)
    control = session.client("bedrock-agentcore-control")
    gateway_policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": state["refund_processor"]},
        {"Effect": "Allow", "Action": "execute-api:Invoke", "Resource": f"arn:aws:execute-api:{REGION}:{account}:{state['api_id']}/prod/GET/*"},
        {"Effect": "Allow", "Action": ["apigateway:GET"], "Resource": f"arn:aws:apigateway:{REGION}::/restapis/{state['api_id']}/*"}]}
    gateway_role = role("gateway", "bedrock-agentcore.amazonaws.com", gateway_policy)
    if "gateway_id" not in state:
        result = control.create_gateway(name=prefix + "-gateway", roleArn=gateway_role, protocolType="MCP", authorizerType="NONE")
        record("gateway_id", result["gatewayId"])
        record("gateway_url", result["gatewayUrl"])
    wait(lambda: control.get_gateway(gatewayIdentifier=state["gateway_id"]))
    if "order_target" not in state:
        result = control.create_gateway_target(gatewayIdentifier=state["gateway_id"], name="order_tracker",
            targetConfiguration={"mcp": {"apiGateway": {"restApiId": state["api_id"], "stage": "prod", "apiGatewayToolConfiguration": {
                "toolFilters": [{"filterPath": path, "methods": ["GET"]} for path, _ in routes],
                "toolOverrides": [{"name": operation, "path": path, "method": "GET", "description": operation.replace("_", " ")} for path, operation in routes]}}}},
            credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
        record("order_target", result["targetId"])
    if "refund_target" not in state:
        result = control.create_gateway_target(gatewayIdentifier=state["gateway_id"], name="refund_processor",
            targetConfiguration={"mcp": {"lambda": {"lambdaArn": state["refund_processor"], "toolSchema": {
                "inlinePayload": json.loads((ROOT / "starter/lambda/lambda_schema").read_text())}}}},
            credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
        record("refund_target", result["targetId"])
    for key in ("order_target", "refund_target"):
        wait(lambda key=key: control.get_gateway_target(gatewayIdentifier=state["gateway_id"], targetId=state[key]))
    s3 = session.client("s3")
    if "bucket" not in state:
        name = prefix + "-catalog-" + account
        s3.create_bucket(Bucket=name)
        record("bucket", name)
        s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={k: True for k in
            ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")})
    s3.upload_file(str(ROOT / "starter/product_catalog.txt"), state["bucket"], "product_catalog.txt")
    kb_policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::" + state["bucket"]},
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::" + state["bucket"] + "/*"}]}
    kb_role = role("knowledge", "bedrock.amazonaws.com", kb_policy)
    bedrock = session.client("bedrock-agent")
    if "kb_id" not in state:
        result = bedrock.create_knowledge_base(name=prefix + "-knowledge", roleArn=kb_role,
            knowledgeBaseConfiguration={"type": "MANAGED", "managedKnowledgeBaseConfiguration": {"embeddingModelType": "MANAGED"}})
        record("kb_id", result["knowledgeBase"]["knowledgeBaseId"])
    wait(lambda: bedrock.get_knowledge_base(knowledgeBaseId=state["kb_id"])["knowledgeBase"], desired="ACTIVE")
    if "data_source_id" not in state:
        result = bedrock.create_data_source(knowledgeBaseId=state["kb_id"], name="catalog", dataDeletionPolicy="DELETE",
            dataSourceConfiguration={"type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR", "managedKnowledgeBaseConnectorConfiguration": {
                "connectorParameters": {"type": "S3", "version": "1", "connectionConfiguration": {
                    "bucketName": state["bucket"], "bucketOwnerAccountId": account},
                    "deletionProtectionConfiguration": {"enableDeletionProtection": False}}}},
            vectorIngestionConfiguration={"parsingConfiguration": {"parsingStrategy": "SMART_PARSING"}})
        record("data_source_id", result["dataSource"]["dataSourceId"])
    if "ingestion_job" not in state:
        result = bedrock.start_ingestion_job(knowledgeBaseId=state["kb_id"], dataSourceId=state["data_source_id"])
        record("ingestion_job", result["ingestionJob"]["ingestionJobId"])
    wait(lambda: bedrock.get_ingestion_job(knowledgeBaseId=state["kb_id"], dataSourceId=state["data_source_id"],
        ingestionJobId=state["ingestion_job"])["ingestionJob"], desired="COMPLETE")
    if "memory_id" not in state:
        result = control.create_memory(name="CustomerSupportMemory_" + state["suffix"], eventExpiryDuration=7,
            memoryStrategies=[{"semanticMemoryStrategy": {"name": "customer_facts", "namespaces": ["cs_agent/{actorId}/facts"]}},
                              {"userPreferenceMemoryStrategy": {"name": "customer_preferences", "namespaces": ["cs_agent/{actorId}/preferences"]}}])
        record("memory_id", result["memory"]["id"])
    wait(lambda: control.get_memory(memoryId=state["memory_id"])["memory"], desired="ACTIVE")
    (ROOT / "starter/runtime_settings.json").write_text(json.dumps(dict(REGION=REGION, GATEWAY_URL=state["gateway_url"],
        KB_ID=state["kb_id"], MEMORY_ID=state["memory_id"]), indent=2))
    print("PROJECT_INFRASTRUCTURE_READY", flush=True)

if __name__ == "__main__":
    main()
