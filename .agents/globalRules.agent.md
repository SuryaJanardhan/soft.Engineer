# Global Agent Authority & Decision Rules

1. **User Authority**:
   - The user is the captain of the ship and lead architect.
   - NEVER make architectural or major design decisions on your own.
   - You must NEVER assume authority to change architecture, pipeline design, or core components without presenting clear options, validating, questioning, and obtaining explicit user approval.

2. **No Hardcoding & No Fake Fallbacks**:
   - Absolutely zero fake templates, static string stubs, or mock fallbacks for incoming requests or execution paths.
   - The OpenHands core SDK Coder Agent (`openhands.sdk`) must be used as-is for the sandbox coding agent.
   - If an error occurs (e.g. LLM failure, credential issue, tool execution error), the system must perform a **graceful shutdown**, send a clean error email notification to the user, log the failure audit, and exit cleanly. No fake fallbacks.
