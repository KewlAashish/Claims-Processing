# HTTP Demo Scenarios Design

## Goal

Create a reviewer-friendly demo suite that exercises the running FastAPI service through HTTP. The demo should make the claims workflow easy to inspect from the terminal and leave a markdown audit trail for each executed scenario.

## User Experience

The reviewer starts the API, then runs either the demo index or a specific scenario script:

```powershell
uvicorn app.main:app --reload
python demo/index.py
python demo/scenarios/partial_limit.py
```

Each scenario prints staged progress in the CLI: setup, submission, adjudication, optional payment or dispute, and final outcome. Each run also writes a markdown report under `demo/output/` containing the important request summaries, created resource IDs, claim status, line decisions, money fields, explanations, and final state.

## Architecture

The demo code lives under `demo/` and stays separate from application code.

- `demo/index.py` lists available scenarios, checks that the API is reachable, and prints exact commands.
- `demo/lib/api_client.py` wraps HTTP requests against the service. It reads the base URL from `DEMO_API_URL` and defaults to `http://localhost:8000`.
- `demo/lib/rendering.py` owns CLI formatting and markdown report writing.
- `demo/scenarios/*.py` contains small, self-contained scenario scripts.
- `demo/output/` stores generated markdown reports and keeps a `.gitkeep` file in source control.

## Scenarios

The first scenario set covers the core reviewer-visible business outcomes:

- `approved_claim.py`: creates a covered claim that is fully approved, then marks it paid.
- `partial_deductible.py`: shows partial approval caused by a remaining deductible.
- `partial_limit.py`: uses prior usage setup to show an annual limit cap and member responsibility.
- `denied_not_covered.py`: submits an uncovered coverage type and shows denial.
- `dispute_flow.py`: submits a decided claim, opens a dispute, and shows the claim status transition.

Every scenario creates unique member and policy identifiers so repeated runs do not collide.

## Data Flow

Scenario scripts create demo data through the public API: member, policy, coverage rules, enrollment, claim submission, and optional pay/dispute actions. They then fetch the claim to render the authoritative final state returned by the service.

The scripts should not bypass the API or import app services. Shared helper code may shape payloads and render outputs, but business decisions must come from the running service.

## Error Handling

The API client fails fast with a concise message when the service is unavailable or a request returns an unexpected status. The index script should make startup requirements obvious by checking `/openapi.json`.

Generated markdown should only be written after enough data exists to produce a useful report. If a scenario fails mid-run, the terminal output should show the failed stage and HTTP response details.

## Testing And Verification

Verification will use the repository's existing commands plus a smoke run:

```powershell
pytest
ruff check .
ruff format .
uvicorn app.main:app --reload
python demo/scenarios/approved_claim.py
```

The scenario smoke run validates that the demo exercises the actual HTTP API and creates a markdown output file.

## Risks

The demo depends on a running API and the existing local database. That is intentional for realism, but the scripts must print a clear message when the API is not available. The scenario data should be unique per run to avoid collisions in repeated demos.
