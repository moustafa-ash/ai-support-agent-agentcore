# Rubric checklist

| Criterion | Implementation | Hosted evidence |
|---|---|---|
| Runtime | Module-level app, async decorated invoke, app.run | Pending |
| MCP integrations | Gateway discovery; API and Lambda targets | Pending |
| RAG | Decorated tool, Retrieve API, managed search, guard, joined chunks | Pending |
| Cross-session memory | Both strategies, namespace compatibility, actor-scoped retrieval and original turn persistence | Pending |
| Code Interpreter | Self-contained decimal arithmetic, executeCode/clearContext, structured breakdown, labeled fallback | Pending |
| Browser | Regional AgentCoreBrowser added to tools, bounded session timeout, cleanup | Pending |
| Reflection | 302-word review draft with design, challenge, production example | Draft ready |

Local verification: 12 offline tests passed. Provided Lambda functions, refund
schema and product catalog are unchanged from the upstream starter.

## Required conversation evidence

- [ ] Order: SHIPPED, TRK987654321, UPS, estimated delivery.
- [ ] Refund: REF identifier, APPROVED, 3–5 business days, actual order amount.
- [ ] RAG: Platinum free same-day shipping, 15% discount, priority support; actual retrieval.
- [ ] Memory: Jane and concise preference retrieved after a separate-session introduction.
- [ ] Discount: actual sandbox call, 4,000 points redeemed, 10%, $99, 349 remaining.
- [ ] Browser: live Udacity page content and observed title.

A successful CLI exit alone does not establish a passed scenario. Review responses
and service-side tool logs. No fixture output can satisfy these hosted evidence items.
The user reviews and submits the finished bundle; automatic submission is excluded.
