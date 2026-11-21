"""Anthropic Claude LLM provider."""

import json

import anthropic


class AnthropicProvider:
    """Anthropic Claude extractor."""

    def __init__(self, api_key: str, model: str = "claude-opus-5-5"):
        """Initialize Anthropic provider."""
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def complete_json(
        self, system: str, user_prompt: str, json_schema: dict
    ) -> dict:
        """Call Claude with structured output (JSON mode)."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Parse JSON from response
            text = response.content[0].text
            # Try to find JSON in the response
            json_start = text.find("{")
            json_end = text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)

            raise ValueError("No JSON found in response")

        except anthropic.APIError as e:
            raise ValueError(f"Anthropic API error: {e}") from e
