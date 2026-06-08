"""
Canonical schema and normalization layer for document extraction outputs.
"""

from .canonical import (
    Page,
    Block,
    CanonicalDocument,
    normalize_paddleocr_output,
    normalize_mineru_output,
    normalize_docling_output,
    normalize_granite_docling_output,
    json_to_markdown,
)

__all__ = [
    "Page",
    "Block",
    "CanonicalDocument",
    "normalize_paddleocr_output",
    "normalize_mineru_output",
    "normalize_docling_output",
    "normalize_granite_docling_output",
    "json_to_markdown",
]