# MVP Architecture: Jira to PR Workflow

## 1. Design Position

The MVP is not a fully autonomous engineering system. It is a durable, policy-driven task-preparation and draft-PR workflow.

It can automatically choose the next eligible task and perform bounded repository work. Humans own Jira status transitions, draft-PR review, merge, and every decision made during an active high-severity incident. Eligible low- to medium-complexity tickets do not wait for plan approval.

The previous idea of "no queues and no databases" is not compatible with automatic selection, webhook retries, pause/resume, or auditability. The smallest credible MVP uses SQLite as durable state and a single worker process. That is deliberately simple, but not disposable.

## 2. Core Rules

1. Jira statuses are human-controlled only. The service has no permission to transition an issue.
2. Only tickets a human has moved to `Agent Ready` are eligible for selection.
3. A deterministic scheduler selects work; the LLM never decides queue priority.
4. A P0 or P1 stops normal mutation work. The system may gather read-only evidence, but it does not edit, push, or open a PR for an active P0/P1.
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
LangGraph executes analysis, implementation, repair, and validation
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

### LangGraph agent executor

LangGraph owns the bounded, agentic portion of a single job. It is not the scheduler and it does not get credentials for Jira status transitions or merges. Its graph state is scoped to one `job_id`; the application database remains the audit and coordination source of truth.

The graph provides what a plain linear function does not: conditional routes, durable checkpoints after each node, a controlled repair loop after failed validation, and an explicit safe stop before each external mutation.

```text
preflight
  → collect_context
  → make_plan
  → prepare_worktree
  → implement
  → validate ── pass ──→ create_draft_pr
       │                       ↓
       └── repair ─────────────┘
              │
              └── retry limit, policy failure, or pause → stop
```

Each node receives and returns JSON-serializable state only. Network calls, Git writes, and model calls are wrapped as idempotent activities using the job ID and a mutation-specific idempotency key. A resumed node must be safe to run again.

### Isolated executor and validator

- Creates an ephemeral worktree per job and uses a restricted tool allowlist.
- Never runs arbitrary shell text supplied by a model. Test commands come from project configuration or an approved allowlist.
- Runs targeted tests, lint/type checks, and a build where available.
- Stops on a failed safety check or when it exceeds configured budget.

### GitHub handoff

- Pushes only an `agent/<ticket-id>` branch in an allowed repository.
- Creates a draft PR with a fixed template: change summary, rationale, validation evidence, remaining risk, test gaps, and rollback notes.
- Cannot approve, merge, dismiss checks, alter branch protections, or deploy.

### Central repository knowledge base

The knowledge base is separate from LangGraph checkpoints. It is durable shared memory for one configured core repository and contains a code graph plus prior-fix evidence:

- Code nodes: Python modules, classes, and functions.
- Code edges: module definitions and imports.
- Fix records: ticket summary, changed files, validation evidence, draft PR URL, and a human-recorded outcome of `merged`, `rejected`, or `reverted`.

Before planning, the context node queries symbols related to the ticket and similar prior fixes. The model receives those as evidence, not instructions. A previous rejected or reverted fix must be treated as a warning, never copied automatically.

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

## 8. LangGraph Function Design

The implementation should have thin graph nodes and ordinary testable functions beneath them. A node coordinates one decision boundary; helper functions do the I/O and return typed data. Do not bury tool execution, policy checks, and retry logic inside a single model prompt.

### Graph state

```python
class AgentState(TypedDict):
    job_id: str
    ticket: NormalizedTicket
    policy: PolicyDecision
    worktree_path: str | None
    repository_ref: str
    context: RepositoryContext
    plan: ImplementationPlan | None
    changes: list[FileChange]
    validation: ValidationReport | None
    repair_attempts: int
    pr_url: str | None
    stop_reason: str | None
```

`job_id`, `repository_ref`, `repair_attempts`, and every side-effect result must be checkpointed. Never put raw secrets, full unredacted command output, or an unrestricted chat history in graph state.

