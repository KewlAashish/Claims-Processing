# Claims Processing System Design

Date: 2026-05-20

## Purpose

Build a structured, deterministic claims processing system for an insurance company. The system accepts claim submissions with line items, applies policy coverage rules, computes approved amounts, tracks claim lifecycle state, explains every line-item decision with actual calculation values, and supports member disputes.

This is not a GenAI application. The first version should be Pythonic, explicit, testable, and easy for a reviewer to run locally.

## Assignment Outcomes

The submission should demonstrate:

- Clear domain modeling for members, policies, coverage rules, claims, line items, usage, and disputes.
- Deterministic rule evaluation for coverage, deductible, and annual limit handling.
- Claim-level and line-item-level state management.
- Explanations generated from actual adjudication calculations, not static mock text.
- A working API that can be run locally by a reviewer.
- Tests that encode domain behavior.
- Documentation for domain model, decisions, trade-offs, self-review, and AI collaboration artifacts.

## Recommended Stack

- Python 3.12+
- FastAPI for the HTTP API.
- Pydantic for request and response validation.
- SQLAlchemy 2.x for ORM and persistence.
- SQLite for local development and reviewer demo.
- Pytest for domain and API tests.
- Ruff for linting and formatting.
- Docker and Docker Compose for a low-friction reviewer setup.

SQLite is the right default for this assignment because the system needs real persistence and SQL relationships, but does not need operational database complexity. The implementation should use SQLAlchemy patterns that can move to PostgreSQL later if needed.

## Architecture

The application should be layered around domain behavior rather than around database tables alone.

```text
FastAPI routes
  -> Pydantic schemas
  -> Services for workflows
  -> Domain adjudication logic
  -> Repositories
  -> SQLAlchemy models
  -> SQLite
```

Primary boundaries:

- API layer validates and exposes flows.
- Service layer coordinates workflows such as claim submission, payment, and disputes.
- Domain layer owns adjudication calculations, state aggregation, and explanation generation.
- Persistence layer stores entities and usage updates transactionally.

Claim adjudication and usage updates should happen inside one transaction so a claim result and the corresponding coverage usage cannot diverge.

## Directory Structure

```text
app/
  main.py
  api/
    routes/
      members.py
      policies.py
      claims.py
  domain/
    adjudication.py
    enums.py
    explanations.py
    state_machine.py
  persistence/
    database.py
    models.py
    repositories.py
  schemas/
    claims.py
    members.py
    policies.py
  services/
    claim_service.py
    member_service.py
    policy_service.py
  seed.py

tests/
  domain/
    test_adjudication.py
    test_claim_state_machine.py
  api/
    test_claim_submission.py

docs/
  domain-model.md
  decisions.md
  self-review.md
  superpowers/
    specs/
      2026-05-20-claims-processing-design.md

ai-artifacts/
README.md
Dockerfile
docker-compose.yml
requirements.txt
```

The `ai-artifacts/` directory should eventually contain raw JSONL logs, but those can be added later.

## Domain Entities

### Member

Represents a person who can submit claims.

Fields:

- `id`
- `full_name`
- `date_of_birth`
- `external_member_id`
- `created_at`

### Policy

Represents an insurance policy that owns coverage rules.

Fields:

- `id`
- `policy_number`
- `name`
- `effective_start_date`
- `effective_end_date`
- `status`

### CoverageRule

Represents how a specific coverage type is handled under a policy.

Fields:

- `id`
- `policy_id`
- `coverage_type`
- `annual_limit`
- `deductible_amount`
- `covered`

There should be at most one active coverage rule per `policy_id + coverage_type`.

### MemberPolicy

Represents a member's enrollment in a policy.

Fields:

- `id`
- `member_id`
- `policy_id`
- `status`
- `effective_start_date`
- `effective_end_date`

This is separate from `Member` and `Policy` so policy enrollment can have its own lifecycle.

### CoverageUsage

Tracks how much of a coverage bucket a member has used during a benefit year.

Fields:

- `id`
- `member_id`
- `policy_id`
- `coverage_type`
- `benefit_year`
- `paid_amount_used`
- `deductible_amount_satisfied`

There should be one usage row per `member_id + policy_id + coverage_type + benefit_year`.

### Claim

Represents a submitted claim.

Fields:

- `id`
- `member_id`
- `policy_id`
- `status`
- `diagnosis_code`
- `provider_name`
- `submitted_at`
- `decided_at`

`diagnosis_code` and `provider_name` are sensitive data. They are included because the assignment mentions them, but they should not be written to normal application logs.

### ClaimLineItem

Represents one expense inside a claim.

Fields:

