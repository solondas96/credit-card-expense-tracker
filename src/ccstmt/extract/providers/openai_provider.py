"""OpenAI GPT LLM provider."""

import json

import openai


class OpenAIProvider:
    """OpenAI GPT extractor."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize OpenAI provider."""
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

    def complete_json(
        self, system: str, user_prompt: str, json_schema: dict
    ) -> dict:
        """Call GPT with JSON mode."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            text = response.choices[0].message.content
            return json.loads(text)

        except openai.APIError as e:
            raise ValueError(f"OpenAI API error: {e}") from e
