"""
PaddleOCR VL adapters (versions 1.5 and 1.6).

Both versions expose the same Python API:
    from paddleocr import PaddleOCRVL
    pipeline = PaddleOCRVL(pipeline_version="v1.5")
    output = pipeline.predict(path)
The output is a list of page objects containing text blocks and tables.
"""

import json
import os
import time
from typing import Any, Dict

from .base import DocumentExtractor, ExtractionResult
from schema import (
    normalize_paddleocr_output,
    json_to_markdown,
    CanonicalDocument,
)


class PaddleOCRAdapter(DocumentExtractor):
    """Adapter for PaddleOCR VL (both 1.5 and 1.6)."""

    def __init__(self, version: str = "1.6", **kwargs):
        super().__init__(**kwargs)
        if version not in {"1.5", "1.6"}:
            raise ValueError(f"Unsupported PaddleOCR VL version: {version}")
        self.version = version
        self.tool_name = f"PaddleOCR VL {version}"
        # Import lazily to avoid ImportError when PaddleOCR is not installed
        try:
            from paddleocr import PaddleOCRVL
        except Exception as exc:
            self.logger.error("Failed to import PaddleOCRVL: %s", exc)
            raise
        self.PaddleOCRVL = PaddleOCRVL
        # The VL pipeline is created lazily and cached so the (multi-GB) model
        # loads only once and is reused across every input file. Reloading it
        # per file exhausts GPU memory on small cards.
        self._pipeline = None

    def _get_pipeline(self):
        """Create the VL pipeline on first use and reuse it thereafter."""
        if self._pipeline is None:
            self.logger.info("Loading PaddleOCR-VL %s pipeline (one-time)", self.version)
            self._pipeline = self.PaddleOCRVL(pipeline_version=f"v{self.version}")
        return self._pipeline

    def _run_tool(self, input_path: str) -> Dict[str, Any]:
        """Run the (cached) PaddleOCR pipeline and capture all output types.

        ``pipeline.predict`` returns a generator yielding one result object per
        page. Each result object exposes:
          - ``res.markdown``  -> dict with ``"markdown_texts"`` (PaddleOCR's own
            native markdown rendering for that page)
          - ``res.json``      -> a JSON-serializable dict of the parsed structure
        We iterate the generator a single time and collect both, so we never run
        the (expensive) VL inference more than once per document.
        """
        pipeline = self._get_pipeline()
        start = time.time()

        markdown_pages = []
        json_pages = []
        try:
            for res in pipeline.predict(input_path):
                # Native markdown for this page.
                try:
                    md = res.markdown
                    markdown_pages.append(
                        md.get("markdown_texts", "") if isinstance(md, dict) else str(md)
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    self.logger.warning("No native markdown for a page: %s", exc)
                # Serializable JSON for this page.
                try:
                    json_pages.append(res.json)
                except Exception as exc:  # pragma: no cover - defensive
                    self.logger.warning("No JSON for a page: %s", exc)
        finally:
            # Free per-document activation memory (NOT the model weights, which
            # we keep resident for the next file) to avoid memory creep.
            self._empty_cuda_cache()

        runtime = time.time() - start
        return {
            "markdown_pages": markdown_pages,
            "json_pages": json_pages,
            # Kept under "pages" so the canonical normalizer can still inspect it.
            "pages": json_pages,
            "runtime_seconds": runtime,
        }

    def _empty_cuda_cache(self) -> None:
        """Release cached/idle GPU blocks between documents (keeps the model)."""
        try:
            import paddle

            if paddle.device.is_compiled_with_cuda():
                paddle.device.cuda.empty_cache()
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Could not empty CUDA cache: %s", exc)

    def run(self, input_path: str) -> ExtractionResult:
        start_time = time.time()
        try:
            # Run the underlying tool
            raw = self._run_tool(input_path)
            runtime = raw.get("runtime_seconds", time.time() - start_time)

            # Direct markdown – PaddleOCR's own native rendering, captured per
            # page during the single predict pass above.
            markdown_direct = "\n\n".join(
                p for p in raw.get("markdown_pages", []) if p
            )

            # Native JSON output – the per-page serializable dicts. ``default=str``
            # guards against any non-JSON values (e.g. numpy/bbox objects).
            json_output = json.dumps(
                raw.get("json_pages", []), ensure_ascii=False, indent=2, default=str
            )

            # Markdown from JSON – deferred for now. PaddleOCR-VL's JSON uses a
            # different structure ("parsing_res_list") than the canonical
            # normalizer expects, so we skip this path until we implement a
            # proper VL normalizer. For now we only capture the basics:
            # native markdown (markdown_direct) and raw JSON (json_output).
            markdown_from_json = ""

            num_pages = len(raw.get("markdown_pages", []))

            metadata = {
                "pages": num_pages,
                "model_version": self.version,
                "runtime_seconds": runtime,
                "tool_version": "unknown",  # Could be filled via pip show
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
            self.logger.error("PaddleOCR %s failed: %s", self.version, exc)
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
