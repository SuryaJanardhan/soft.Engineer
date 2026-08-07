# MVP Architecture: Jira to PR Workflow

## 1. Design Position

The MVP is not a fully autonomous engineering system. It is a durable, policy-driven task-preparation and draft-PR workflow.

It can automatically choose the next eligible task and perform bounded repository work. Humans own Jira status transitions, draft-PR review, merge, and every decision made during an active high-severity incident. Eligible low- to medium-complexity tickets do not wait for plan approval.

The previous idea of "no queues and no databases" is not compatible with automatic selection, webhook retries, pause/resume, or auditability. The smallest credible MVP uses SQLite as durable state and a single worker process. That is deliberately simple, but not disposable.

## 2. Core Rules

1. Jira statuses are human-controlled only. The service has no permission to transition an issue.
2. Only tickets a human has moved to `Agent Ready` are eligible for selection.
3. A deterministic scheduler selects work; the LLM never decides queue priority.
4. A P0 stops normal mutation work. A P1 blocks execution unless a human explicitly approves it.
5. The service may create only a constrained branch and a draft PR. It cannot merge, deploy, or alter production systems.
6. The workflow persists every event receipt, approval, checkpoint, and failure before taking the next action.

## 3. End-to-End Flow

```text
Jira webhook or manual scan
        ↓
Verify signature and persist event receipt
        ↓
Read ticket; never change its Jira status
        ↓
Eligibility + incident policy + deterministic priority selection
        ↓
Create a leased internal job in SQLite
        ↓
Analyze live repository context and publish plan comment
        ↓
Create isolated worktree, make bounded edits, run validation
        ↓
Create draft PR and publish result comment
        ↓
Human reviews, merges, and changes Jira status
```

The scheduler checks Jira only as a source of human lifecycle decisions. Its own progress is stored internally and exposed in logs and comments.

## 4. State Ownership

| Owner | State | Meaning |
|---|---|---|
| Human in Jira | `Backlog`, `Agent Ready`, `PR Review`, `Done`, `Blocked` | Accountability and delivery lifecycle |
| Workflow engine | `queued`, `analyzing`, `executing`, `validating`, `awaiting_pr_review`, `paused`, `failed`, `completed` | Durable technical execution state |

The service may write a structured Jira comment such as “plan ready”, “validation failed”, or “draft PR created.” A comment is evidence; it is not a lifecycle transition.

## 5. Incident and Priority Policy

The queue contains only `Agent Ready` tickets. Selection is deterministic and configurable, for example:

1. Filter out blocked tickets, unsupported repositories, risky paths, ambiguous tasks, and tickets without acceptance criteria.
2. Apply incident policy first.
3. Sort remaining candidates by configured priority tier, then SLA age, then creation time.
4. Respect a per-repository concurrency limit of one for the MVP.

| Condition | Automation behavior |
|---|---|
| P0 active | Do not execute or push changes. Pause jobs at safe checkpoints, notify the incident owner, and provide read-only context only. |
| P1 active | Pause normal queued jobs. Analysis may run, but no branch, edit, commit, or PR occurs. |
| P2 | Normal workflow is allowed when no P0/P1 policy blocks it. |
| P3/P4 | Eligible for automatic selection when capacity exists. |

Pausing is cooperative. A worker checks for a pause before editing, committing, pushing, or opening a PR. It saves a checkpoint rather than being killed mid-write. Humans decide whether a paused job resumes or is cancelled.

## 6. Components

### Intake and event receiver

- Accept a Jira webhook and validate its signature.
- Deduplicate events using an immutable event ID and stored receipt.
- Fetch the current ticket after receiving an event; events are hints, not the source of truth.
- Record the ticket snapshot, source event, and correlation ID.

### Scheduler and durable job store

- SQLite tables for `events`, `jobs`, `job_attempts`, `checkpoints`, `approvals`, and `audit_log`.
- A lease prevents two workers from acting on one ticket simultaneously.
- Exponential retry is allowed only for safe reads and transient remote failures. Editing, pushing, and PR creation require idempotency checks.
- The scheduler must survive a restart without duplicating a branch or PR.

### Policy engine

- Uses configuration, not model output, to decide eligibility and priority.
- Enforces repository allowlists, protected-path deny lists, file-count limits, time limits, and model-cost limits.
- Stops the job when ticket requirements and live repository evidence conflict.

### Planner and repository context

