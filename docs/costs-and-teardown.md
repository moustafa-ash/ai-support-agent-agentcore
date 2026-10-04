# Costs and teardown

Approved execution budget: $15 for this project. Use only Udacity's sandbox,
us-east-1, one tiny product catalog, and a small set of rubric/robustness invocations.
No load testing, OpenSearch collection, provisioned model capacity, or EC2 runtime.

AWS reports [managed KB storage](https://aws.amazon.com/bedrock/pricing/) at $5/GB/month
and standard retrieval at $1/1,000 calls. This catalog is about 2 KB; storage is
small under proportional billing. [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
bills Runtime, Browser, and Code Interpreter for consumption, with additional
Gateway, memory, logging, and Bedrock inference charges. Udacity estimates the
course project below $15; this is an estimate, not an enforceable billing cap.

Check available lab allocation and costs before provisioning, after deployment,
and after tests. Billing may lag. Record inaccessible cost reporting as unavailable,
not zero. Stop new work if estimated additional spend would exceed the $15 limit.

The October 4 resubmission baseline and post-test Cost Explorer checkpoints
reported approximately $0.173114 for the sandbox account; the raw responses are
`evidence/cost-baseline.json` and `evidence/cost-after-tests.json`. These are reported
account costs, not a project-specific final invoice. Billing can lag. The previous
submission's zero-dollar checkpoints are archived in `evidence/previous-submission/`.
The revised run used a tiny catalog, bounded sessions, one intentional deployed
Gateway outage, seven scenario calls, a delayed recall retry, and one direct Runtime
proof call. No load testing was performed.
Check the account again after billing catches up and before additional usage.
The $15 limit is a working stop condition, not an automatically enforced AWS cap.
The previous deployment was torn down as requested. The new review deployment can
incur further charges; use its current inventory for any subsequent teardown.

## After user review

Resources are intentionally retained for review. Use the ignored
`infrastructure-state.json` as the inventory; verify its account and region match
your active Udacity credentials. Delete only resources from this project.

1. From `starter/`, use `uv run agentcore destroy` to remove its Runtime deployment.
   Check the generated deployment configuration for the associated artifact bucket/role.
   The toolkit artifact bucket may be shared with other exercises: remove only the
   `ai_support_agent/` objects created here. Do not empty or delete a shared bucket.
2. Delete both Gateway targets, then the project's Gateway.
3. Delete the project's Memory resource.
4. Delete the Knowledge Base data source and Knowledge Base. Verify managed storage
   deletion completes. This project uses managed storage, not an OpenSearch collection.
5. Empty only the catalog bucket listed in the private inventory, then delete it.
6. Delete the listed REST API and the two project-prefixed Lambda functions.
7. Delete only this project's inline IAM policies and roles, plus its CloudWatch
   log groups after saving evidence. Do not remove course-provided roles or other exercises.
8. Check costs and resource inventory again. Keep local code and sanitized evidence.

Teardown is deliberately manual and is not run until the user requests it.
