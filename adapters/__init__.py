"""Top-level package for document extraction adapters.

This module provides the public API for the various adapters that wrap
different document extraction tools (PaddleOCR, MinerU, Docling, etc.).
"""

from .base import DocumentExtractor, ExtractionResult
from .paddle_ocr import PaddleOCRAdapter
from .mineru import MinerUAdapter
from .docling import DoclingAdapter
from .granite_docling import GraniteDoclingAdapter
from .opendataloader import OpenDataLoaderAdapter

__all__ = [
    "DocumentExtractor",
    "ExtractionResult",
    "PaddleOCRAdapter",
    "MinerUAdapter",
    "DoclingAdapter",
    "GraniteDoclingAdapter",
    "OpenDataLoaderAdapter",
]