### Deterministic application functions

| Function | Responsibility | Must not do |
|---|---|---|
| `receive_jira_event(payload)` | Verify webhook, deduplicate, store receipt | Start an agent run directly |
| `select_next_job()` | Apply incident, priority, eligibility, and capacity policy | Ask an LLM which ticket matters most |
| `acquire_job_lease(job_id)` | Guarantee one active worker per job | Modify Jira status |
| `should_pause(job_id)` | Check incident state and cancellation before mutation | Depend on stale graph state alone |
| `record_audit_event(...)` | Persist actor, action, outcome, correlation ID | Store secrets or raw credentials |
| `run_agent_job(job_id)` | Load one leased job and invoke/resume LangGraph | Select or reprioritize other jobs |

### LangGraph nodes and helpers

| Node | Helper functions | Input | Output and route |
|---|---|---|---|
| `preflight_node` | `should_pause`, `verify_policy`, `verify_lease` | Job and policy | Route to `stop` if paused or rejected; otherwise `collect_context` |
| `collect_context_node` | `search_repo`, `read_codeowners`, `read_recent_diffs`, `find_tests` | Ticket and repository ref | Bounded `RepositoryContext` |
| `make_plan_node` | `call_model_structured`, `validate_plan_schema`, `check_plan_scope` | Ticket and context | Valid `ImplementationPlan`, or `stop` for ambiguity/scope failure |
| `prepare_worktree_node` | `create_worktree`, `create_agent_branch`, `record_checkpoint` | Approved repository ref | Isolated worktree and branch name |
| `implement_node` | `agent_tool_loop`, `read_file`, `apply_patch`, `run_allowed_command` | Plan and worktree | Recorded file changes; route to `validate` or `stop` |
| `validate_node` | `run_configured_checks`, `collect_diff`, `evaluate_validation` | Changes and allowed commands | Route to `create_draft_pr`, `repair`, or `stop` |
| `repair_node` | `call_model_structured`, `agent_tool_loop`, `increment_repair_attempt` | Failed validation report | Route to `validate`, or `stop` at retry limit |
| `create_draft_pr_node` | `push_branch_idempotently`, `create_draft_pr_idempotently`, `post_jira_comment` | Validated diff and evidence | PR URL and `completed` |
| `stop_node` | `record_stop_reason`, `post_jira_comment` | Stop reason | `paused` or `failed`; never changes Jira status |

### Tool contract

The LLM can request tools, but tools enforce policy independently. Every tool takes `job_id` and checks the lease, pause flag, repository allowlist, and path policy before acting.

```python
def apply_patch(job_id: str, path: str, patch: str) -> ToolResult:
    require_active_lease(job_id)
    require_not_paused(job_id)
    require_allowed_path(path)
    require_file_budget(job_id)
    return apply_patch_in_worktree(job_id, path, patch)

def run_allowed_command(job_id: str, command_id: str) -> CommandResult:
    require_active_lease(job_id)
    require_not_paused(job_id)
    command = configured_command(command_id)
    return run_in_worktree(job_id, command)
```

The model supplies neither arbitrary shell text nor arbitrary filesystem paths. Validation commands are selected from repository configuration. The agent may propose a test command, but the policy layer must map that proposal to an approved command ID.

### Persistence approach

For local development, a SQLite-backed LangGraph checkpointer is acceptable. For production or any workflow that must survive concurrent workers, use a database-backed production checkpointer such as Postgres and keep the application audit records in the same durable database. LangGraph checkpoints resume the agent graph; the `jobs` table and idempotency keys remain responsible for external side effects such as Git pushes and PR creation.

### MVP module layout

The Python MVP implements these boundaries in `agents/`:

