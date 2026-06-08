# Document Extraction Comparison Pipeline

Run several PDF document-extraction tools over the same set of PDFs and compare
them side by side. Each tool produces a native **Markdown** file and a
structured **JSON** file per document, plus a combined **analysis report**
(coverage, success rate, runtime).

## Tools compared

| Tool key (`--tools`) | What it is | Engine | Env |
|----------------------|------------|--------|-----|
| `PaddleOCR15` | PaddleOCR-VL v1.5 | Vision-language OCR (GPU) | `venv-paddle` |
| `PaddleOCR16` | PaddleOCR-VL v1.6 | Vision-language OCR (GPU) | `venv-paddle` |
| `MinerU` | MinerU (pipeline backend) | Layout + OCR model pipeline (GPU) | `.venv` |
| `Docling` | Docling | Layout/table models (GPU) | `.venv` |
| `GraniteDocling` | Granite Docling | Single VLM via `docling` CLI (GPU) | `.venv` |
| `OpenDataLoader` | OpenDataLoader PDF | Rule-based, **no ML/GPU**, needs Java 11+ | `.venv` |

> **Rule-based vs ML:** OpenDataLoader only reads a PDF's existing text layer
> (very fast, but blank on scanned/image-only PDFs). The OCR/VLM tools render
> and read the pixels, so they handle scans — at much higher runtime cost.

## ⚠️ Two virtual environments are required

PaddleOCR (CUDA-11 / `nccl-cu11`) and the torch tools (CUDA-13 / `nccl-cu13`)
depend on **conflicting CUDA libraries and cannot coexist** in one environment.
So there are two venvs, each run with its own interpreter:

| Venv | Tools | Requirements file |
|------|-------|-------------------|
| `.venv` | MinerU, Docling, GraniteDocling, OpenDataLoader | `requirements-torch.txt` |
| `venv-paddle` | PaddleOCR15, PaddleOCR16 | `requirements-paddle.txt` |

You run the same `cli.py`, just with the matching interpreter
(`.venv/bin/python` vs `venv-paddle/bin/python`).

## Prerequisites

- **Python 3.11**
- **[`uv`](https://github.com/astral-sh/uv)** package manager
- **NVIDIA GPU** (~6 GB+) for the OCR/VLM tools (OpenDataLoader needs none)
- **Java 11+** — only for OpenDataLoader:
  ```bash
  sudo apt install -y openjdk-17-jre-headless
  sudo update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java
  java -version   # must show 11 or newer
  ```

## Setup

### 1. Torch venv (MinerU, Docling, GraniteDocling, OpenDataLoader)

```bash
uv venv .venv --python 3.11
VIRTUAL_ENV=.venv uv pip install -r requirements-torch.txt
```

### 2. Paddle venv (PaddleOCR-VL) — optional, only if you want PaddleOCR

```bash
uv venv venv-paddle --python 3.11
VIRTUAL_ENV=venv-paddle uv pip install -r requirements-paddle.txt
```

## Running

`cli.py` processes every `*.pdf` in `--input` (a file or a directory) with the
tools you list, and writes outputs under `--output` (default `./results`).

```bash
# Torch tools — point at a folder of PDFs
.venv/bin/python cli.py \
    --input /path/to/pdfs \
    --tools MinerU,Docling,GraniteDocling,OpenDataLoader \
    --output ./results

# A single tool, single file
.venv/bin/python cli.py --input mydoc.pdf --tools OpenDataLoader --output ./results

# PaddleOCR — MUST use the paddle interpreter
venv-paddle/bin/python cli.py --input /path/to/pdfs --tools PaddleOCR16 --output ./results
```

Useful flags:
- `--tools all` — every tool registered in the active venv
- `--recursive` — descend into subdirectories of `--input`

> **PATH note (MinerU / GraniteDocling / OpenDataLoader):** these shell out to
> CLIs/Java installed in the venv. Running `.venv/bin/python` directly does *not*
> put `.venv/bin` on `PATH`. If you hit `No such file or directory: 'mineru'`,
> either prepend the venv to PATH or activate it:
> ```bash
> PATH="$PWD/.venv/bin:$PATH" .venv/bin/python cli.py ...
> # or:  source .venv/bin/activate && python cli.py ...
> ```

## Output layout

```
results/
├── <document>/
│   └── <Tool>/
│       ├── <document>_direct.md     # tool's native markdown
│       └── <document>_json.json     # tool's structured JSON
├── summary.jsonl          # append-only log: one line per (document, tool) run
├── comparison_report.md   # auto-written by cli.py each run
└── analysis_report.md     # readable report (see below)
```

`summary.jsonl` accumulates across runs; reports **deduplicate by
(document, tool), keeping the latest** — so re-running one tool never wipes
another tool's earlier results.

## Analysis report

After running, regenerate the human-readable report (Overview, coverage matrix,
per-tool success rate, runtime charts, failures):

```bash
.venv/bin/python generate_report.py \
    --summary results/summary.jsonl \
    --output results/analysis_report.md
```

## Bounding-box annotations (PaddleOCR)

`annotate_bboxes.py` draws PaddleOCR's `parsing_res_list` boxes onto the source
PDF pages. Run it with the **paddle** interpreter:

```bash
venv-paddle/bin/python annotate_bboxes.py
```

## Project layout

```
adapters/        one adapter per tool (paddle_ocr, mineru, docling,
                 granite_docling, opendataloader); base.py defines the interface
cli.py           entry point: discovers PDFs, runs tools, writes outputs
generate_report.py   summary.jsonl -> analysis_report.md
utils/           config loading + ResultWriter (storage.py)
schema/          canonical document schema (markdown-from-JSON is deferred)
requirements*.txt    base + per-venv pinned dependencies
```

## Adding another tool

1. Create `adapters/<tool>.py` with a class extending `DocumentExtractor`
   (`adapters/base.py`); implement `run()` to return an `ExtractionResult`
   with `markdown_direct`, `json_output`, and `metadata` (include
   `runtime_seconds` and `pages`).
2. Export it from `adapters/__init__.py`.
3. Register it in `get_available_tools()` in `cli.py`.
4. Add its dependency to the matching `requirements-*.txt`.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `No such file or directory: 'mineru'` | venv `bin` not on PATH — see PATH note above |
| `libtorch_cuda.so: undefined symbol: ncclCommResume` | paddle was installed into the torch venv — keep the two venvs separate |
| OpenDataLoader fails / empty | Java missing or < 11 — install `openjdk-17-jre-headless` |
| CUDA out of memory | run fewer GPU tools at once; tools load models once and reuse them |
| OpenDataLoader output looks empty | the PDF is scanned/image-only (no text layer) — use an OCR/VLM tool instead |
```
