"""
MinerU adapter (CLI based).

MinerU is invoked as:
    mineru -p "<input_path>" -o <output_dir>
It writes its results to the output directory; we will read the JSON file
named `result.json` (or similar) if it exists.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from .base import DocumentExtractor, ExtractionResult
from schema import (
    normalize_mineru_output,
    json_to_markdown,
    CanonicalDocument,
)


class MinerUAdapter(DocumentExtractor):
    """Adapter for the MinerU CLI tool."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = "MinerU"
        # MinerU version detection – try `mineru --version`
        try:
            result = subprocess.run(["mineru", "--version"], capture_output=True, text=True, check=True)
            self.version = result.stdout.strip()
        except Exception:
            self.version = "unknown"

    def _run_cli(self, input_path: str) -> Dict[str, Any]:
        """Execute MinerU CLI and return parsed JSON output.

        MinerU creates an output directory containing a JSON file (usually
        `output.json` or `result.json`). We will read the first JSON file we
        encounter in that directory.
        """
        import shutil

        start = time.time()
        tmp_dir = Path("./tmp_mineru_output")
        # Ensure a clean directory each run. MinerU writes a nested tree
        # (<stem>/auto/...), so remove the whole dir rather than unlinking files.
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["mineru", "-p", input_path, "-o", str(tmp_dir), "--backend", "pipeline"]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"MinerU CLI failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("MinerU CLI timed out")

        # MinerU writes its output under <tmp>/<stem>/auto/. Search recursively
        # and prefer the rich structured file (*_middle.json), then the content
        # list, then any JSON.
        json_candidates = list(tmp_dir.rglob("*.json"))
        if not json_candidates:
            raise RuntimeError("MinerU did not produce a JSON file in the output directory")

        def _rank(p: Path) -> int:
            name = p.name.lower()
            if name.endswith("_middle.json"):
                return 0
            if "content_list" in name:
                return 1
            if name.endswith("_model.json"):
                return 2
            return 3

        json_path = sorted(json_candidates, key=_rank)[0]
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # raw may be a list (content_list) or dict (middle). Wrap lists so we can
        # attach metadata uniformly.
        if isinstance(raw, list):
            raw = {"content": raw}
        runtime = time.time() - start
        raw["runtime_seconds"] = runtime
        return raw

    def run(self, input_path: str) -> ExtractionResult:
        start_time = time.time()
        try:
            raw = self._run_cli(input_path)
            runtime = raw.get("runtime_seconds", time.time() - start_time)

            # Normalization to canonical schema
            canonical: CanonicalDocument = normalize_mineru_output(self.tool_name, raw, input_path)

            # MinerU writes its markdown under <tmp>/<stem>/auto/<stem>.md.
            # Search recursively and concatenate any markdown found.
            markdown_direct = ""
            out_dir = Path("./tmp_mineru_output")
            md_files = list(out_dir.rglob("*.md"))
            if md_files:
                parts = []
                for p in sorted(md_files):
                    parts.append(p.read_text(encoding="utf-8"))
                markdown_direct = "\n\n".join(parts)

            json_output = json.dumps(raw, ensure_ascii=False, indent=2)
            markdown_from_json = json_to_markdown(canonical)

            metadata = {
                "pages": len(canonical.pages),
                "model_version": self.version,
                "runtime_seconds": runtime,
                "tool_version": self.version,
                "page_numbers": ",".join(str(p.page_number) for p in canonical.pages),
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
            self.logger.error("MinerU failed: %s", exc)
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