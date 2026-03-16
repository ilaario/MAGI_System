import json

from ..llm_client import LLMClient
from ..models.decision_result import DecisionResult


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = LLMClient(model=model)

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError(
                f"{self.name} returned no valid JSON object.\nRaw response:\n{text}"
            )

        return text[start : end + 1]

    def evaluate(self, scenario: str, retries: int = 3) -> DecisionResult:
        last_error = None

        for _ in range(retries):
            try:
                raw = self.client.ask(
                    system_prompt=self.system_prompt,
                    user_prompt=scenario,
                )
                json_text = self._extract_json(raw)
                data = json.loads(json_text)
                return DecisionResult.model_validate(data)
            except Exception as e:
                last_error = e

        raise ValueError(f"{self.name} failed after {retries} attempts: {last_error}")
