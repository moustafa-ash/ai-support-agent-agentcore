# Verified evidence

Local: 13 offline tests passed. AWS/model/MCP boundaries are mocked in those tests;
generated calculator code executes locally. See `local-tests.txt`.

Hosted: all six scenarios passed in Udacity's sandbox, us-east-1. Final deployed
source: `8833789`. Final conversations were collected on 2026-10-03 UTC
(2026-10-04 in Cairo). These are real CLI outputs, not fixtures.

| Scenario | Conversation | Actual service evidence |
|---|---|---|
| Order tracking | `01-order.txt`: shipped, UPS, TRK987654321, October 5 | API-backed `order-tracker___get_order` succeeds in initial integration verification |
| Refund | `02-refund.txt`: REF-ZQ63VYW7, approved, $139.99, 3–5 business days | Lambda-backed `refund-processor___initiate_refund` succeeds |
| RAG | `03-rag.txt`: Platinum shipping, 15%, priority support | `search_knowledge_base` returns real managed-KB catalog chunks |
| Memory | `04-memory-a.txt`, `04-memory-b.txt`: Jane and concise preference | Retrieval and completed-turn save logs; fresh Agent instances with `s-A-final` and `s-B-final` payload sessions, separated by 90 seconds |
| Discount | `05-discount.txt`: 4,000 / 10% ($11) / $99 / 349 | `calculate_loyalty_discount` returns `calculation_mode=code_interpreter`, 99 earned points |
| Browser | `06-browser.txt`: Learn the Latest Tech Skills; Advance Your Career \| Udacity | Browser evaluation returns that exact live document title, followed by close |

`tool-events.jsonl` contains real, sanitized CloudWatch traces from initial checks
and the final suite. Gateway discovery is in `setup-checks.txt`; retained service
readiness is in `resource-status.json`. Final order answers may reuse extracted
fictional order facts; the initial trace independently proves the API integration.
Production order status should always be refreshed from an authorized backend.

Earlier unsuccessful attempts are retained in `attempts/`: the first memory recall
preceded extraction, and Nova's discount paraphrases changed dollar amounts.
The final hook renders exact calculator values. Initial HTML-based browsing did
not establish the title; the final run uses `document.title`. A navigation load-state
timeout occurred even in the final run, but the loaded document returned its title
successfully. Do not treat those earlier attempts as passed evidence.

All three cost checkpoints report $0, with AWS billing lag possible. Detailed
account/resource settings stay in ignored private files. Credentials are excluded.
Resources remain available for review; no Udacity submission has been made.
