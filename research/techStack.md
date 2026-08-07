# Tech Stack & Architecture: Jira to PR Workflow

## Overview

This document compares frameworks, tools, and architecture patterns for building a production-grade agentic workflow that converts Jira tickets to pull requests.

---

## 1. Agent & LLM Frameworks

### Option A: LangChain
**Pros:**
- Rich ecosystem of chains, tools, and memory abstractions
- Strong integrations with Jira, GitHub, and Git CLI
- Agent orchestration via ReAct pattern
- Easy to prototype with multiple LLMs

**Cons:**
- Abstractions can hide production control flow
- Token counting and cost management not built-in
- Heavy dependency tree; slower startup
- Chain composition becomes hard to debug at scale

**Best for:** Quick prototype, multiple LLM experimentation

---

### Option B: LlamaIndex (formerly GPT-Index)
**Pros:**
- Excellent document/vector retrieval integration
- Built-in evaluation framework for retrieval quality
- Better for multi-document reasoning and grounding
- Lighter footprint than LangChain

**Cons:**
- Smaller tool ecosystem
- Less mature agent loop than LangChain
- Fewer integrations out of the box

**Best for:** Code retrieval and context grounding phase

---

### Option C: Anthropic SDK + Claude (Direct Agents API)
**Pros:**
- Minimal overhead; direct API calls
- Full control over prompt and tool execution loop
- Better cost transparency
- Extended thinking for complex reasoning

**Cons:**
- No magic; must build orchestration and memory from scratch
- Requires manual tool registry and execution
- Steeper learning curve

**Best for:** Production systems where control and cost matter

---

### Option D: OpenAI Assistants API / GPT-4 with Code Interpreter
**Pros:**
- Built-in code execution environment
- Persistent thread-based memory
- Good for interactive, iterative workflows

**Cons:**
- Vendor lock-in
- Higher latency and cost for large codebases
- Limited cross-function composition
- Interpreter sandbox can be restrictive

**Best for:** Interactive code generation, not batch automation

---

### Option E: Ollama + Local LLMs
**Pros:**
- No external API dependency
- Full privacy and control
- Offline capability
- Cost: low after model download

**Cons:**
- Accuracy often falls short of Claude/GPT-4 for complex reasoning
- Requires significant compute (GPU or high-end CPU)
- Inference speed slower than cloud API
- No extended reasoning capability

**Best for:** Cost-sensitive environments, privacy-critical deployments

---

**Recommendation for soft.Engineer:** Start with a **direct model SDK behind a small provider adapter**. Reasons:
- Direct control over the tool loop fits production guardrails.
- Structured output and token accounting can be enforced by the workflow.
- The scheduler, incident policy, state transitions, and permissions must be ordinary deterministic code, not model behavior.
- A provider adapter preserves the option to change models without rewriting workflow state.

---

## 2. Code Repository & Context Retrieval

### Option A: AST-based Parsing (Python ast, TypeScript ts compiler)
**Pros:**
- Precise understanding of code structure
- Low false positives; accurate dependency tracking
- Can extract symbols, types, and imports reliably
- Enables strong static analysis

**Cons:**
- Must implement parser for each language
- Parsing failures = silent information loss
- Slower for large codebases

**Best for:** Statically-typed languages with mature parsers (Python, TypeScript, Go)

---

### Option B: Tree-sitter (Multi-language parser)
**Pros:**
- Single tool for 100+ languages
- Incremental parsing; handles syntax errors gracefully
- Fast; can re-parse on file change
- Good for highlighting and symbol location

**Cons:**
- Less precise than language-native AST
- Requires tree queries to extract semantic info
- Not a substitute for type checkers

**Best for:** Multi-language codebases, symbol extraction, rapid indexing

---

### Option C: Vector embeddings + semantic search (Weaviate, Pinecone, Milvus)
**Pros:**
- Fuzzy matching on intent and concept
- Can find related code even if not directly referenced
- Lightweight; scales to huge codebases
- Works across languages

**Cons:**
- Can hallucinate related code that is not relevant
- Accuracy depends on quality of embeddings
- Stale if repo changes between update cycles
- Requires embedding model and vector DB overhead

**Best for:** Discovering related patterns and design inspiration

---

### Option D: Git blame + recent diff mining
**Pros:**
- Ground truth about what changed and why
- Identifies expert owners for code review
- Reveals active vs dormant code paths
- No parsing required

