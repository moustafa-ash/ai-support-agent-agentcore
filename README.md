# AI Support Agent with Amazon Bedrock AgentCore

Udacity AWS AI Engineering project using Strands, Nova 2 Lite, AgentCore Runtime,
Gateway MCP tools, a Bedrock Knowledge Base, cross-session Memory, Code Interpreter,
and Browser. The supplied store, orders, customer records and refunds are fictional.
See [starter provenance](ATTRIBUTION.md) and [original instructions](docs/udacity-instructions.md).

## Current validation

The implementation passes 12 offline integration-boundary tests. Live deployment
and all six AWS scenarios are pending; offline tests do not establish cloud success.
See [evidence](evidence/README.md) for the latest status.

## Local setup and tests

```powershell
cd starter
uv sync --python 3.13 --locked
cd ..
starter\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On Linux use `starter/.venv/bin/python`. Only install the Python
`bedrock-agentcore-starter-toolkit`, not the npm CLI with the same command name.
Resource settings are supplied through environment variables; AWS credentials use
the standard credential chain. Never commit credentials or private deployment metadata.

## Deploy in Udacity's sandbox

All project services use `us-east-1`. Keep deployment settings in ignored
`starter/runtime_settings.json` containing `REGION`, `GATEWAY_URL`, `KB_ID`, and `MEMORY_ID`.
The deployment helper passes these to Runtime as environment variables.
Use the provided lab account and confirm identity and available budget first.

The course's Gateway uses the `NONE` authorizer and fictional data only. The
provided Lambdas remain unchanged. This demo does not implement production
authentication, refund persistence, or payment processing.

From `starter/`, configure and deploy using the Python Starter Toolkit:

```bash
uv run agentcore configure --entrypoint main.py --name ai_support_agent --deployment-type direct_code_deploy --runtime PYTHON_3_13 --disable-memory --non-interactive --region us-east-1 --idle-timeout 60 --max-lifetime 600 --requirements-file requirements-runtime.txt
uv run python ../scripts/deploy.py
uv run setup_permissions.py
uv run agentcore invoke '{"prompt":"Can you track order ORD-001?","customer_id":"CUST-123","session_id":"t1"}'
```

## Request interface

If the course VM's system Python lacks SQLite, create the environment with
`UV_PROJECT_ENVIRONMENT=../.venv-cloud uv sync --python 3.13 --managed-python --locked`
and keep that variable set for subsequent `uv run` commands. Keep virtual environments
outside `starter/` because the toolkit's source packager excludes only `.venv` by name.

`prompt` is a required non-empty string. `customer_id` and `session_id` are
optional non-empty strings. Missing session IDs are UUIDs; anonymous actors are
unique per request to avoid shared memory. The response is text.

Loyalty redemption uses blocks of 500 points at 100 points/$1, capped at 50% of
the order. Tier discounts apply afterward; points accrue on the final paid amount,
rounded down to whole points. The Gold/4,250 points/$150 example returns 4,000
points redeemed, 10% tier discount, $99 paid, and 349 remaining points.
Interpreter failures explicitly return a tier-only estimate without redemption or earning.

## Review and costs

The approved project spending limit is $15; reported AWS costs can lag. Resources
are to remain available for user review, so charges can continue afterward.
Do not submit to Udacity automatically. Retain logs for six live scenarios and a
200–400 word reflection. Follow the teardown checklist after review.
