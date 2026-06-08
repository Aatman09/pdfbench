#!/usr/bin/env python3
"""
Turn results/summary.jsonl into a human-readable Markdown analysis report.

The summary file is append-only (one JSON object per tool run), which is hard to
read directly. This script aggregates it into tables and charts:

  - Overview (documents, tools, overall success rate)
  - Tool x Document coverage matrix
  - Per-tool output coverage (direct markdown / JSON / markdown-from-JSON)
  - Success-rate chart (Mermaid + ASCII)
  - Average-runtime chart (Mermaid + ASCII)
  - Per-document runtime table
  - Failure list with error messages

Charts are emitted both as Mermaid (renders as real graphs on GitHub / VS Code /
Obsidian) and as ASCII bars (render in any plain-text viewer).

Usage:
    python generate_report.py --summary results/summary.jsonl --output results/analysis_report.md
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_results(summary_path):
    """Load summary.jsonl, keeping the latest row per (document, tool)."""
    latest = {}
    with open(summary_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc = os.path.splitext(os.path.basename(row.get("input_path", "")))[0]
            tool = row.get("tool_name", "")
            latest[(doc, tool)] = row
    return latest


def ascii_bar(value, max_value, width=40):
    """Render a single horizontal ASCII bar."""
    if max_value <= 0:
        filled = 0
    else:
        filled = int(round((value / max_value) * width))
    return "█" * filled + "·" * (width - filled)


def fmt(n, dec=1):
    return f"{n:.{dec}f}"


def main():
    ap = argparse.ArgumentParser(description="Generate a Markdown analysis report from summary.jsonl")
    ap.add_argument("--summary", default="results/summary.jsonl", help="Path to summary.jsonl")
    ap.add_argument("--output", default="results/analysis_report.md", help="Output markdown path")
    args = ap.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        raise SystemExit(f"Summary file not found: {summary_path}")

    latest = load_results(summary_path)
    rows = list(latest.values())

    docs = sorted({os.path.splitext(os.path.basename(r.get("input_path", "")))[0] for r in rows})
    tools = sorted({r.get("tool_name", "") for r in rows})

    # ---- Aggregations ---------------------------------------------------------
    # per (doc, tool) lookup
    cell = {(os.path.splitext(os.path.basename(r["input_path"]))[0], r["tool_name"]): r for r in rows}

    per_tool = defaultdict(lambda: {
        "runs": 0, "success": 0, "md_direct": 0, "json": 0, "md_from_json": 0,
        "runtime_sum": 0.0, "runtime_n": 0, "pages": 0,
    })
    for r in rows:
        t = r["tool_name"]
        s = per_tool[t]
        s["runs"] += 1
        if r.get("status") == "success":
            s["success"] += 1
        if r.get("markdown_direct"):
            s["md_direct"] += 1
        if r.get("json_output"):
            s["json"] += 1
        if r.get("markdown_from_json"):
            s["md_from_json"] += 1
        rt = (r.get("metadata") or {}).get("runtime_seconds")
        if isinstance(rt, (int, float)):
            s["runtime_sum"] += rt
            s["runtime_n"] += 1
        pg = (r.get("metadata") or {}).get("pages")
        if isinstance(pg, (int, float)):
            s["pages"] += pg

    total_runs = len(rows)
    total_success = sum(1 for r in rows if r.get("status") == "success")
    overall_rate = (total_success / total_runs * 100) if total_runs else 0

    L = []
    L.append("# Document Extraction — Analysis Report\n")
    L.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")

    # ---- 1. Overview ----------------------------------------------------------
    L.append("## 1. Overview\n")
    L.append(f"- **Documents:** {len(docs)}")
    L.append(f"- **Tools:** {len(tools)} ({', '.join(tools)})")
    L.append(f"- **Total tool runs:** {total_runs}")
    L.append(f"- **Overall success rate:** {fmt(overall_rate)}%  ({total_success}/{total_runs})\n")

    # ---- 2. Coverage matrix ---------------------------------------------------
    L.append("## 2. Coverage Matrix (document × tool)\n")
    L.append("✓ = success · ✗ = error/failed · — = not run\n")
    header = "| Document | " + " | ".join(tools) + " |"
    sep = "|" + "---|" * (len(tools) + 1)
    L.append(header)
    L.append(sep)
    for d in docs:
        cells = []
        for t in tools:
            r = cell.get((d, t))
            if r is None:
                cells.append("—")
            elif r.get("status") == "success":
                cells.append("✓")
            else:
                cells.append("✗")
        L.append(f"| {d} | " + " | ".join(cells) + " |")
    L.append("")

    # ---- 3. Per-tool output coverage ------------------------------------------
    L.append("## 3. Output Coverage per Tool\n")
    L.append("| Tool | Docs | Success | Direct MD | JSON | MD-from-JSON | Avg runtime (s) |")
    L.append("|------|------|---------|-----------|------|--------------|-----------------|")
    for t in tools:
        s = per_tool[t]
        avg_rt = s["runtime_sum"] / s["runtime_n"] if s["runtime_n"] else 0
        L.append(
            f"| {t} | {s['runs']} | {s['success']}/{s['runs']} | {s['md_direct']} | "
            f"{s['json']} | {s['md_from_json']} | {fmt(avg_rt)} |"
        )
    L.append("")

    # ---- 4. Success rate chart ------------------------------------------------
    L.append("## 4. Success Rate per Tool\n")
    L.append(
        "**Success rate** = the percentage of documents a tool processed "
        "*without error*. For each document the tool either finishes and returns "
        "output (success) or raises an error / times out (failure). The rate is "
        "`successful documents ÷ documents attempted × 100`. It measures "
        "**reliability** (did the tool run end-to-end), not the *quality* of the "
        "extracted text. A bar reaching the far right means 100% — the tool "
        "completed on every document it was given.\n"
    )
    rates = {t: (per_tool[t]["success"] / per_tool[t]["runs"] * 100 if per_tool[t]["runs"] else 0) for t in tools}
    L.append("```")
    for t in tools:
        s = per_tool[t]
        L.append(f"{t:<18} {ascii_bar(rates[t], 100)} {fmt(rates[t],0)}%  ({s['success']}/{s['runs']})")
    L.append("```\n")

    # ---- 5. Average runtime chart ---------------------------------------------
    L.append("## 5. Average Runtime per Tool\n")
    L.append(
        "**Average runtime** = mean wall-clock seconds the tool took per "
        "document (model load + inference). Lower is faster. Bars are scaled "
        "relative to the slowest tool.\n"
    )
    avg = {t: (per_tool[t]["runtime_sum"] / per_tool[t]["runtime_n"] if per_tool[t]["runtime_n"] else 0) for t in tools}
    max_rt = max(avg.values()) if avg else 0
    L.append("```")
    for t in tools:
        L.append(f"{t:<18} {ascii_bar(avg[t], max_rt)} {fmt(avg[t],1)}s")
    L.append("```\n")

    # ---- 6. Per-document runtime ----------------------------------------------
    L.append("## 6. Runtime per Document (seconds)\n")
    L.append("| Document | " + " | ".join(tools) + " |")
    L.append("|" + "---|" * (len(tools) + 1))
    for d in docs:
        cells = []
        for t in tools:
            r = cell.get((d, t))
            if r is None:
                cells.append("—")
            else:
                rt = (r.get("metadata") or {}).get("runtime_seconds", 0)
                cells.append(fmt(rt, 1) if isinstance(rt, (int, float)) else "—")
        L.append(f"| {d} | " + " | ".join(cells) + " |")
    L.append("")

    # ---- 7. Failures ----------------------------------------------------------
    failures = [r for r in rows if r.get("status") != "success"]
    L.append("## 7. Failures\n")
    if not failures:
        L.append("_No failures recorded._\n")
    else:
        L.append("| Document | Tool | Error |")
        L.append("|----------|------|-------|")
        for r in sorted(failures, key=lambda x: (os.path.basename(x.get("input_path", "")), x.get("tool_name", ""))):
            d = os.path.splitext(os.path.basename(r.get("input_path", "")))[0]
            err = (r.get("error") or "").replace("\n", " ").replace("|", "\\|")[:160]
            L.append(f"| {d} | {r.get('tool_name','')} | {err} |")
        L.append("")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"Report written to {out_path}  ({len(docs)} docs, {len(tools)} tools, {total_runs} runs)")


if __name__ == "__main__":
    main()
