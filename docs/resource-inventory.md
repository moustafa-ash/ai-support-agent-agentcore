# Retained sandbox inventory

Region: us-east-1. Readiness was checked at 2026-10-03 21:06 UTC; see
`evidence/resource-status.json`. No teardown was run.

| Resource | Quantity | Status / purpose |
|---|---:|---|
| AgentCore Runtime | 1 | READY, direct_code_deploy, PYTHON_3_13 |
| AgentCore Gateway | 1 | READY, course NONE authorizer, fictional data |
| Gateway targets | 2 | READY; REST API orders and direct Lambda refunds |
| REST API | 1 | prod stage, three GET routes |
| Lambda functions | 2 | Active; unchanged starter handlers, Python 3.12 |
| Managed Knowledge Base | 1 | ACTIVE, synchronized original catalog |
| Knowledge Base data source | 1 | S3 managed connector, ingestion complete |
| Catalog S3 bucket | 1 | Public access blocked |
| Memory | 1 | ACTIVE, semantic and preference strategies, 7-day event expiry |
| Project integration IAM roles | 3 | Lambda, Gateway, Knowledge Base |
| Runtime execution IAM role | 1 | Toolkit-created; scoped integration policy added |
| Runtime artifacts | 1 object prefix | Toolkit S3 bucket can be shared; delete only project objects |
| CloudWatch logs | Runtime and Lambda groups | Keep sanitized evidence before any later deletion |

Exact identifiers, role ARNs and endpoints are in the ignored local
`private/infrastructure-state.json`, `private/.bedrock_agentcore.yaml`, and
`private/runtime_settings.json`, with corresponding private files in the VM.
These contain resource metadata, not AWS credentials. Temporary lab credentials
remain in the VM AWS profile only. Sandbox lifecycle and credential expiry can
limit later access even though the resources have been retained.

The Runtime has a 60-second idle timeout and 600-second maximum lifetime.
Browser sessions are bounded to 300 seconds; Code Interpreter uses a scoped
session context. Retaining resources does not require keeping compute sessions busy.
Use [project-specific teardown steps](costs-and-teardown.md) only after review.