```text
agents/
├── main.py                 # CLI and run_agent_job entry point
├── graph.py                # LangGraph topology and conditional routes
├── config.py               # File, command, and repair budgets
├── models.py               # Ticket, policy, and graph-state contracts
├── policy.py               # Deterministic eligibility and incident checks
├── store.py                # SQLite events, jobs, leases, and audit log
├── services.py             # Explicit dependency container
├── model.py                # Structured planning-model interface and demo adapter
├── repository.py           # Safe demo repository and draft-PR adapter
└── nodes/
    ├── preflight.py        # Lease and policy guard
    ├── context.py          # Repository search sub-functions
    ├── planning.py         # Structured planning and scope validation
    ├── workspace.py        # Worktree and branch preparation
    ├── execution.py        # Policy-enforced tool loop
    ├── validation.py       # Configured checks and repair routing
    ├── repair.py           # One bounded repair attempt
    ├── handoff.py          # Idempotent draft-PR handoff
    └── stop.py             # Safe failure and pause handling
```

The initial repository and model adapters are intentionally local demo adapters. Replace them with production adapters only after the policy, idempotency, and integration tests cover their side effects.

## 9. Permission Model

| Integration | Allowed | Explicitly prohibited |
|---|---|---|
| Jira | Read issues, read incident state, add comments | Change status, close/reopen tickets, alter priority or assignee |
| GitHub | Read repository metadata, create constrained branches, push commits, create draft PRs | Merge, approve, change protection, alter secrets or workflows |
| Repository worker | Read configured repo and write its ephemeral worktree | Access host secrets, other repositories, arbitrary network targets |
| Notifications | Post status summaries | Treat a Slack reaction as a workflow transition |

## 10. MVP Technology Choices

| Concern | MVP choice | Reason |
|---|---|---|
| Runtime | Python 3.11+ | Straightforward API and tooling support |
| Job orchestration | Explicit state machine + SQLite | Owns queue policy, leases, audit state, and Jira boundaries |
| Agent workflow | LangGraph | Checkpointed graph, conditional repair loop, and bounded tool execution |
| Persistence | SQLite | Needed for idempotency, pause/resume, and audit history |
| Model integration | Provider adapter with structured output | Avoids coupling policy and state to one model SDK |
| Repository context | Git CLI plus language-aware parser where needed | Live and inspectable evidence |
| GitHub | Official API client or direct REST/GraphQL wrapper | Least-privilege draft PR creation |
| Observability | Structured JSON logs with correlation IDs | Traceable job history from day one |
| Deployment | One containerized worker and one webhook endpoint | Smallest deployable durable unit |

Do not add Kubernetes, a vector database, Temporal, or multi-agent coordination in V1. LangGraph is used for the agent workflow, not as a replacement for the scheduler or policy engine. Adopt Postgres-backed checkpoints before calling the system production-ready.

## 11. Safety Bounds

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

## 12. MVP Success Criteria

- A repeated webhook never creates duplicate jobs, branches, or PRs.
- The service never changes a Jira status.
- A human can determine why a task was selected and what the system did from the audit record.
- A P0/P1 policy safely pauses normal work before a mutation.
- Every draft PR contains validation evidence or an explicit test gap.
- Restarting the worker resumes or reports work safely from its last checkpoint.
- A validation failure may enter one bounded LangGraph repair loop, but cannot retry indefinitely or bypass policy.

## 13. Build Order

1. Implement configuration, SQLite schema, structured logs, and a dry-run CLI.
2. Add signed Jira intake, event deduplication, manual `Agent Ready` eligibility, and the scheduler.
3. Implement the LangGraph read-only path: `preflight`, `collect_context`, and `make_plan`, with structured output tests.
4. Add `prepare_worktree`, `implement`, `validate`, and one bounded `repair` route using fake tools in tests.
5. Add idempotent branch push, draft PR handoff, and structured Jira comments.
6. Add incident pause policy, safe checkpoints, integration tests, and failure/restart tests.

Only enable real repository writes after dry runs prove the policy, audit, duplicate-event, and pause behavior.