- `id`
- `claim_id`
- `coverage_type`
- `service_date`
- `description`
- `submitted_amount`
- `status`
- `decision_code`
- `deductible_applied`
- `eligible_amount`
- `approved_amount`
- `member_responsibility`
- `remaining_annual_limit_before_claim`
- `remaining_annual_limit_after_claim`
- `explanation`

### ClaimDispute

Represents a member dispute against a claim decision.

Fields:

- `id`
- `claim_id`
- `reason`
- `status`
- `created_at`

The MVP records disputes and marks the claim as disputed. It does not implement a human review or dispute resolution workflow.

## Status Model

### Claim Statuses

```text
SUBMITTED
UNDER_REVIEW
APPROVED
PARTIALLY_APPROVED
DENIED
PAID
DISPUTED
```

### Line Item Statuses

```text
APPROVED
PARTIALLY_APPROVED
DENIED
```

The MVP intentionally excludes `NEEDS_REVIEW` or manual review states. Every submitted line item is deterministically adjudicated by code.

## Claim State Aggregation

After all line items are adjudicated:

```text
All line items APPROVED
=> claim APPROVED

All line items DENIED
=> claim DENIED

Any mix of APPROVED, PARTIALLY_APPROVED, and DENIED
=> claim PARTIALLY_APPROVED

Every line item PARTIALLY_APPROVED
=> claim PARTIALLY_APPROVED

Approved or partially approved claim is paid
=> claim PAID

Eligible claim is disputed
=> claim DISPUTED
```

Payment and dispute are explicit lifecycle transitions after adjudication.

## Deductible Model

The MVP uses a simple deductible model:

- A deductible is the amount a member must pay out of pocket before reimbursement begins.
- Deductible is tracked per `member + policy + coverage_type + benefit_year`.
- After the deductible is satisfied, eligible covered expenses are reimbursed up to the remaining annual limit.
- There is no reimbursement percentage in the MVP because the requirements do not ask for percentage-based coinsurance.

Example:

```text
Rule:
OPD annual limit = 10000
OPD deductible = 1000

Existing usage:
deductible satisfied = 600
paid so far = 2000

New OPD line item:
submitted amount = 2000

Remaining deductible = 400
Deductible applied = 400
Eligible amount = 1600
Remaining annual limit before claim = 8000
Approved amount = 1600
Member responsibility = 400
Remaining annual limit after claim = 6400
```

## Adjudication Rules

For each line item:

```text
If coverage type is not covered:
  approved amount = 0
  status = DENIED
  decision_code = DENIED_NOT_COVERED

Else:
  calculate remaining deductible
  apply deductible to submitted amount
  calculate eligible amount after deductible
  calculate remaining annual limit
  cap approved amount by remaining annual limit
  calculate member responsibility

If approved amount == submitted amount:
  status = APPROVED

If approved amount > 0 and approved amount < submitted amount:
  status = PARTIALLY_APPROVED

If approved amount == 0:
  status = DENIED
```

Expected decision codes:

```text
COVERED_FULLY
PARTIAL_DEDUCTIBLE_APPLIED
PARTIAL_LIMIT_REMAINING
PARTIAL_DEDUCTIBLE_AND_LIMIT
DENIED_NOT_COVERED
DENIED_LIMIT_EXHAUSTED
DENIED_DEDUCTIBLE_NOT_MET
```

## Explanation Generation

Explanation text must be generated from the actual adjudication result object. It should not be hardcoded independently from the calculation.

Example response shape:

```json
{
  "line_item_id": "line_123",
  "coverage_type": "OPD",
  "submitted_amount": 2000,
  "deductible_applied": 400,
  "eligible_amount": 1600,
  "approved_amount": 1600,
  "member_responsibility": 400,
  "remaining_annual_limit_before_claim": 8000,
  "remaining_annual_limit_after_claim": 6400,
  "status": "PARTIALLY_APPROVED",
  "decision_code": "PARTIAL_DEDUCTIBLE_APPLIED",
  "message": "Partially approved. The submitted amount was 2000. 400 was applied to the remaining OPD deductible, leaving 1600 eligible for reimbursement. The remaining annual OPD limit before this claim was 8000, so 1600 was approved."
}
```

This makes the explanations auditable and testable.

## API Surface

### `POST /members`

Registers a member who can submit claims. Keeps member setup explicit instead of hardcoding members in the database.

### `POST /policies`

Creates an insurance policy container. A policy owns coverage rules and can later be assigned to members.

### `POST /policies/{policy_id}/coverage-rules`

Adds or updates the rules that decide whether a coverage type is reimbursable, what the annual limit is, and what deductible applies.

### `POST /members/{member_id}/policies`