**Cons:**
- Does not tell you the structure of current code
- Requires Git history; new repos have no signal
- Scalability depends on repo size and history length

**Best for:** Risk assessment, owner identification, context freshness

---

**Recommendation:** Combine **Tree-sitter (Option B)** for structure + **Git blame + diffs (Option D)** for context freshness + **optional semantic search (Option C)** for pattern discovery. This trades simplicity for accuracy and production safety.

---

## 3. Test & Validation framework

### Option A: Standard test runners (pytest, jest, vitest)
**Pros:**
- Native to the language
- High integration with CI/CD
- Mature ecosystem
- Good for unit and integration tests

**Cons:**
- Requires test infrastructure already in place
- Flaky tests are hard to detect automatically
- No built-in validation that test added by agent is sound

**Best for:** Codebases with strong test coverage

---

### Option B: mutation testing (stryker, mutmut)
**Pros:**
- Validates that tests actually catch failures
- Ensures test quality, not just coverage
- Catches hallucinated implementations

**Cons:**
- Slow; runs hundreds of code variants
- High false positive rate if baseline is weak
- Not suitable for runtime performance testing

**Best for:** Verifying agent-generated tests are not hollow

---

### Option C: property-based testing (hypothesis, Quickcheck)
**Pros:**
- Generates many edge cases automatically
- Catches subtle logic errors
- Specification-driven

**Cons:**
- Requires explicit property definition
- Hard to use when logic is underspecified
- Agent may not know properties to define

**Best for:** Math-heavy, deterministic algorithms

---

### Option D: shadowing & canary validation
**Pros:**
- Run new code in shadow mode in production
- Catch real-world failures before merge
- Validates behavior against live traffic

**Cons:**
- Requires instrumentation
- High complexity to implement safely
- Not suitable for all change types (destructive ops, writes)

**Best for:** High-stakes changes, live traffic patterns

---

**Recommendation:** Enforce **existing test coverage (Option A)** + **fallback explicit test-gap flag** if coverage is weak. Add **mutation testing (Option B)** as optional gate for critical modules.

---

## 4. Git & PR Management

### Option A: GitHub REST API + PyGithub
**Pros:**
- Simple, mature API
- Works offline with local commit history
- No external service dependency

**Cons:**
- Rate limits (often exceeded in batch workflows)
- REST verbose for complex workflows
- No direct webhook into branch protection

**Best for:** Simple PR create/read/update operations

---

### Option B: GitHub GraphQL API
**Pros:**
- Single query for complex data
- Lower latency; fewer round-trips
- Better for complex workflows (reviews, status checks)

**Cons:**
- Learning curve
- Rate limits still apply
- Requires query tuning

**Best for:** Multi-step workflows with dependencies

---

### Option C: GitOps / Pull Request Operators (flux, argocd)
**Pros:**
- Declarative workflow
- Git is the source of truth
- Audit trail built-in

**Cons:**
- Overkill for single-repo workflows
- Additional infrastructure to manage
- Latency between commit and effect

**Best for:** Multi-repo, multi-cluster deployments

---

### Option D: GitLab CI / GitHub Actions for orchestration
**Pros:**
- Native CI/CD integration
- Workflows as code
- Easy to add approval gates

**Cons:**
- Vendor lock-in
- Limited to vendor's execution environment
- Harder to run locally for testing

**Best for:** Integrating with existing CI/CD pipeline

---

**Recommendation:** Use a least-privilege GitHub API client for branch and draft-PR operations. Jira ticket retrieval belongs to the Jira API, not GitHub. Keep Jira status transitions out of the service credentials entirely. Use GitHub Actions for repository-native checks, but do not use CI as the source of workflow state.

---

## 5. Orchestration & Workflow Engine

### Option A: Simple state machine (custom Python/TypeScript)
**Pros:**
- Minimal dependencies
- Full debugging visibility
- Easy to test step by step

**Cons:**
- Must handle retries, timeouts, error recovery manually
- No built-in persistence
- Does not scale to complex workflows

**Best for:** Simple V1 implementation, single-stage workflows

---

### Option B: Temporal / Durable Task Scheduling
**Pros:**
- Handles timeouts, retries, distributed execution
- Workflow as code with durable history
- Built-in observability

**Cons:**
- Additional infrastructure (Temporal server)
- Learning curve; verbose workflow definitions
- Higher operational complexity

