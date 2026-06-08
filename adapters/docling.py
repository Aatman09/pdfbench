"""
Docling adapter.

Docling can be invoked either via CLI:
    docling --input <pdf_path> --output <dir>
or programmatically via its Python API.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict

from .base import DocumentExtractor, ExtractionResult
from schema import (
    normalize_docling_output,
    json_to_markdown,
    CanonicalDocument,
)


class DoclingAdapter(DocumentExtractor):
    """Adapter for Docling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "Docling"
        try:
            from docling.document_converter import DocumentConverter
            self.DocumentConverter = DocumentConverter
        except ImportError as e:
            self.logger.error("Failed to import Docling: %s", e)
            raise
        # Try to get version
        try:
            from importlib.metadata import version
            self.version = version("docling")
        except Exception:
            self.version = "unknown"

    def _run_tool(self, input_path: str) -> Dict[str, Any]:
        """Process the document with Docling and return its structured output.

        ``result.document`` is a ``DoclingDocument``. Its real serialization API
        is ``export_to_dict()`` (full structured JSON) and ``export_to_markdown()``
        (native markdown) -- there is no ``to_json()`` method.
        """
        start = time.time()
        converter = self.DocumentConverter()
        result = converter.convert(input_path)
        runtime = time.time() - start

        doc = result.document
        try:
            doc_dict = doc.export_to_dict()
        except Exception as exc:
            self.logger.warning("export_to_dict failed: %s", exc)
            doc_dict = {}
        try:
            markdown = doc.export_to_markdown()
        except Exception as exc:
            self.logger.warning("export_to_markdown failed: %s", exc)
            markdown = ""

        return {
            "document": doc_dict,
            "markdown_direct": markdown,
            "runtime_seconds": runtime,
        }

    def run(self, input_path: str) -> ExtractionResult:
        start_time = time.time()
        try:
            raw = self._run_tool(input_path)
            runtime = raw.get("runtime_seconds", time.time() - start_time)
            doc_dict = raw.get("document", {})

            # Direct markdown – Docling's own native rendering.
            markdown_direct = raw.get("markdown_direct", "")

            # Full structured JSON from export_to_dict().
            json_output = json.dumps(doc_dict, ensure_ascii=False, indent=2, default=str)

            # Markdown from JSON – deferred. DoclingDocument.export_to_dict()
            # stores `pages` as a dict and uses texts/tables/body, which the
            # current canonical normalizer (list-of-pages with text_blocks) does
            # not understand. We keep the basics (json + native markdown) and
            # revisit the normalizer later.
            markdown_from_json = ""

            pages_obj = doc_dict.get("pages")
            num_pages = len(pages_obj) if isinstance(pages_obj, (dict, list)) else 0

            metadata = {
                "pages": num_pages,
                "model_version": self.version,
                "runtime_seconds": runtime,
                "tool_version": self.version,
            }

            return self._create_result(
                tool_name=self.tool_name,
                input_path=input_path,
                status="success",
                error=None,
                markdown_direct=markdown_direct,
                json_output=json_output,
                markdown_from_json=markdown_from_json,
                metadata=metadata,
            )
        except Exception as exc:
            runtime = time.time() - start_time
            self.logger.error("Docling failed: %s", exc)
            return self._create_result(
                tool_name=self.tool_name,
                input_path=input_path,
                status="error",
                error=str(exc),
                markdown_direct="",
                json_output="",
                markdown_from_json="",
                metadata={"runtime_seconds": runtime, "model_version": self.version},
            )