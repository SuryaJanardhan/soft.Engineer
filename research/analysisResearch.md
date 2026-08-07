# Research Notes: Jira to PR Workflow

## Core Production Problem

The real issue is not generating code. The hard part is reliably turning an underspecified Jira ticket into a safe, reviewable change in a living codebase.

In production, the workflow fails when any of these break:

- The ticket is incomplete, contradictory, or outdated.
- The agent pulls the wrong context from the repository.
- The change touches shared code with hidden blast radius.
- Tests do not exist, are flaky, or do not cover the failure mode.
- The PR looks plausible but is semantically wrong.
- Reviewers cannot tell what was changed, why it was changed, or how it was verified.

That means the system has to be designed around failure containment, not just code generation.

## Real Production Issues

### 1. Ambiguous tickets

Jira tickets often describe symptoms, not implementation constraints. A ticket may say "fix login issue" while the root cause is anything from frontend state to backend auth propagation to an expired feature flag.

Production impact:

- The agent guesses the wrong root cause.
- The change solves a surface symptom but not the defect.
- Review time increases because the implementation does not match the actual problem.

### 2. Stale repository context

The codebase changes faster than any static summary. A workflow that relies on old assumptions will pick outdated patterns, removed helpers, or obsolete APIs.

Production impact:

- Broken builds because the agent used deprecated interfaces.
- Incorrect imports or config references.
- Poor fit with current architecture conventions.

### 3. Hidden dependency and blast-radius risk

Small changes in shared code can affect multiple services, jobs, or customer paths. The agent may treat a local fix as isolated when it is not.

Production impact:

- Regressions in unrelated flows.
- Latent failures that appear only under production traffic.
- Hotfixes that create follow-on incident work.

### 4. Weak or missing tests

For many medium- or low-priority tasks, the real production risk is the lack of a strong executable oracle. If the change cannot be validated, the workflow becomes a confidence exercise instead of an engineering process.

Production impact:

- False confidence from green but low-signal tests.
- Flaky behavior that passes in CI and fails in prod.
- Reviewers cannot trust the patch.

### 5. Hallucinated implementation details

The agent can invent helper functions, non-existent flags, or behaviors that sound consistent but do not exist in the codebase.

Production impact:

- Time wasted on cleanup.
- Broken PRs that require manual repair.
- Lower trust in the system over time.

### 6. Poor handoff quality

Even if the code is correct, the workflow can still fail if the PR does not communicate intent, scope, tradeoffs, and validation.

Production impact:

- Reviewers spend extra time reconstructing context.
- Approval stalls because the diff lacks evidence.
- Merge decisions become inconsistent.

### 7. Unsafe autonomy

If the workflow edits too much too early, the cost of mistakes compounds.

Production impact:

- Large diffs that are hard to inspect.
- Harder rollbacks.
- Higher chance of inserting subtle regressions.

### 8. Priority inversion and incident interference

Jira priority is not enough to decide what the system should work on. Values can be stale, manually inconsistent, or disconnected from an active incident. A background agent that keeps editing P3 work while a P0 incident is active competes for compute, reviewer attention, and repository stability when the team needs focus.

Production impact:

- A low-value change lands during an incident and complicates diagnosis or rollback.
- The system chooses a task that is nominally high priority but blocked, risky, or owned by another team.
- Duplicate webhooks start duplicate runs against the same ticket.

### 9. Misleading workflow status

If an agent changes a ticket to `In Progress`, `Done`, or `Blocked`, Jira no longer clearly identifies the accountable human decision. This is especially damaging during incidents and audits, where a status change is an operational claim, not a progress animation.

Production impact:

- Tickets appear complete even though a reviewer rejected the change.
- Teams cannot distinguish agent execution state from a human-approved lifecycle decision.
- Incident timelines become unreliable.

## Root Cause Categories

The failures above usually come from one of five categories:

- Requirement ambiguity.
- Context retrieval failure.
- Change-scope misjudgment.
- Verification weakness.
- Review packaging failure.

That means the solution should not be just "better prompts." It needs explicit control points.

## Proposed Solution Shape

### A. Intake and normalization layer

Normalize the Jira ticket into a structured task object:

- Problem statement.
- Acceptance criteria.
- Files or systems likely involved.
- Risk level.
- Assumptions and open questions.

This reduces the chance that the agent acts on raw, noisy ticket text.

### B. Context retrieval layer

Use repository search, ownership signals, recent diffs, and linked docs to gather only relevant context.

