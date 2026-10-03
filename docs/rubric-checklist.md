# Rubric checklist

| Criterion | Implementation | Hosted evidence |
|---|---|---|
| Runtime | Module-level app, async decorated invoke, app.run | READY; successful live invocations |
| MCP integrations | Gateway discovery; API and Lambda targets | Six registered tools; successful order and refund traces |
| RAG | Decorated tool, Retrieve API, managed search, guard, joined chunks | Platinum response and actual retrieved catalog chunks |
| Cross-session memory | Both strategies, namespace compatibility, actor-scoped retrieval and original turn persistence | Jane/concise recalled in a distinct payload session after a 90-second wait |
| Code Interpreter | Decimal arithmetic, executeCode/clearContext, exact response rendering, labeled fallback | Actual sandbox result: 4,000 / 10% / $99 / 349 |
| Browser | Regional AgentCoreBrowser, bounded timeout, document.title, cleanup | Live Udacity title evaluation and browser-close trace |
| Reflection | 340-word review draft with design, challenge, production example | Ready for user review |

Local verification: 13 offline tests passed. Provided Lambda functions, refund
schema and product catalog are unchanged from the upstream starter.

## Required conversation evidence

- [x] Order: SHIPPED, TRK987654321, UPS, estimated delivery.
- [x] Refund: REF identifier, APPROVED, 3–5 business days, $139.99 actual order amount.
- [x] RAG: Platinum free same-day shipping, 15% discount, priority support; actual retrieval.
- [x] Memory: Jane and concise preference retrieved after a separate-session introduction.
- [x] Discount: actual sandbox call, 4,000 points redeemed, 10%, $99, 349 remaining.
- [x] Browser: live Udacity page and observed title.

A successful CLI exit alone does not establish a passed scenario. Review responses
and service-side tool logs. No fixture output can satisfy these hosted evidence items.
The user reviews and submits the finished bundle; automatic submission is excluded.
