"""
Abstract base class for document extraction adapters.

All tool-specific adapters must inherit from DocumentExtractor and implement
the run() method. This ensures a consistent interface across all tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time


@dataclass
class ExtractionResult:
    """Standardized result structure returned by all adapters."""

    tool_name: str
    input_path: str
    status: str  # "success" or "error"
    error: Optional[str]
    markdown_direct: str
    json_output: str
    markdown_from_json: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "input_path": self.input_path,
            "status": self.status,
            "error": self.error,
            "markdown_direct": self.markdown_direct,
            "json_output": self.json_output,
            "markdown_from_json": self.markdown_from_json,
            "metadata": self.metadata,
        }


class DocumentExtractor(ABC):
    """
    Abstract base class for document extraction tools.

    Each adapter must:
    1. Call the underlying tool's API/CLI
    2. Normalize output to the canonical schema
    3. Generate all three output types (or empty strings if unsupported)
    4. Return a standardized ExtractionResult
    """

    def __init__(self, **kwargs):
        """Initialize the adapter with optional configuration."""
        self.config = kwargs
        self.logger = self._get_logger()

    def _get_logger(self):
        """Get or create a logger for this adapter."""
        import logging
        return logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def run(self, input_path: str) -> ExtractionResult:
        """
        Process the input document and return standardized results.

        Args:
            input_path: Path to the input document (PDF, image, etc.)

        Returns:
            ExtractionResult with all output types and metadata
        """
        pass

    def _create_result(
        self,
        tool_name: str,
        input_path: str,
        status: str,
        error: Optional[str],
        markdown_direct: str,
        json_output: str,
        markdown_from_json: str,
        metadata: Dict[str, Any],
    ) -> ExtractionResult:
        """Helper to create a standardized result."""
        return ExtractionResult(
            tool_name=tool_name,
            input_path=input_path,
            status=status,
            error=error,
            markdown_direct=markdown_direct,
            json_output=json_output,
            markdown_from_json=markdown_from_json,
            metadata=metadata,
        )

    def _detect_input_type(self, input_path: str) -> str:
        """Detect if input is PDF, image, or other."""
        import os
        ext = os.path.splitext(input_path)[1].lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
            return 'image'
        else:
            return 'unknown'