# soft.Engineer

Python MVP for a bounded Jira-to-draft-PR workflow.

The `agents/` package separates deterministic task orchestration from the LangGraph agent flow:

- The SQLite job store owns event receipts, job leases, audit records, and final job state.
- Policy functions decide eligibility and pause work for P0/P1 incidents.
- LangGraph runs one leased job through preflight, context collection, planning, execution, validation, bounded repair, and draft-PR handoff.
- The local adapter is safe demo mode. It does not call Jira or GitHub, change Jira status, write to a repository, or open a real PR.

## Run the MVP

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m agents.main --ticket ENG-101 --priority P3
```

Simulate an active incident pause:

```bash
.venv/bin/python -m agents.main --ticket ENG-102 --priority P3 --incident P0
```

Run the tests:

```bash
.venv/bin/python -m pytest -q
```
