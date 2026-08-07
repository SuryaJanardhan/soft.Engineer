# Jira to PR Agentic Workflow

## Problem Statement

Build a production-grade agentic workflow that selects the next eligible Jira task by policy and produces a reviewable pull request for medium- to low-priority engineering work.

The workflow should mimic the practical parts of a software engineer's process: understand the ticket, gather relevant code and context, propose a plan, make the code changes, run checks, prepare a PR, and hand off to a human reviewer with enough evidence to approve or reject quickly.

## Why This Matters

Teams spend a large amount of time on repetitive but still important work: small bug fixes, narrow refactors, dependency updates, config changes, and straightforward feature follow-ups. These tasks are not usually hard enough to justify a full manual cycle, but they are still risky enough that bad automation can create real production issues.

The goal is not to replace engineers. The goal is to reduce the time spent on low-leverage execution while keeping quality, traceability, and rollback safety at a level that is acceptable in production.

## Scope

- Input: Jira ticket, acceptance criteria, linked docs, and codebase context.
- Output: code changes, tests, validation evidence, and a PR draft.
- Target work: medium- to low-complexity changes with clear boundaries.
- The scheduler may automatically select the next eligible task, but it does not decide business priority or urgency on its own.
- Jira workflow status transitions are performed only by humans. The system may read tickets and add comments, labels, evidence, and PR links, but it must never transition a Jira status.
- Human approval is required at plan approval, PR approval, and merge time.

## Operating Model

Jira is the human accountability record. The workflow engine has separate internal execution states, such as `queued`, `analyzing`, `awaiting_plan_approval`, `executing`, `validating`, `paused`, and `failed`. These states explain what the system is doing; they must not be written back as Jira transitions.

A human makes a ticket eligible by moving it to `Agent Ready`. The scheduler selects from eligible tickets using an explicit policy: priority, age, team ownership, required skills, risk class, and execution capacity. It must reject or defer work that is ambiguous, security-sensitive, blocked, or outside configured repository boundaries.

Active incidents override normal task selection. For P0 incidents, the system pauses before any unsafe mutation and provides context only. For P1 incidents, it may prepare an investigation or impact report but needs explicit approval before creating a draft PR. P2 and lower work follows the normal approval gates.

## Not The Goal

- Fully autonomous production changes without review.
- Automatic Jira status transitions or automatic task closure.
- Large architecture changes with unclear blast radius.
- Autonomous mitigation or deployment during an active production incident.
- Tasks that require deep product judgment or ambiguous requirements.

## Success Criteria

- The agent consistently produces correct, minimal diffs.
- The generated PRs are reviewable without major cleanup.
- Tests and validation cover the changed behavior.
- Failures are explainable, observable, and easy to roll back.
- The workflow never creates duplicate jobs from repeated events and can safely resume paused work.
- An active high-severity incident pauses lower-priority mutation work without losing the task's audit trail.
- Human reviewers spend less time fixing the agent's mistakes than doing the task manually.
