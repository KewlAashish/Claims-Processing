# Domain Model

## Entities

- `Member`: person who submits claims. Uses `external_member_id` for a source-system identifier.
- `Policy`: coverage container with effective dates and lifecycle status.
- `CoverageRule`: one policy rule per coverage type, including annual limit, deductible, and whether it is covered.
- `MemberPolicy`: enrollment connecting a member to a policy with its own active window.
- `CoverageUsage`: per member, policy, coverage type, and benefit year tracking paid amount and deductible satisfied.
- `Claim`: submitted reimbursement request containing sensitive diagnosis and provider fields.
- `ClaimLineItem`: adjudicated expense with calculation values, status, decision code, and explanation.
- `ClaimDispute`: member dispute record that marks the claim as disputed.

## Relationships

- A policy has many coverage rules.
- A member has many policy enrollments.
- A policy has many enrolled members through `MemberPolicy`.
- A member and policy pair can have many claims.
- A claim has one or more line items.
- Coverage usage is separate from claim line items so benefit-year balances can be updated transactionally.

## Status Model

Claim statuses:

```text
SUBMITTED -> UNDER_REVIEW -> APPROVED | PARTIALLY_APPROVED | DENIED
APPROVED | PARTIALLY_APPROVED -> PAID
APPROVED | PARTIALLY_APPROVED | DENIED | PAID -> DISPUTED
```

Line item statuses are `APPROVED`, `PARTIALLY_APPROVED`, and `DENIED`.

After adjudication, claim status is aggregated from line items:

- all approved: `APPROVED`
- all denied: `DENIED`
- any mixed or partially approved result: `PARTIALLY_APPROVED`

## Rule Model

The MVP uses explicit Python domain logic rather than a dynamic rule language. Each line item is evaluated
against a single `CoverageRule` by coverage type:

1. Reject uncovered or missing rules.
2. Apply remaining deductible.
3. Calculate eligible amount after deductible.
4. Cap reimbursement by remaining annual limit.
5. Generate a decision code, status, and explanation from the computed values.

Deductible and annual limit usage are tracked per member, policy, coverage type, and benefit year.
