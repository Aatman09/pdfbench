"""
Granite Docling adapter (CLI based).

Granite Docling is invoked as:
    docling --pipeline vlm --vlm-model granite_docling <input>
It writes outputs similar to Docling.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from .base import DocumentExtractor, ExtractionResult
from schema import (
    normalize_granite_docling_output,
    json_to_markdown,
    CanonicalDocument,
)


class GraniteDoclingAdapter(DocumentExtractor):
    """Adapter for Granite Docling CLI."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "Granite Docling"
        # Attempt to get version from docling package (since Granite Docling uses docling CLI)
        try:
            from importlib.metadata import version
            self.version = version("docling")
        except Exception:
            self.version = "unknown"

    def _run_cli(self, input_path: str) -> Dict[str, Any]:
        """Execute Granite Docling CLI and return parsed JSON output."""
        import shutil

        start = time.time()
        tmp_dir = Path("./tmp_granite_docling_output")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # The docling CLI defaults to Markdown-only output, so we must request
        # JSON (and markdown) explicitly via --to, and point --output at our dir.
        cmd = [
            "docling",
            "--pipeline", "vlm",
            "--vlm-model", "granite_docling",
            "--to", "json",
            "--to", "md",
            "--output", str(tmp_dir),
            input_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=2400)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Granite Docling CLI failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Granite Docling CLI timed out")

        # Search recursively for the produced JSON.
        json_candidates = list(tmp_dir.rglob("*.json"))
        if not json_candidates:
            # Surface the CLI's own output to help diagnose a silent no-op.
            tail = (proc.stderr or proc.stdout or "").strip()[-400:]
            raise RuntimeError(
                "Granite Docling did not produce a JSON file. CLI output: " + tail
            )
        json_path = json_candidates[0]
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        runtime = time.time() - start
        raw["runtime_seconds"] = runtime
        return raw

    def run(self, input_path: str) -> ExtractionResult:
        start_time = time.time()
        try:
            raw = self._run_cli(input_path)
            runtime = raw.get("runtime_seconds", time.time() - start_time)

            # Attempt to read direct markdown if produced (search recursively).
            markdown_direct = ""
            tmp_dir = Path("./tmp_granite_docling_output")
            md_files = list(tmp_dir.rglob("*.md"))
            if md_files:
                parts = []
                for p in sorted(md_files):
                    parts.append(p.read_text(encoding="utf-8"))
                markdown_direct = "\n\n".join(parts)

            json_output = json.dumps(raw, ensure_ascii=False, indent=2, default=str)

            # Markdown from JSON – deferred (Granite uses Docling's JSON structure,
            # which the current canonical normalizer does not understand). Keep the
            # basics: native markdown + structured JSON.
            markdown_from_json = ""

            pages_obj = raw.get("pages")
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
            self.logger.error("Granite Docling failed: %s", exc)
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