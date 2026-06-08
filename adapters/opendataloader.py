"""
OpenDataLoader PDF adapter (Python SDK over a Java engine).

OpenDataLoader PDF (https://github.com/opendataloader-project/opendataloader-pdf)
is a pure-rule-based PDF extractor. The Python package wraps a Java engine
(requires Java 11+) and is invoked as:

    import opendataloader_pdf
    opendataloader_pdf.convert(
        input_path=["file.pdf"],
        output_dir="out/",
        format="markdown,json",
    )

It writes one file per requested format into ``output_dir`` (e.g.
``<stem>.md`` and ``<stem>.json``). No GPU is used.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict

from .base import DocumentExtractor, ExtractionResult


class OpenDataLoaderAdapter(DocumentExtractor):
    """Adapter for OpenDataLoader PDF (Python SDK)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "OpenDataLoader"
        try:
            import opendataloader_pdf
            self._odl = opendataloader_pdf
        except ImportError as e:
            self.logger.error("Failed to import opendataloader_pdf: %s", e)
            raise
        try:
            from importlib.metadata import version
            self.version = version("opendataloader-pdf")
        except Exception:
            self.version = "unknown"

    def _run_tool(self, input_path: str) -> Dict[str, Any]:
        """Run OpenDataLoader and collect its JSON + markdown output files."""
        import shutil

        start = time.time()
        tmp_dir = Path("./tmp_opendataloader_output")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # convert() writes <stem>.json / <stem>.md into output_dir. The Java
        # engine prints progress to stdout; we don't need its return value.
        self._odl.convert(
            input_path=[input_path],
            output_dir=str(tmp_dir),
            format="markdown,json",
        )
        runtime = time.time() - start

        # Collect output recursively (the engine may nest per-document folders).
        json_candidates = sorted(tmp_dir.rglob("*.json"))
        if not json_candidates:
            raise RuntimeError(
                "OpenDataLoader did not produce a JSON file in the output directory"
            )
        with open(json_candidates[0], "r", encoding="utf-8") as f:
            raw = json.load(f)

        markdown_direct = ""
        md_files = sorted(tmp_dir.rglob("*.md"))
        if md_files:
            markdown_direct = "\n\n".join(p.read_text(encoding="utf-8") for p in md_files)

        return {
            "document": raw,
            "markdown_direct": markdown_direct,
            "runtime_seconds": runtime,
        }

    def run(self, input_path: str) -> ExtractionResult:
        start_time = time.time()
        try:
            raw = self._run_tool(input_path)
            runtime = raw.get("runtime_seconds", time.time() - start_time)
            doc = raw.get("document", {})

            markdown_direct = raw.get("markdown_direct", "")
            json_output = json.dumps(doc, ensure_ascii=False, indent=2, default=str)

            # Markdown-from-JSON deferred (OpenDataLoader uses its own JSON
            # structure, not the canonical schema). Keep native markdown + JSON.
            markdown_from_json = ""

            # Best-effort page count from common keys in the JSON structure.
            num_pages = 0
            if isinstance(doc, dict):
                pages_obj = doc.get("pages") or doc.get("page_list")
                if isinstance(pages_obj, (list, dict)):
                    num_pages = len(pages_obj)

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
            self.logger.error("OpenDataLoader failed: %s", exc)
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