**Best for:** Long-running, multi-step async workflows

---

### Option C: Airflow
**Pros:**
- Mature; widely used in data pipelines
- Rich UI for monitoring and debugging
- Strong integration with Jira, GitHub, K8s

**Cons:**
- Overkill for simple workflows
- Deployment complexity
- Python-heavy ecosystem

**Best for:** Complex, scheduled, large-scale automation

---

### Option D: Prefect / Dagster
**Pros:**
- Simpler than Airflow
- Better error handling and recovery
- Modern Python-native APIs

**Cons:**
- Smaller ecosystem than Airflow
- Still requires infrastructure
- Learning curve

**Best for:** Modern Python workflows with complex dependencies

---

**Recommendation:** Start with an explicit state machine plus **SQLite-backed durable job state** for V1. A stateless synchronous loop is not sufficient when webhooks are retried, tasks are automatically selected, or work must pause for an incident. Move to Temporal when multiple workers, long-running jobs, or higher throughput justify the operational cost.

---

## 6. Production Observability & Logging

### Option A: Structured logging (structured-log, pythonjsonlogger)
**Pros:**
- Machine-readable; easy to query and alert
- Works well with log aggregation (ELK, Datadog)
- Zero external dependency

**Cons:**
- Requires discipline in log field standardization
- Human review of logs is harder without good tooling

**Best for:** Production systems with centralized logging

---

### Option B: Distributed tracing (OpenTelemetry, Jaeger)
**Pros:**
- Full visibility into multi-step workflows
- Easy to spot bottlenecks and failures
- Standard protocol; not vendor-locked

**Cons:**
- Sampling overhead
- Requires tracing backend
- Initial setup complexity

**Best for:** Complex multi-service workflows

---

### Option C: Metrics + dashboards (Prometheus, Grafana)
**Pros:**
- Real-time visibility
- Good for SLO tracking
- Alerting built-in

**Cons:**
- Does not capture individual request context
- Requires metric definition upfront
- Disk overhead for storage

**Best for:** System health, throughput, error rates

---

**Recommendation:** Implement **structured logging (Option A)** immediately. Add **OpenTelemetry tracing (Option B)** once workflows become complex. Use **Prometheus metrics (Option C)** for dashboards and SLO tracking.

---

## 7. High-Level Architecture

### Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation & Handoff Layer                                │
│  - PR review template generator                             │
│  - Summary report to engineer                               │
│  - Approval/rejection feedback handler                      │
└─────────────────────────────────────────────────────────────┘
                           ↑↓
┌─────────────────────────────────────────────────────────────┐
│ Validation & Verification Pipeline                          │
│  - Test runner wrapper (pytest, jest, etc.)                 │
│  - Linting and static analysis                              │
│  - Build check (if applicable)                              │
│  - Test quality check (mutation, coverage)                  │
└─────────────────────────────────────────────────────────────┘
                           ↑↓
┌─────────────────────────────────────────────────────────────┐
│ Execution Engine (LLM + Tool Loop)                          │
│  - Agent orchestrator (Claude SDK or LangChain)             │
│  - Tool registry (edit file, run test, query repo)          │
│  - Execution sandbox / isolation                            │
│  - Bounded execution (max files, max iterations)            │
└─────────────────────────────────────────────────────────────┘
                           ↑↓
┌─────────────────────────────────────────────────────────────┐
│ Planning & Analysis Layer                                   │
│  - Ticket normalization                                     │
│  - Context retrieval (AST + git blame)                      │
│  - Deterministic eligibility, priority, and incident policy │
│  - Risk assessment & scope validation                       │
│  - Implementation plan generation                           │
│  - Human-controlled Jira status approval gate               │
└─────────────────────────────────────────────────────────────┘
                           ↑↓
┌─────────────────────────────────────────────────────────────┐
│ Intake Layer                                                 │
│  - Jira ticket fetch & parse                                │
│  - Signed webhook receipt and event deduplication           │
│  - Acceptance criteria extraction                           │
│  - Linked docs integration                                  │
│  - Pre-qualification checks                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Technology Stack Recommendations

