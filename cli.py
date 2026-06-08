#!/usr/bin/env python3
"""
Command-line interface for the document extraction testing pipeline.

Usage:
    python cli.py --input <path_to_document> --tools PaddleOCR16,MinerU,Docling
    python cli.py --input <directory> --recursive --tools all
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

from adapters import PaddleOCRAdapter, MinerUAdapter, DoclingAdapter
from adapters.granite_docling import GraniteDoclingAdapter
from adapters.opendataloader import OpenDataLoaderAdapter
from utils.storage import ResultWriter, setup_logging
from utils.config import load_config, Config


def get_available_tools() -> Dict[str, Any]:
    """Return available tool classes and their names."""
    return {
        "PaddleOCR15": lambda: PaddleOCRAdapter(version="1.5"),
        "PaddleOCR16": lambda: PaddleOCRAdapter(version="1.6"),
        "MinerU": MinerUAdapter,
        "Docling": DoclingAdapter,
        "GraniteDocling": GraniteDoclingAdapter,
        "OpenDataLoader": OpenDataLoaderAdapter,
    }


def create_tool(tool_name: str):
    """Create a tool instance by name."""
    tools = get_available_tools()
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}. Available: {list(tools.keys())}")
    return tools[tool_name]()


def run_pipeline(input_path: str, tools: Dict[str, Any], writer, logger) -> List[Dict[str, Any]]:
    """Run all (already-instantiated) tools on a single input.

    Tools are created once by the caller and reused across every input file so
    that heavy models load a single time. Reloading a multi-GB model per file
    otherwise exhausts GPU memory.
    """
    results = []

    for tool_name, tool in tools.items():
        logger.info(f"Running {tool_name} on {input_path}")
        start_time = time.time()

        try:
            result = tool.run(input_path)
            results.append(result.to_dict())
            logger.info(f"{tool_name} completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            results.append({
                "tool_name": tool_name,
                "input_path": input_path,
                "status": "error",
                "error": str(e),
                "markdown_direct": "",
                "json_output": "",
                "markdown_from_json": "",
                "metadata": {"runtime_seconds": time.time() - start_time},
            })

    # Write all results
    for result in results:
        writer.write_result(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Document extraction testing pipeline")
    parser.add_argument("--input", required=True, help="Input file or directory path")
    parser.add_argument(
        "--tools",
        default="all",
        help="Comma-separated list of tools (PaddleOCR15,PaddleOCR16,MinerU,Docling,GraniteDocling) or 'all'"
    )
    parser.add_argument("--output", default="./results", help="Output directory")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--recursive", action="store_true", help="Process directories recursively")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    config.output_dir = args.output
    if args.tools != "all":
        config.tools = args.tools.split(",")

    # Setup logging
    logger = setup_logging("doc_extraction")
    logger.info(f"Starting pipeline with config: {config}")

    # Determine input files
    input_path = Path(args.input)
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        files = [str(input_path)]
    elif input_path.is_dir():
        if args.recursive:
            files = [str(p) for p in input_path.rglob("*.pdf")]
        else:
            files = [str(p) for p in input_path.glob("*.pdf")]
    else:
        logger.error(f"Invalid input path: {input_path}")
        sys.exit(1)

    logger.info(f"Found {len(files)} PDF files to process")

    # Instantiate each tool ONCE so heavy models load a single time and are
    # reused across all input files. (Reloading a multi-GB VL model per file
    # exhausts GPU memory.) A tool that fails to initialize is skipped, and an
    # error result is recorded for it against every input file.
    writer = ResultWriter(config.output_dir)
    tools = {}
    init_errors = {}
    for tool_name in config.tools:
        try:
            tools[tool_name] = create_tool(tool_name)
        except Exception as e:
            logger.error(f"Failed to initialize {tool_name}: {e}")
            init_errors[tool_name] = str(e)

    # Run pipeline
    all_results = []
    for file_path in files:
        logger.info(f"Processing: {file_path}")
        results = run_pipeline(file_path, tools, writer, logger)
        # Record initialization failures as error results per file.
        for tool_name, err in init_errors.items():
            result = {
                "tool_name": tool_name,
                "input_path": file_path,
                "status": "error",
                "error": f"initialization failed: {err}",
                "markdown_direct": "",
                "json_output": "",
                "markdown_from_json": "",
                "metadata": {"runtime_seconds": 0},
            }
            writer.write_result(result)
            results.append(result)
        all_results.extend(results)

    # Generate comparison report
    report_path = Path(config.output_dir) / "comparison_report.md"
    writer.write_summary_report(all_results, str(report_path))
    logger.info(f"Comparison report written to {report_path}")

    # Print summary table
    print("\n" + "=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)
    print(f"{'Tool':<20} | {'Status':<10} | {'Pages':<6} | {'Runtime':<10} | {'MD Direct':<10} | {'JSON':<6} | {'MD from JSON':<12}")
    print("-" * 80)
    for r in all_results:
        direct = "✓" if r.get("markdown_direct") else "✗"
        js = "✓" if r.get("json_output") else "✗"
        md = "✓" if r.get("markdown_from_json") else "✗"
        print(f"{r['tool_name']:<20} | {r['status']:<10} | {r['metadata'].get('pages', 0):<6} | {r['metadata'].get('runtime_seconds', 0):<10.2f} | {direct:<10} | {js:<6} | {md:<12}")
    print("=" * 80)


if __name__ == "__main__":
    main()