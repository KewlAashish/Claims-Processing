# Decisions And Trade-Offs

## Stack

- FastAPI provides a small REST surface with OpenAPI docs for reviewers.
- SQLAlchemy 2.x keeps persistence explicit and portable.
- SQLite is used for local setup and Docker review. The schema avoids SQLite-specific behavior where practical.
- Pydantic validates API input and output.
- Pytest and Ruff are the verification path.

## Domain Decisions

- `POST /claims` adjudicates immediately. There is no manual review queue in the MVP.
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

## Known Trade-Offs

- There is no migration tool such as Alembic; `create_all` is sufficient for the assignment but not for production.
- The API has setup endpoints for members, policies, and enrollment so the reviewer can run a complete demo.
- Coverage types are normalized to uppercase strings rather than modeled as a fixed enum, because insurers often add products.
- Payment is a state transition only. No real payment rail or ledger is implemented.
- Disputes are recorded but not resolved.
