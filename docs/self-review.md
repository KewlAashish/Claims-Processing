# Self-Review

## Solid

- The adjudication logic is isolated from FastAPI and SQLAlchemy, with direct domain tests for deductible,
  annual limit, uncovered services, and state aggregation.
- Claim submission persists the claim, line items, and coverage usage in one service workflow and one commit.
- Line-item explanations are generated from the same calculation values returned in the API response.
- The API covers the complete reviewer demo path: setup, claim submission, inspection, payment, and dispute.
- API tests cover multi-line claims that consume the same coverage bucket in sequence, missing coverage
  rules, policy and enrollment date validation, payment transitions, dispute creation, duplicate line item
  rejection, and unknown member handling.
- Raw coding-agent JSONL session logs are included under `ai-artifacts/` for process review.

## Thin

- There is no Alembic migration setup; database creation uses SQLAlchemy metadata.
- Claim submission and adjudication happen synchronously in one request. A higher-volume production phase
  should separate `SUBMITTED` and `UNDER_REVIEW` into durable workflow states backed by a task queue and
  worker processing.
- There is no concurrency protection around coverage usage rows beyond the single-process SQLite demo path.
- Error responses are intentionally simple and do not include structured application error codes.
- Disputes can be opened, but there is no resolution workflow that sends the claim back through review.

## Out Of Scope For This Assignment

- Authentication and role-based access control.
- Admin panels for managing policies, members, providers, or coverage catalogs.
- Real payment rails, ledgers, email notifications, reporting, analytics, or provider/member account
  management.

## Next Improvements

- Add Alembic migrations and a PostgreSQL profile.
- Add optimistic locking or transactional row locking for usage updates in a production database.
- Add structured audit events that avoid sensitive claim details.
- Add tests for repeated claims across the same benefit year, especially when earlier claims have already
  consumed part or all of a coverage limit.
- Split synchronous adjudication into a queue-backed workflow where `SUBMITTED`, `UNDER_REVIEW`, manual
  review, and retry states are observable.
- Add secured member and reviewer interfaces for claim tracking, queue management, assignment, notes, and
  audit history.
- Explore a GenAI-assisted manual review layer for unstructured policy documents or claim packets, with
  citations, human approval, model/version logging, and sensitive-data controls.
- Add dispute resolution states if the product needs a human review workflow.
