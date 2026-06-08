"""
Result storage module for handling document extraction outputs.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

class ResultWriter:
    """Writes structured results to disk in standardized format."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.summary_file = Path(base_dir) / "summary.jsonl"

    def write_result(self, result: Dict[str, Any]):
        """Write a single result to summary file and output files."""
        base_name = os.path.splitext(os.path.basename(result["input_path"]))[0]
        # Include the tool name in the path so results from different tools
        # don't overwrite each other.
        tool_slug = result["tool_name"].replace(" ", "_").replace("/", "_")
        output_dir = Path(self.base_dir) / base_name / tool_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write direct outputs
        if result["markdown_direct"]:
            (output_dir / f"{base_name}_direct.md").write_text(result["markdown_direct"])
        if result["json_output"]:
            (output_dir / f"{base_name}_json.json").write_text(result["json_output"])
        if result["markdown_from_json"]:
            (output_dir / f"{base_name}_json_to_md.md").write_text(result["markdown_from_json"])

        # Write to summary file
        with open(self.summary_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def _load_all_results(self) -> List[Dict[str, Any]]:
        """Load every result ever written from summary.jsonl, deduplicated.

        The summary file is append-only across runs, so the same (document, tool)
        pair can appear multiple times. We keep the LAST occurrence (the most
        recent run) for each pair so the report reflects current state without
        losing tools that were run in earlier invocations.
        """
        if not self.summary_file.exists():
            return []
        latest: Dict[tuple, Dict[str, Any]] = {}
        with open(self.summary_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (row.get("input_path", ""), row.get("tool_name", ""))
                latest[key] = row
        # Stable ordering: by document, then tool name.
        return sorted(latest.values(), key=lambda r: (r.get("input_path", ""), r.get("tool_name", "")))

    def write_summary_report(self, results: List[Dict[str, Any]], report_path: str):
        """Generate markdown comparison report.

        The ``results`` argument (current run) is ignored in favour of the full,
        deduplicated history in summary.jsonl, so the report always shows every
        tool across every run rather than only the most recent invocation.
        """
        results = self._load_all_results()

        report_lines = [
            "# Document Extraction Tool Comparison Report\n",
            f"**Generated at**: {os.popen('date').read().strip()}\n",
            "## Summary Statistics\n",
        ]

        # Create a summary table
        report_lines.extend([
            "| Document | Tool | Status | Pages | Runtime (s) | Markdown Direct | JSON | Markdown from JSON |",
            "|----------|------|--------|-------|-------------|-----------------|------|-------------------|"
        ])

        for result in results:
            doc = os.path.splitext(os.path.basename(result.get("input_path", "")))[0]
            status = "✓" if result["status"] == "success" else "✗"
            pages = result["metadata"].get("pages", 0)
            runtime = result["metadata"].get("runtime_seconds", 0)
            has_direct = "✓" if result["markdown_direct"] else "✗"
            has_json = "✓" if result["json_output"] else "✗"
            has_from_json = "✓" if result["markdown_from_json"] else "✗"

            report_lines.append(
                f"| {doc} | {result['tool_name']} | {status} | {pages} | {runtime:.2f} | {has_direct} | {has_json} | {has_from_json} |"
            )

        report_lines.extend(["\n", "## Detailed Results\n"])

        for result in results:
            report_lines.extend([
                f"### {result['tool_name']}\n",
                f"- **Input**: `{result['input_path']}`\n",
                f"- **Status**: {result['status']}\n",
            ])

            if result["status"] == "error":
                report_lines.append(f"- **Error**: {result['error']}\n")

            report_lines.extend([
                f"- **Runtime**: {result['metadata'].get('runtime_seconds', 0):.2f} seconds\n",
                f"- **Pages Processed**: {result['metadata'].get('pages', 0)}\n",
                "\n"
            ])

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

# Setup logging
def setup_logging(logger_name: str):
    """Configure logging for a specific logger."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create file handler
    file_handler = logging.FileHandler("doc_extraction.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger