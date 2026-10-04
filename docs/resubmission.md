# Resubmission review

Reviewer feedback was read directly in Udacity on October 4, 2026. Two criteria
require changes; RAG, Browser, Code Interpreter, Memory, and Reflection passed.

| Reviewer request | Change | Verification |
|---|---|---|
| Show a deployed `agentcore invoke` command and successful response | Record the executed command, UTC timestamp, sanitized CLI output, and exit code | [Direct terminal invocation screenshot](../evidence/screenshots/runtime-invoke-proof.jpg), [actual stdout](../evidence/runtime-invoke-proof.txt), plus seven scenario transcripts/screenshots |
| Catch Gateway failures and give a meaningful message | Connection/discovery handling logs success, catches timeout/connection/general failures, rejects empty discovery, and returns a safe service message | [Deployed intentional outage](../evidence/gateway-outage.txt), [screenshot](../evidence/screenshots/gateway-outage.jpg), and [diagnostic logs](../evidence/gateway-outage-events.jsonl) |
| Gateway tool results must be well formed and nonempty | Validate MCP status/content, reject malformed/empty/error responses and unsuccessful backend status, unwrap the supplied Lambda response envelope | [Four successful Gateway results](../evidence/gateway-success.json), [order screenshot](../evidence/screenshots/01-order.jpg), [refund screenshot](../evidence/screenshots/02-refund.jpg) |

Gateway tools use a 30-second request timeout. Failed tool responses are replaced
with a safe, nonempty error before the model sees them. The final response guard
prevents the model from claiming an action succeeded, and persists the same
customer-facing text to Memory. A timed-out refund has an uncertain outcome;
customers are told to check its status before retrying. No automatic refund
retry was added. Endpoint details, credentials, and raw exception text are
excluded from the project logger's failure diagnostics.

Local verification passes 21 offline tests, including a real SDK hook event/order
test; AWS and model calls remain mocked. Fresh hosted verification passed all six
scenarios on October 4. The initial memory recall was too early; the later session
correctly recalled Jane and concise responses, about 577 seconds after introduction.
The failed attempt is retained and labeled separately. Historical evidence from
the first submission is in `evidence/previous-submission/`.

The Runtime was first deployed with `https://example.invalid/mcp` for the deliberate
outage test, then redeployed with the saved working endpoint. The positive scenario
logs exclude that earlier negative test by their recorded suite start time.
[Artifact verification](../evidence/source-verification.json) confirms the deployed
source matches and the working Gateway is restored. The new resources remain
available for review; the old deployment's teardown is historical.

## Reviewer note for the next submission

I addressed both requested changes. Please start with `docs/resubmission.md`.
`evidence/screenshots/runtime-invoke-proof.jpg` shows a direct deployed
`uv run agentcore invoke` command and successful response. The six scenarios also
include complete sanitized CLI transcripts and readable terminal screenshots.
`evidence/gateway-success.json` contains nonempty, successful API-backed order and
Lambda-backed refund results from actual CloudWatch events. Gateway connection,
discovery, and tool-result failures now produce safe messages and diagnostic logs;
`evidence/gateway-outage.txt` and its screenshot demonstrate an intentional deployed
outage. The working endpoint was restored and verified afterward. Negative and
historical attempts are clearly separated from current successful evidence.
