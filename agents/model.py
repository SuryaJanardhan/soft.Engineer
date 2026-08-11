import json
import logging
from typing import Any, Protocol

from agents.config import GroqSettings

LOGGER = logging.getLogger(__name__)


class PlanningModel(Protocol):
    def make_plan(self, ticket: dict[str, str], context: dict[str, object]) -> dict[str, object]: ...

    def repair_plan(self, plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]: ...


class DeterministicPlanningModel:
    """Local stand-in for a structured-output LLM provider."""

    def make_plan(self, ticket: dict[str, str], context: dict[str, object]) -> dict[str, object]:
        files = list(context["candidate_files"])
        return {
            "summary": f"Implement: {ticket['summary']}",
            "files": files,
            "validation_commands": list(context["test_commands"]),
            "risks": ["Demo adapter does not inspect a live repository"],
            "rollback": "Revert the agent branch before merge",
        }

    def repair_plan(self, plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]:
        repaired_plan = dict(plan)
        repaired_plan["repair_note"] = f"Repair requested after: {validation['summary']}"
        return repaired_plan


class GroqPlanningModel:
    """Groq LLM planning provider with dual API key rotation."""

    def __init__(self, settings: GroqSettings, fallback_model: PlanningModel | None = None) -> None:
        self.settings = settings
        self.fallback_model = fallback_model or DeterministicPlanningModel()
        self.current_key_index = 0

    def make_plan(self, ticket: dict[str, str], context: dict[str, object]) -> dict[str, object]:
        if not self.settings.api_keys:
            LOGGER.info("No Groq API keys configured. Using deterministic planning model fallback.")
            return self.fallback_model.make_plan(ticket, context)

        prompt = (
            f"You are an expert autonomous software engineering agent.\n"
            f"Generate a structured change plan JSON for the following ticket:\n"
            f"Ticket ID: {ticket.get('ticket_id')}\n"
            f"Summary: {ticket.get('summary')}\n"
            f"Description: {ticket.get('description')}\n"
            f"Candidate Files: {context.get('candidate_files')}\n"
            f"Test Commands: {context.get('test_commands')}\n\n"
            f"Return JSON strictly with schema:\n"
            f'{{\n  "summary": "Short task plan description",\n'
            f'  "files": ["list", "of", "files"],\n'
            f'  "validation_commands": ["list", "of", "test_commands"],\n'
            f'  "risks": ["risk items"],\n'
            f'  "rollback": "rollback instruction"\n}}\n'
        )

        response_json = self._call_groq_with_key_rotation(prompt)
        if response_json and "files" in response_json:
            return response_json

        LOGGER.warning("Groq response invalid or failed. Falling back to deterministic model.")
        return self.fallback_model.make_plan(ticket, context)

    def repair_plan(self, plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]:
        if not self.settings.api_keys:
            return self.fallback_model.repair_plan(plan, validation)

        prompt = (
            f"Repair the failed execution plan.\n"
            f"Original Plan: {json.dumps(plan)}\n"
            f"Validation Results: {json.dumps(validation)}\n\n"
            f"Return updated plan JSON matching original schema.\n"
        )

        response_json = self._call_groq_with_key_rotation(prompt)
        if response_json and "files" in response_json:
            return response_json

        return self.fallback_model.repair_plan(plan, validation)

    def _call_groq_with_key_rotation(self, prompt: str) -> dict[str, Any] | None:
        total_keys = len(self.settings.api_keys)
        attempts = 0

        while attempts < total_keys:
            key_index = (self.current_key_index + attempts) % total_keys
            api_key = self.settings.api_keys[key_index]

            try:
                from groq import Groq

                client = Groq(api_key=api_key)
                LOGGER.info("Invoking Groq API key index=%d model=%s", key_index, self.settings.model_name)
                completion = client.chat.completions.create(
                    model=self.settings.model_name,
                    messages=[
                        {"role": "system", "content": "You output strict valid JSON objects only."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )

                content = completion.choices[0].message.content or "{}"
                parsed = json.loads(content)
                self.current_key_index = key_index
                return parsed

            except Exception as error:
                LOGGER.warning(
                    "Groq API call failed with key index=%d error=%s. Rotating to next key.",
                    key_index,
                    error,
                )
                attempts += 1

        LOGGER.error("All %d Groq API keys exhausted or failed.", total_keys)
        return None
