"""LLM-based statement extractor with chunking and retry."""


from pydantic import ValidationError

from ccstmt.extract.base import Extractor
from ccstmt.extract.providers.anthropic_provider import AnthropicProvider
from ccstmt.extract.providers.ollama_provider import OllamaProvider
from ccstmt.extract.providers.openai_provider import OpenAIProvider
from ccstmt.extract.schema import StatementExtract


class LLMExtractor(Extractor):
    """LLM-based extractor with chunking for long statements."""

    PROMPT_VERSION = "1.0"

    def __init__(self, provider_name: str, **provider_kwargs):
        """Initialize LLM extractor.

        Args:
            provider_name: "anthropic", "openai", or "ollama"
            **provider_kwargs: Passed to provider (e.g., api_key, model)
        """
        if provider_name == "anthropic":
            self.provider = AnthropicProvider(**provider_kwargs)
        elif provider_name == "openai":
            self.provider = OpenAIProvider(**provider_kwargs)
        elif provider_name == "ollama":
            self.provider = OllamaProvider(**provider_kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

        self.provider_name = provider_name
        self.model = getattr(self.provider, "model", provider_name)

    def can_handle(self, issuer: str, text: str) -> bool:
        """LLM can attempt to extract any statement."""
        return bool(text and len(text) > 100)

    def extract(self, text: str) -> StatementExtract:
        """Extract statement from text using LLM."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text)

        try:
            # Try extraction
            result_json = self.provider.complete_json(
                system_prompt, user_prompt, {}
            )
            statement = StatementExtract(**result_json)
            return statement

        except ValidationError as e:
            # Retry once with error feedback
            error_msg = str(e)
            retry_prompt = self._build_retry_prompt(text, error_msg)

            try:
                result_json = self.provider.complete_json(
                    system_prompt, retry_prompt, {}
                )
                statement = StatementExtract(**result_json)
                return statement
            except (ValidationError, ValueError) as retry_error:
                raise ValueError(
                    f"Extraction failed after retry: {retry_error}"
                ) from retry_error

        except ValueError as e:
            raise ValueError(f"Extraction failed: {e}") from e

    def _build_system_prompt(self) -> str:
        """Build system prompt for statement extraction."""
        return """You are an expert credit card statement parser.
Extract structured data from credit card statement text.

Return ONLY valid JSON matching this schema:
{
  "issuer": "string",
  "card_last4": "4 digits",
  "card_variant": "string or null",
  "currency": "INR or other",
  "statement_date": "YYYY-MM-DD",
  "period_start": "YYYY-MM-DD or null",
  "period_end": "YYYY-MM-DD or null",
  "payment_due_date": "YYYY-MM-DD or null",
  "total_amount_due": "decimal",
  "minimum_amount_due": "decimal or null",
  "previous_balance": "decimal or null",
  "payments_credits": "decimal or null",
  "purchases_debits": "decimal or null",
  "fees_charges": "decimal or null",
  "credit_limit": "decimal or null",
  "available_credit": "decimal or null",
  "reward_points_closing": "decimal or null",
  "transactions": [
    {
      "txn_date": "YYYY-MM-DD",
      "posting_date": "YYYY-MM-DD or null",
      "description": "string",
      "amount": "decimal (positive)",
      "direction": "debit or credit",
      "card_last4": "4 digits or null",
      "original_amount": "decimal or null",
      "original_currency": "string or null",
      "is_emi": false,
      "reference": "string or null"
    }
  ]
}

IMPORTANT:
- Extract ONLY what is present; use null when absent
- Do NOT infer or compute values
- Dates: Use DD/MM/YYYY from statement as YYYY-MM-DD
- Numbers: Handle Indian format (1,23,456.78)
- Amounts: Always positive; direction indicates debit/credit
- Every transaction must appear EXACTLY ONCE
"""

    def _build_user_prompt(self, text: str) -> str:
        """Build user prompt for extraction."""
        return f"""Extract all data from this credit card statement:

{text}

Return valid JSON only."""

    def _build_retry_prompt(self, text: str, error_msg: str) -> str:
        """Build retry prompt with error feedback."""
        return f"""Previous extraction had errors: {error_msg}

Please retry carefully:

{text}

Return valid JSON only."""