- Uses live repository search, code ownership, recent diffs, tests, and linked documentation.
- Produces a structured plan: target files, expected behavior, risks, test commands, assumptions, and rollback approach.
- Posts the plan as a Jira comment for traceability, then continues automatically when the ticket remains eligible.

### Isolated executor and validator

- Creates an ephemeral worktree per job and uses a restricted tool allowlist.
- Never runs arbitrary shell text supplied by a model. Test commands come from project configuration or an approved allowlist.
- Runs targeted tests, lint/type checks, and a build where available.
- Stops on a failed safety check or when it exceeds configured budget.

### GitHub handoff

- Pushes only an `agent/<ticket-id>` branch in an allowed repository.
- Creates a draft PR with a fixed template: change summary, rationale, validation evidence, remaining risk, test gaps, and rollback notes.
- Cannot approve, merge, dismiss checks, alter branch protections, or deploy.

## 7. Minimal Data Model

```text
events(event_id, received_at, ticket_id, payload_hash, processed_at)
jobs(job_id, ticket_id, state, priority, lease_until, branch_name, pr_url)
job_attempts(attempt_id, job_id, action, idempotency_key, result, created_at)
checkpoints(job_id, phase, repository_ref, worktree_ref, created_at)
approvals(job_id, approval_type, jira_status_snapshot, observed_at)
audit_log(job_id, correlation_id, action, actor, outcome, occurred_at)
```

SQLite is enough for one worker and low volume. Move to Postgres plus a durable workflow engine only when multiple workers, high event rates, or long-running workflows require it.

## 8. Permission Model

| Integration | Allowed | Explicitly prohibited |
|---|---|---|
| Jira | Read issues, read incident state, add comments | Change status, close/reopen tickets, alter priority or assignee |
| GitHub | Read repository metadata, create constrained branches, push commits, create draft PRs | Merge, approve, change protection, alter secrets or workflows |
| Repository worker | Read configured repo and write its ephemeral worktree | Access host secrets, other repositories, arbitrary network targets |
| Notifications | Post status summaries | Treat a Slack reaction as a workflow transition |

## 9. MVP Technology Choices

| Concern | MVP choice | Reason |
|---|---|---|
| Runtime | Python 3.11+ | Straightforward API and tooling support |
| Workflow | Explicit state machine | Easy to test and audit at low volume |
| Persistence | SQLite | Needed for idempotency, pause/resume, and audit history |
| Model integration | Provider adapter with structured output | Avoids coupling policy and state to one model SDK |
| Repository context | Git CLI plus language-aware parser where needed | Live and inspectable evidence |
| GitHub | Official API client or direct REST/GraphQL wrapper | Least-privilege draft PR creation |
| Observability | Structured JSON logs with correlation IDs | Traceable job history from day one |
| Deployment | One containerized worker and one webhook endpoint | Smallest deployable durable unit |

Do not add Kubernetes, a vector database, Temporal, or multi-agent coordination in V1. Add a durable workflow engine after the SQLite worker demonstrates a real need for distributed retries or parallelism.

## 10. Safety Bounds

```python
MAX_FILES_CHANGED = 10
MAX_MODEL_CALLS = 30
MAX_JOB_SECONDS = 600
MAX_RETRY_ATTEMPTS = 2
MAX_CONCURRENT_JOBS_PER_REPOSITORY = 1
```

Additional mandatory controls:

- Require an explicit test-gap note if validation cannot cover the change.
- Deny configured sensitive paths such as deployment manifests, authentication policy, billing, and secrets by default.
- Check pause and incident state before every mutation boundary.
- Record command, exit code, duration, and redacted output for every tool action.
- Fail closed when a permission, signature, or idempotency check cannot be verified.

## 11. MVP Success Criteria

- A repeated webhook never creates duplicate jobs, branches, or PRs.
- The service never changes a Jira status.
- A human can determine why a task was selected and what the system did from the audit record.
- A P0/P1 policy safely pauses normal work before a mutation.
- Every draft PR contains validation evidence or an explicit test gap.
- Restarting the worker resumes or reports work safely from its last checkpoint.

## 12. Build Order

1. Implement configuration, SQLite schema, structured logs, and a dry-run CLI.
2. Add signed Jira intake, event deduplication, manual `Agent Ready` eligibility, and the scheduler.
3. Implement read-only analysis and structured Jira plan comments.
4. Add isolated repository execution, configured validation commands, and draft PR handoff.
5. Add incident pause policy, safe checkpoints, integration tests, and failure/restart tests.

Only enable real repository writes after dry runs prove the policy, audit, duplicate-event, and pause behavior.