Enrolls a member into a policy through `MemberPolicy`. This tracks active or inactive policy status separately from the member and policy records.

### `GET /members/{member_id}`

Supports demo and debugging by showing member details and policy enrollment.

### `GET /policies/{policy_id}`

Supports demo and debugging by showing policy details and coverage rules.

### `POST /claims`

Main assignment flow. Accepts structured claim data with line items, validates member and policy eligibility, adjudicates each line item, updates usage, and returns claim-level plus line-item decisions.

### `GET /claims/{claim_id}`

Lets a reviewer inspect the final adjudication result after submission, including statuses, approved amounts, member responsibility, and explanations.

### `POST /claims/{claim_id}/pay`

Moves an approved or partially approved claim to `PAID`. Keeps payment as a lifecycle transition without building real payment rails.

### `POST /claims/{claim_id}/disputes`

Covers the explicit requirement that members can dispute decisions. Records the dispute reason and marks the claim as `DISPUTED`, while leaving actual dispute resolution out of MVP scope.

## Setup and Demo Expectations

The README should support two paths:

- Docker path for reviewers.
- Local Python path for development.

Recommended reviewer flow:

```text
docker compose up --build
run seed command or use auto-seeded startup
open API docs
submit sample claim
inspect claim result
mark claim paid
submit dispute
run tests
```

The README should include ready-to-copy `curl` examples for setup, claim submission, payment, and dispute flows.

## Testing Strategy

Tests should focus on domain behavior, not only HTTP status codes.

Core tests:

- Unknown member cannot submit a claim.
- Member without active policy cannot submit a claim.
- Uncovered coverage type is denied with `DENIED_NOT_COVERED`.
- Deductible absorbs full amount and returns `DENIED_DEDUCTIBLE_NOT_MET`.
- Deductible partially applies and remaining amount is approved.
- Annual limit caps reimbursement and returns partial approval.
- Exhausted annual limit returns denial.
- Mixed line-item results aggregate to claim `PARTIALLY_APPROVED`.
- All approved line items aggregate to claim `APPROVED`.
- All denied line items aggregate to claim `DENIED`.
- Paid transition only works for approved or partially approved claims.
- Dispute transition only works for eligible claim statuses.
- Duplicate line items inside the same claim are rejected when `coverage_type`, `service_date`, `description`, and `submitted_amount` are all identical.

## Edge Cases

The MVP should handle:

- Unknown member.
- Unknown policy.
- Member has no active policy.
- Policy inactive or outside effective dates.
- Coverage type not covered.
- Claim line amount is zero or negative.
- Duplicate line items inside the same claim.
- Annual limit already exhausted.
- Deductible not yet satisfied.
- Mixed approved, partially approved, and denied line items.
- Dispute submitted while claim is still `SUBMITTED` or `UNDER_REVIEW`.
- Dispute submitted for a non-existent claim.

The MVP should not handle:

- User authentication.
- Policy purchase or enrollment business workflows beyond direct setup APIs.
- Provider account management.
- Admin dashboards.
- Email notifications.
- Real payment rails.
- Human review queues.
- Retroactive policy changes.
- Multi-tenant access control.

## Security and Sensitive Data

Claims may include member names, diagnosis codes, and provider details. The MVP should acknowledge this without overbuilding security features outside the assignment scope.

Decisions:

- Do not log diagnosis codes, member names, or provider names in normal application logs.
- Keep sensitive fields explicit in models and docs.
- Use local-only SQLite storage for the assignment.
- Document production hardening needs, such as auth, access control, encryption, audit logs, and retention policies.

## Assignment Documentation Plan

The implementation should include:

- `docs/domain-model.md`: entities, relationships, status model, and rule model.
- `docs/decisions.md`: stack choice, deterministic adjudication, SQLite, excluded manual review, excluded reimbursement percentages, and other trade-offs.
- `docs/self-review.md`: honest assessment after implementation, including what is solid, what is thin, and what would be improved next.
- `README.md`: setup, run, seed, API examples, tests, and Docker instructions.
- `ai-artifacts/`: raw JSONL session logs and any chat exports or notable prompts.

`docs/self-review.md` should be written after the implementation exists so it reflects the actual code rather than a speculative review.

## Implementation Choices

These choices are part of the approved design:

- `POST /claims` performs adjudication immediately and returns the full decision result in the same request.
- Public API IDs are UUID strings. The database can store them as strings for SQLite simplicity.
- Seed data is created through `python -m app.seed` instead of automatic startup seeding.
- Duplicate line items inside the same claim are rejected when `coverage_type`, `service_date`, `description`, and `submitted_amount` are all identical.