The system should prefer live repository evidence over summary memory whenever possible.

### C. Plan-before-edit gate

Require a short implementation plan before any code is modified.

The plan should include:

- Files likely to change.
- Verification steps.
- Expected risk areas.
- Fallback or rollback path.

### D. Bounded execution

Limit the agent to small, incremental edits.

This is safer than letting the agent do a large free-form rewrite because it keeps diffs auditable and makes it easier to stop when reality diverges from the plan.

### E. Verification pipeline

Run checks in layers:

- Targeted unit tests.
- Relevant integration tests.
- Static checks and linting.
- Build or typecheck when available.

If the task has no strong test coverage, the workflow should flag that gap explicitly instead of pretending the result is validated.

### F. Review packaging

Every PR should include:

- What changed.
- Why it changed.
- What was validated.
- What risks remain.
- What should be watched after merge.

This is what makes the output reviewable in production.

### G. Policy-based scheduling and separate state

Treat task selection as a deterministic policy, not an LLM judgement. The scheduler considers only tickets manually moved to `Agent Ready`, then applies configured priority, ownership, risk, age, repository allowlists, and available capacity. It must persist an idempotency key per Jira event and a lease per active task.

Maintain two separate state models:

| State owner | Purpose | Examples |
|---|---|---|
| Human in Jira | Accountability and lifecycle | `Backlog`, `Agent Ready`, `Plan Review`, `PR Review`, `Done`, `Blocked` |
| Workflow engine | Durable execution progress | `queued`, `analyzing`, `awaiting_plan_approval`, `executing`, `validating`, `paused`, `failed` |

The agent has no Jira transition permission. It may add a structured comment with its plan, risk assessment, validation result, or PR link. A human performs every Jira status transition.

### H. Incident policy

An active incident changes scheduling behavior but must not turn the agent into an autonomous incident responder.

| Severity | System behavior |
|---|---|
| P0 | Stop queued work and pause running jobs before an edit, push, or other mutation. Gather read-only context and notify the incident owner. |
| P1 | Pause normal execution. Prepare an impact report or proposed plan. Require explicit human approval before a draft PR. |
| P2 | Permit normal workflow only after the normal plan gate and only when no P0/P1 policy blocks it. |
| P3/P4 | Eligible for automatic selection when capacity is available. |

Pause must be cooperative and checkpointed. Do not terminate a process in the middle of a file write, commit, or push. A human decides whether a paused task is resumed or cancelled.

## Comparison Matrix

### Single agent vs multi-agent

- Single agent: simpler, cheaper, easier to debug, but more likely to miss context and collapse planning, coding, and verification into one brittle loop.
- Multi-agent: better at separating responsibilities like planning, implementation, and validation, but harder to coordinate and more expensive to operate.

Recommendation: use a small number of specialized stages, not a large swarm.

### Fully autonomous vs human-gated

- Fully autonomous: faster, but unsafe for shared production code because the failure cost is too high.
- Human-gated: slower, but it keeps accountability and catches ambiguity before merge.

Recommendation: human approval at plan and PR stages for all non-trivial tasks.

### Free-form editing vs bounded patching

- Free-form editing: flexible, but error-prone and hard to reason about.
- Bounded patching: more controlled, easier to inspect, and safer for production.

Recommendation: favor bounded patching for the first release.

### Summary memory vs live retrieval

- Summary memory: faster, but stale and can drift from the codebase.
- Live retrieval: slower, but accurate and grounded in current repository state.

Recommendation: use live retrieval as the source of truth and memory only for durable workflow preferences.

## Production Guardrails

- Reject tasks with unclear acceptance criteria.
- Stop when the codebase contradicts the ticket.
- Cap the number of files changed for low-risk tasks.
- Require tests or an explicit test-gap note.
- Log every action the agent takes.
- Keep rollback instructions attached to the PR.
- Escalate to a human when confidence drops below a threshold.
- Use durable storage for event receipts, task leases, checkpoints, approvals, and audit records; a JSON file is not sufficient once events can be retried or tasks can overlap.
- Give the agent least-privilege credentials: ticket read and comment access, constrained branch creation, and draft PR creation. No Jira transitions, merges, deployments, or broad secret access.
- Enforce repository and path allowlists, command allowlists, maximum cost, time, and file-change budgets.

## What This Solves

This approach turns the workflow from "generate code and hope" into "execute within a controlled production process."

That matters because the main product here is not the code patch. The main product is a predictable, reviewable delivery pipeline that does not create new operational risk while trying to reduce engineering effort.
