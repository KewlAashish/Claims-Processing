# Claims Processing System

Deterministic claims adjudication API for an insurance reimbursement workflow. It models
members, policies, coverage rules, enrollments, coverage usage, claim line decisions, payment,
and disputes.

## Run With Docker

```bash
docker compose up --build
```

In another terminal, seed demo data:

```bash
docker compose exec api python -m app.seed
```

Open API docs at http://localhost:8000/docs.

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Run tests and linting:

```bash
pytest
ruff check .
ruff format .
```

## HTTP Demo Scripts

Start the API, then run the scenario index or an individual scenario:

```bash
uvicorn app.main:app --reload
python demo/index.py
python demo/scenarios/approved_claim.py
python demo/scenarios/partial_deductible.py
python demo/scenarios/partial_limit.py
python demo/scenarios/denied_not_covered.py
python demo/scenarios/dispute_flow.py
```

Each scenario calls the running HTTP API, prints the workflow stages in the terminal,
and writes a markdown report to `demo/output/`. Set `DEMO_API_URL` if the API is not
running on `http://localhost:8000`.

## Demo Flow

Create a member:

```bash
curl -X POST http://localhost:8000/members ^
  -H "Content-Type: application/json" ^
  -d "{\"full_name\":\"Asha Patel\",\"date_of_birth\":\"1990-01-01\",\"external_member_id\":\"MEM-001\"}"
```

Create a policy:

```bash
curl -X POST http://localhost:8000/policies ^
  -H "Content-Type: application/json" ^
  -d "{\"policy_number\":\"POL-001\",\"name\":\"Standard Health\",\"effective_start_date\":\"2026-01-01\",\"effective_end_date\":\"2026-12-31\"}"
```

Add a coverage rule:

```bash
curl -X POST http://localhost:8000/policies/{policy_id}/coverage-rules ^
  -H "Content-Type: application/json" ^
  -d "{\"coverage_type\":\"OPD\",\"annual_limit\":\"10000\",\"deductible_amount\":\"1000\",\"covered\":true}"
```

Enroll the member:

```bash
curl -X POST http://localhost:8000/members/{member_id}/policies ^
  -H "Content-Type: application/json" ^
  -d "{\"policy_id\":\"{policy_id}\",\"effective_start_date\":\"2026-01-01\",\"effective_end_date\":\"2026-12-31\"}"
```

Submit a claim:

```bash
curl -X POST http://localhost:8000/claims ^
  -H "Content-Type: application/json" ^
  -d "{\"member_id\":\"{member_id}\",\"policy_id\":\"{policy_id}\",\"diagnosis_code\":\"J10\",\"provider_name\":\"City Clinic\",\"line_items\":[{\"coverage_type\":\"OPD\",\"service_date\":\"2026-03-01\",\"description\":\"Consultation\",\"submitted_amount\":\"2000\"}]}"
```

Inspect, pay, and dispute:

```bash
curl http://localhost:8000/claims/{claim_id}
curl -X POST http://localhost:8000/claims/{claim_id}/pay
curl -X POST http://localhost:8000/claims/{claim_id}/disputes ^
  -H "Content-Type: application/json" ^
  -d "{\"reason\":\"Member believes the provider submitted additional records.\"}"
```

## Notes

- `POST /claims` adjudicates immediately and updates coverage usage in the same database commit.
- Explanations are generated from adjudication result values.
- Diagnosis codes and provider names are stored because they are part of the assignment, but the app does
  not log them.

## Submission Checklist

- Include the `.git/` directory in the final archive so reviewers can inspect commit history, sequencing,
  and iteration.
- Include raw coding-agent JSONL session logs in `ai-artifacts/`.
- Include `app/`, `tests/`, `docs/`, `README.md`, `requirements.txt`, `pyproject.toml`, `Dockerfile`,
  and `docker-compose.yml`.
