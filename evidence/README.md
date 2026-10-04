# Resubmission evidence — October 4, 2026

Start with [the reviewer response](../docs/resubmission.md). The revised source
passes **21 offline tests** and all **six scenarios were verified live** in the
Udacity sandbox. Local tests mock AWS/model/MCP boundaries; hosted outputs below
come from the deployed Runtime and actual CloudWatch tool events.

## The two requested corrections

- **Deployment proof:** [direct terminal invocation screenshot](screenshots/runtime-invoke-proof.jpg)
  shows the actual `uv run agentcore invoke` command, successful order response,
  and zero pipeline exit code. [Complete sanitized stdout](runtime-invoke-proof.txt)
  is also included. A display filter omits private deployment metadata from the terminal.
- **Gateway robustness:** [successful structured results](gateway-success.json)
  contain four nonempty, successful Gateway calls, including the API order target
  and Lambda refund target. [Actual service traces](tool-events.jsonl) include
  discovery success and validated tool responses.
- **Intentional outage:** [deployed outage transcript](gateway-outage.txt),
  [screenshot](screenshots/gateway-outage.jpg), and [diagnostic logs](gateway-outage-events.jsonl)
  show a safe message with a dummy Gateway URL. This is negative-test evidence.
  The working endpoint was restored before the successful scenario suite.

## Six successful scenarios

Each scenario transcript includes the exact executed `agentcore invoke` command,
UTC timestamp, full sanitized CLI output, and exit code. Scenario screenshots
show genuine saved transcripts through `scripts/show_evidence.py`; they are
separate from the direct terminal invocation screenshot above.

| Scenario | Actual CLI output | Screenshot | Result |
|---|---|---|---|
| Order | [01-order.txt](01-order.txt) | [Order](screenshots/01-order.jpg) | ORD-001 SHIPPED; UPS, TRK987654321; October 6 delivery |
| Refund | [02-refund.txt](02-refund.txt) | [Refund](screenshots/02-refund.jpg) | REF-U8OQPRXQ APPROVED; $139.99, 3–5 business days |
| RAG | [03-rag.txt](03-rag.txt) | [Platinum](screenshots/03-rag.jpg) | Same-day shipping, 15%, priority support; actual retrieval |
| Memory | [Introduction](04-memory-a.txt), [recall](04-memory-b.txt) | [Session A](screenshots/04-memory-a.jpg), [session B](screenshots/04-memory-b.jpg) | Jane/concise; s-A-review2 and s-B-review3, same customer, about 577 seconds apart |
| Interpreter | [05-discount.txt](05-discount.txt) | [Gold](screenshots/05-discount.jpg) | 4,000 points, 10% ($11), $99 final, 349 remaining; 99 earned |
| Browser | [06-browser.txt](06-browser.txt) | [Live title](screenshots/06-browser.jpg) | Learn the Latest Tech Skills; Advance Your Career \| Udacity |

[Review verification](review-verification.json) cross-checks the commands,
responses, memory timing, discount values, and Gateway results. It supplements
human review. [Source verification](source-verification.json) compares `main.py`
inside the deployed S3 artifact against the workspace and confirms the working
Gateway is restored. [Readiness](resource-status.json) and [setup](setup-checks.txt)
record the live integrations. [Local tests](local-tests.txt) are explicitly offline.

## Earlier attempts and costs

The first resubmission recall was too early and failed to retrieve Jane's
name/preference. It is retained under `attempts/04-memory-before-extraction-review2.*`;
the later successful recall above replaces it as current evidence. Other earlier
unsuccessful runs remain in `attempts/`. The first submission's historical outputs
and zero-dollar cost checkpoints are in `previous-submission/`.

The latest baseline and post-test checkpoints report about $0.17 for the sandbox
account. Billing may lag. Identifiers, endpoints, credentials, and operational
configuration are excluded from the public bundle. The previous deployment was
deleted as requested; the revised deployment is available for review.
