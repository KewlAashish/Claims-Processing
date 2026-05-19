# Decisions And Trade-Offs

## Stack

- FastAPI provides a small REST surface with OpenAPI docs for reviewers.
- SQLAlchemy 2.x keeps persistence explicit and portable.
- SQLite is used for local setup and Docker review. The schema avoids SQLite-specific behavior where practical.
- Pydantic validates API input and output.
- Pytest and Ruff are the verification path.

## Domain Decisions

- `POST /claims` adjudicates immediately. There is no manual review queue in the MVP.
- The state model includes `SUBMITTED` and `UNDER_REVIEW`, but the MVP does not expose them as separate
  asynchronous workflow steps. A later high-volume version should persist submitted claims first, enqueue
  review/adjudication work, and make `UNDER_REVIEW` observable while workers process the queue.
- Coverage rules are code-evaluated records, not a DSL. This keeps behavior deterministic and testable.
- Coverage usage updates happen in the same commit as claim and line item persistence.
- Missing coverage rules are treated as not covered.
- There is no coinsurance percentage because the assignment did not require it.
- Duplicate line items in a single submission are rejected using coverage type, service date, description, and submitted amount.
- Public IDs are UUID strings stored as SQLite text.

## Security Scope

Diagnosis codes and provider names are stored but not logged by the application. Production hardening would
need authentication, authorization, encryption at rest, audit logging, retention controls, and strict access
policies. Those are documented as out of scope for this take-home build.

Authentication, role-based access control, policy administration, reporting, notifications, provider account
management, and real payment rails are treated as adjacent product concerns rather than core assignment
scope. They are intentionally not built so the submission stays focused on claims adjudication, state, usage,
and explanations.

## Known Trade-Offs

- There is no migration tool such as Alembic; `create_all` is sufficient for the assignment but not for production.
- The API has setup endpoints for members, policies, and enrollment so the reviewer can run a complete demo.
- Coverage types are normalized to uppercase strings rather than modeled as a fixed enum, because insurers often add products.
- Payment is a state transition only. No real payment rail or ledger is implemented.
- Disputes are recorded but not resolved.

## Future Scope

The MVP intentionally keeps adjudication synchronous and deterministic. If this moved toward production,
the next step would be an event-driven claims workflow where claim submission, adjudication, manual review,
payment, and dispute handling are separate observable stages.

### Queue-Backed Claim Workflow

`POST /claims` should persist a claim as `SUBMITTED` and return quickly. Background workers would then pull
claim work items from a queue, move them into `UNDER_REVIEW`, run deterministic adjudication, and finalize
them as approved, partially approved, denied, or routed for manual review. This would make `SUBMITTED` and
`UNDER_REVIEW` meaningful operational states rather than internal concepts.

Important production concerns in that model include idempotency keys for duplicate submissions, worker
leasing, retries, dead-letter handling, priority queues, status history, and queue-depth/latency metrics.

### Secured Operations Interfaces

A production version should include secured interfaces for both members and internal claim reviewers.
Members need a simple claim tracker showing the current stage, decision, payment status, dispute status,
and explanations. Reviewers need a queue interface for claims that need manual review, disputes, missing
documentation, failed adjudication, or escalation.

The reviewer queue should support filtering by status, claim age, amount, coverage type, policy, and SLA;
assignment and ownership; notes; decision overrides with required reasons; and a full audit trail for every
state transition and reviewer action.

### GenAI-Assisted Manual Review

If policy documents, claim packets, provider notes, or coverage rules become more unstructured, a GenAI
layer could assist human reviewers. The deterministic adjudication engine should remain the source of truth
for structured rules. GenAI should be used as a reviewer-assist layer, not as the final decision maker.

Useful AI-assisted workflows include summarizing claim packets, extracting candidate coverage terms from
policy documents, suggesting likely decisions with citations, flagging missing documentation, comparing
claim facts against policy language, and drafting member-facing explanations for reviewer approval.

The AI layer would need guardrails: cite source text or rule IDs for recommendations, store model and prompt
versions, log retrieved sources, require human confirmation for final decisions, and avoid sending
unnecessary sensitive health data to model providers.

### Production Hardening

The system would also need PostgreSQL, Alembic migrations, row locking or optimistic concurrency for coverage
usage updates, authentication, role-based access control, encryption at rest, retention policies, structured
audit events, request IDs, rate limits, metrics, and traceable adjudication events.
