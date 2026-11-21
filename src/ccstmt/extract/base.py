"""Base extractor interface."""

from abc import ABC, abstractmethod

from ccstmt.extract.schema import StatementExtract


class Extractor(ABC):
    """Base class for statement extractors."""

    @abstractmethod
    def can_handle(self, issuer: str, text: str) -> bool:
        """Check if this extractor can handle the statement."""

    @abstractmethod
    def extract(self, text: str) -> StatementExtract:
        """Extract statement data from text."""
        pass
