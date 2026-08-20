# Workspace Rules & Architectural Constraints

1. **User Ownership**:
   - The user is the captain of the ship and lead architect.
   - The agent must NEVER take architectural or design decisions autonomously.
   - Any architectural changes, design decisions, or pipeline modifications MUST be presented to the user with clear options, validated, questioned, and explicitly approved before implementation.

2. **No Hardcoding & No Fake Fallbacks**:
   - Zero hardcoding, fake templates, or mock fallback string generation for incoming requests or execution flows.
   - The OpenHands core SDK Coder Agent (`openhands.sdk`) must be used as-is for the sandbox coding agent.
   - In case of failure (e.g. LLM error, missing credential, tool execution failure), the agent must gracefully shut down, dispatch an error email notification to the user, record the failure audit, and exit cleanly.
