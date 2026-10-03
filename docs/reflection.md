# Reflection draft for review

This project uses AgentCore Gateway to expose two different backend integrations
through one MCP interface. I kept the supplied order tracker behind a REST API
with Lambda proxy integration, while the refund processor remains a direct Lambda
target. That choice preserves each handler's expected request format and lets the
Strands agent discover both kinds of tools without implementing separate clients.
For memory, I also preserve the original customer message before adding retrieved
context. Otherwise, saving the augmented message could repeatedly feed previously
retrieved facts back into extraction as though the customer had just stated them.

A concrete challenge arose during infrastructure provisioning. The course setup
uses underscore-based Gateway target names, but the AWS service rejected those
names with a validation error. I changed the target names to use hyphens, leaving
the provided Lambda handlers and their tool-routing logic unchanged. Recording
resource identifiers after each successful creation made it possible to resume
setup without recreating the Lambdas, API, and Gateway. I also checked current
managed Knowledge Base documentation to select its connector and retrieval
configuration rather than assuming the older vector configuration applied. Live
testing exposed another issue: Nova rewrote discount amounts even though Code
Interpreter returned correct values. I added an invocation hook that renders the
exact tool result into the final response and saves that same text to memory.

In production, authentication and authorization would need more than a system
prompt. The educational Gateway uses an unauthenticated endpoint and fictional
records. A real service should authenticate customers, enforce order ownership
inside the backend, and require idempotent refund operations with durable records.
I would also disable detailed tool-result logging for normal customer traffic,
add monitoring for retrieval and interpreter failures, and track costs by service.
The tier-only calculator fallback is useful for explaining a temporary outage,
but it must stay clearly labeled so a customer never mistakes an estimate for a
complete redemption calculation.

Prepared with Codex assistance. Review this draft for accuracy before submission;
the evidence checklist separately records whether hosted tests have passed.