### Recommended Stack for V1

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Rich ecosystem, easy to integrate with Jira/GitHub APIs, good for scripting |
| **LLM/Agent** | Model provider adapter + direct SDK | Keeps model execution separate from deterministic policy and state |
| **Code Context** | Tree-sitter + Git CLI | Multi-language, accurate structure, fresh history |
| **Tests** | pytest (Python) + Jest (Node) | Native, widely used |
| **Git/PR** | PyGithub (GitHub API v3) or GithubPython library | Simple, mature, sufficient for V1 |
| **Orchestration** | State machine + SQLite job store | Minimal deploy while preserving idempotency, pause/resume, and audit state |
| **Logging** | structlog + stdout (later: ELK or Datadog) | Structured, human-readable initially |
| **Config** | Versioned policy file + environment variables | Explicit priority, incident, repository, and command rules |
| **Deployment** | Containerized webhook endpoint + single worker | Portable, reproducible, and sufficient for low-volume durable processing |

---

### Recommended Stack for V2 (Scale)

| Layer | Technology | Addition/Change |
|-------|-----------|-----------------|
| **Orchestration** | Temporal or equivalent | For multi-worker, long-running, resumable workflows |
| **Observability** | OpenTelemetry + Jaeger + Prometheus | Full visibility |
| **Testing** | stryker (mutation testing) | Validate test quality |
| **Code Context** | Semantic search (Weaviate) + AST | Faster, fuzzier retrieval |
| **PR Operations** | GitHub GraphQL API | Lower latency for complex workflows |

---

## 9. Architecture Trade-offs

### Monolithic Agent vs. Microservices

**Monolithic (V1):**
- Single process, single responsibility: take ticket → produce PR
- Simpler to test and debug
- Single point of failure, but easy to restart
- Suitable for batch processing

**Microservices (V2+):**
- Separate planner, executor, validator services
- Better scalability and independent failures
- Harder to test end-to-end
- Requires orchestration and async messaging

**Recommendation:** Start monolithic. Split only if volumes or complexity demand it.

---

### Synchronous vs. Asynchronous

**Single-worker asynchronous (V1):**
- A worker processes a durable queue while Jira remains human-controlled
- Safe restart, pause/resume, and event deduplication are possible
- Does not require a distributed queue at low volume

**Asynchronous (V2+):**
- Workflow runs in background; engineer gets webhook callback
- Scalable; can queue many tasks
- Requires persistent task state and notification system

**Recommendation:** Start with one durable worker and SQLite. Add a distributed queue only when concurrency or throughput makes the single-worker lease model insufficient.

---

### Self-Contained Repo vs. External Service

**Self-contained (V1):**
- Agent talks directly to GitHub/Jira APIs
- Works locally; no external infrastructure
- Scaling is limited, everything on one machine

**External Service (V2+):**
- Dedicated workflow service, exposed via REST/gRPC API
- Can scale horizontally
- Adds operational overhead (service discovery, deployment)

**Recommendation:** Start self-contained. Expose as a service once you need scale or parallel execution.

---

## 10. Deployment Model

### Local Development
- Agent runs in Docker locally
- Uses GitHub/Jira API credentials from `.env`
- Tests against real branch but in sandbox mode
- Manual trigger via CLI: `python agent.py --ticket JIRA-123 --dry-run`

### Staging
- Same container image
- Real Jira and test GitHub repo
- Branch: `agent/staging/*`
- Longer timeout for debugging
- All actions logged to Datadog

### Production
- Containerized agent in Kubernetes or VMs
- Triggered by a signed Jira webhook or scheduled reconciliation when a human has moved a ticket to `Agent Ready`
- Real Jira and production GitHub
- Branch: `agent/TICKET-ID`
- Strict logging and audit trail
- All PRs tagged with `automated` label for filtering
- Jira credentials can read tickets and post comments only; they cannot change status, priority, assignee, or resolution
- An incident policy pauses lower-priority mutation work before edits, commits, pushes, or PR creation

---

## Summary

```
Tech Stack Category    | V1 Choice           | V2 Enhancement
-----------------------|---------------------|-------------------
Agent Framework        | Provider adapter    | Add local LLM fallback
Code Context           | Tree-sitter + Git   | Add semantic retrieval
Orchestration          | State machine + SQLite | Temporal
Testing                | Native test runners | Add mutation testing
Git/PR                 | PyGithub REST API   | GitHub GraphQL
Observability          | structlog + stdout  | OpenTelemetry + Jaeger
Deployment             | Docker + systemd    | Kubernetes + Helm
```

This stack prioritizes **simplicity**, **observability**, and **safety** for the initial release, with clear upgrade paths for scale and complexity.
