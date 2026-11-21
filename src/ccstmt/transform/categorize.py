"""Merchant categorization based on rules."""

import re
from pathlib import Path

import yaml


class Categorizer:
    """Rule-based merchant categorizer."""

    def __init__(self, rules_path: Path):
        """Load categorization rules from YAML."""
        with open(rules_path) as f:
            config = yaml.safe_load(f)

        self.rules = config.get("categories", [])
        self.default = config.get("default_category", "uncategorized")

    def categorize(self, merchant: str) -> tuple[str, str]:
        """Categorize merchant name.

        Returns (category, source) where source is "rule" or "default".
        """
        if not merchant:
            return self.default, "default"

        # Try each rule in order (first match wins)
        for rule in self.rules:
            pattern = rule.get("pattern", "")
            category = rule.get("category", "")

            if re.search(pattern, merchant, re.IGNORECASE):
                return category, "rule"

        return self.default, "default"
