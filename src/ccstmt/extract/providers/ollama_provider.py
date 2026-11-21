"""Ollama local LLM provider."""

import json

import httpx


class OllamaProvider:
    """Ollama local model extractor."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """Initialize Ollama provider."""
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete_json(
        self, system: str, user_prompt: str, json_schema: dict
    ) -> dict:
        """Call Ollama with JSON output."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{system}\n\n{user_prompt}",
                        "stream": False,
                    },
                    timeout=120.0,
                )

                if response.status_code != 200:
                    raise ValueError(
                        f"Ollama error (status {response.status_code}): "
                        f"{response.text}"
                    )

                result = response.json()
                text = result.get("response", "")

                # Try to find JSON in the response
                json_start = text.find("{")
                json_end = text.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = text[json_start:json_end]
                    return json.loads(json_str)

                raise ValueError("No JSON found in Ollama response")

        except httpx.RequestError as e:
            raise ValueError(f"Ollama connection error: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Ollama JSON response: {e}") from e
