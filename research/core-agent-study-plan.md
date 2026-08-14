# Core Coding Agent Study Plan

## Objective

Use the OpenHands SDK as the backbone for the main coding loop, while keeping this project’s existing task orchestration for Jira intake, queueing, policy, memory persistence, and PR handoff. The goal is to avoid re-implementing the agent runtime and tool stack from scratch when a mature SDK already provides the correct foundations.

## Core principle

- Use the SDK for the core execution layer:
  - Agent definition
  - LLM orchestration
  - conversation lifecycle
  - tool registration and execution
  - local workspace execution
  - file editing and terminal operations
- Keep this repo’s own logic for:
  - Jira ticket intake and normalization
  - deterministic scheduling and policy checks
  - SQLite-backed memory / job state
  - incident safety gates
  - final PR push / handoff workflow

## What to keep from the reference SDK

Required study scope:

- /Reference-for-ai/software-agent-sdk/README.md
- /Reference-for-ai/software-agent-sdk/openhands-sdk/openhands/sdk/
- /Reference-for-ai/software-agent-sdk/openhands-tools/openhands/tools/
- /Reference-for-ai/software-agent-sdk/examples/01_standalone_sdk/

Relevant SDK modules to prioritize:

- openhands.sdk
  - Agent
  - Conversation
  - LLM
  - LocalWorkspace
  - Tool registry
  - AgentContext
- tool layer
  - FileEditorTool
  - TerminalTool
  - TaskTrackerTool
  - Glob / grep helpers
  - planning file editor if required for structured work

## What to discard from the reference SDK

Remove anything that does not help with the coding agent itself:

- remote agent server setup for this phase
- example workflows unrelated to the coding loop
- large plugin / marketplace / cloud code not directly tied to local coding execution
- heavy docs and generated artifacts
- broad test and server scaffolding not needed for a minimal study baseline

## Proposed architecture for this project

1. Intake + policy layer
   - Existing Jira webhook and task routing logic stays.
   - Human-controlled Jira lifecycle remains authoritative.

2. Shared memory + task state
   - Continue to use the repo’s SQLite store.
   - Persist job state, checkpoints, audit logs, and pause conditions.

3. Core coding agent
   - Build the execution loop using the OpenHands SDK runtime.
   - Use Agent + Conversation + tool registration as the main coding engine.
   - Use SDK tool abstractions rather than custom agent orchestration primitives.

4. Repository work and validation
   - Use file editor and terminal tools for patching and verification.
   - Keep bounded scope checks, repair loops, and validation gates in our local project code.

5. Draft PR and user notification
   - Keep the existing repo logic for final PR creation and messaging.
   - The SDK handles the actual coding work, not the final productization layer.

## Recommended implementation strategy

- Treat the SDK as the execution backbone, not the whole product.
- Keep our project’s existing design where business logic or safety policy matters.
- Only add custom wrappers around SDK components when we need:
  - Jira integration
  - repo-specific policy checks
  - durable job state
  - branch / PR control
  - incident pause logic

## Minimal MVP fit

The best fit is:

- OpenHands SDK = coding engine + tool execution + conversation loop
- soft.Engineer repo = policy, queueing, memory, review, PR handoff, safety guardrails

This keeps the project focused on the real product problem without rebuilding a generic agent runtime.

## Cleanup target

Only keep the minimal SDK reference material needed for rapid study and integration. All extra directories and examples unrelated to the local coding agent should be removed.
