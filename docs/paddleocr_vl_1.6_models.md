# PaddleOCR-VL 1.6 Pipeline — Internal Models

## Architecture Overview

Unlike **PPStructureV3** which uses **17+ specialized models** in a modular pipeline, **PaddleOCR-VL 1.6** uses a fundamentally different **2-stage architecture**: a layout detector feeds regions into a single Vision-Language Model (VLM) that handles text, tables, formulas, charts, and seals all in one shot.

```
Input Document Image
        │
        ▼
┌─────────────────────────────────┐
│  DocPreprocessor (optional)     │
│  ┌───────────────────────────┐  │
│  │ PP-LCNet_x1_0_doc_ori    │  │  ← Orientation Classification
│  │ UVDoc                    │  │  ← Document Unwarping
│  └───────────────────────────┘  │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  PP-DocLayoutV3                 │  ← Layout Detection (Stage 1)
│  (instance segmentation-based)  │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  PaddleOCR-VL-1.6-0.9B         │  ← Vision-Language Model (Stage 2)
│  (NaViT encoder + ERNIE-4.5)   │
│                                 │
│  Handles ALL of:                │
│   • Text recognition (100+ langs)│
│   • Table structure             │
│   • Formula → LaTeX             │
│   • Chart → Table               │
│   • Seal/stamp text             │
└─────────────────────────────────┘
        │
        ▼
  Structured Output (Markdown / JSON)
```

## Models Used in PaddleOCR-VL 1.6

| # | Model Name | Role | Description |
|---|-----------|------|-------------|
| 1 | **PP-DocLayoutV3** | Layout Detection | Instance-segmentation-based layout detector. Identifies document regions (text, tables, charts, figures, formulas, seals, headers, footers, etc.) with multi-point bounding boxes. Handles warped/curved/skewed documents. |
| 2 | **PaddleOCR-VL-1.6-0.9B** | Vision-Language Recognition (core) | 0.9B-parameter VLM integrating a NaViT-style dynamic-resolution visual encoder + ERNIE-4.5-0.3B language model. Recognizes text, tables, formulas, charts, and seals across 100+ languages. This single model replaces the many specialized models used in PPStructureV3. |
| 3 | **PP-LCNet_x1_0_doc_ori** | Document Orientation Classification | Lightweight classifier detecting document orientation (0°, 90°, 180°, 270°). Part of the `DocPreprocessor` sub-pipeline. *(Optional, off by default)* |
| 4 | **UVDoc** | Document Unwarping | Corrects perspective distortion, warping, and curvature in scanned/photographed documents. Part of the `DocPreprocessor` sub-pipeline. *(Optional, off by default)* |

**That's it — only 4 models** (2 core + 2 optional preprocessing). The VLM (`PaddleOCR-VL-1.6-0.9B`) replaces the ~13 specialized models that PPStructureV3 uses for text detection, text recognition, table structure, formula recognition, chart parsing, etc.

## Optional Feature Flags

The pipeline has boolean toggles that don't add new models but change how the existing models are used:

| Flag | Default | Effect |
|------|---------|--------|
| `use_doc_preprocessor` | `False` | Enables PP-LCNet_x1_0_doc_ori + UVDoc preprocessing |
| `use_layout_detection` | `True` | Enables PP-DocLayoutV3 layout analysis |
| `use_chart_recognition` | `False` | Routes chart regions to VLM for chart→table conversion |
| `use_seal_recognition` | `False` | Routes seal regions to VLM for seal text extraction |
| `use_ocr_for_image_block` | — | Uses VLM to OCR image blocks |
| `merge_layout_blocks` | `True` | Merges adjacent layout blocks for better reading order |

**NOTE:** When `use_seal_recognition` or `use_chart_recognition` are enabled, the **same VLM** (`PaddleOCR-VL-1.6-0.9B`) handles them — no additional models are loaded. This is the key difference from PPStructureV3, which uses `PP-Chart2Table`, `PP-OCRv4_server_seal_det`, etc.

## PPStructureV3 vs PaddleOCR-VL 1.6 — Model Comparison

| Task | PPStructureV3 Models | PaddleOCR-VL 1.6 Models |
|------|---------------------|------------------------|
| Doc preprocessing | UVDoc, PP-LCNet_x1_0_doc_ori | UVDoc, PP-LCNet_x1_0_doc_ori |
| Layout detection | PP-DocLayout_plus-L, PP-DocBlockLayout | **PP-DocLayoutV3** |
| Text detection | PP-OCRv5_mobile_det / server_det | *VLM handles this* |
| Text recognition | PP-OCRv5_mobile_rec / server_rec / en_rec | *VLM handles this* |
| Text orientation | PP-LCNet_x1_0_textline_ori | *VLM handles this* |
| Table classification | PP-LCNet_x1_0_table_cls | *VLM handles this* |
| Table structure | SLANet_plus, SLANeXt_wired | *VLM handles this* |
| Table cell detection | RT-DETR-L (wired + wireless) | *VLM handles this* |
| Formula recognition | PP-FormulaNet_plus-L | *VLM handles this* |
| Chart recognition | PP-Chart2Table | *VLM handles this* |
| Seal detection | PP-OCRv4_server_seal_det | *VLM handles this* |
| **Total models** | **17+** | **4** (2 core + 2 optional) |

## How to Extract the Models Yourself

### Method 1: Python API (Recommended)

```python
from paddleocr import PaddleOCRVL
import yaml

# Initialize with ALL features enabled to see every model
pipeline = PaddleOCRVL(
    pipeline_version="v1.6",
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_layout_detection=True,
    use_chart_recognition=True,
    use_seal_recognition=True,
)

# Export config to YAML
pipeline.export_paddlex_config_to_yaml("paddleocr_vl_1.6_config.yaml")

# Parse and print all model_name entries
with open("paddleocr_vl_1.6_config.yaml") as f:
    config = yaml.safe_load(f)

def find_models(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{path}.{k}" if path else k
            if k == "model_name":
                print(f"  {p}: {v}")
            else:
                find_models(v, p)

find_models(config)
```

### Method 2: PaddleX CLI

```bash
# Get the default config file
paddlex --get_pipeline_config PaddleOCR-VL-1.6

# Then grep for model names
grep "model_name" PaddleOCR-VL-1.6.yaml
```

### Method 3: Check the deployment configs in the repo

```bash
# These are in the PaddleOCR GitHub repo:
# deploy/paddleocr_vl_docker/pipeline_config_vllm.yaml
# deploy/paddleocr_vl_docker/pipeline_config_fastdeploy.yaml
```

## Pipeline Config Structure (from `pipeline_config_vllm.yaml`)

```yaml
pipeline_name: PaddleOCR-VL-1.6
batch_size: 64

use_doc_preprocessor: False     # Set True to enable UVDoc + PP-LCNet
use_layout_detection: True
use_chart_recognition: False    # VLM handles charts when True
use_seal_recognition: False     # VLM handles seals when True

SubModules:
  LayoutDetection:
    module_name: layout_detection
    model_name: PP-DocLayoutV3         # ← Model 1
    batch_size: 8
    threshold: 0.3
    layout_nms: True

  VLRecognition:
    module_name: vl_recognition
    model_name: PaddleOCR-VL-1.6-0.9B  # ← Model 2 (the VLM)
    genai_config:
      backend: vllm                     # or native, sglang-server, etc.

SubPipelines:
  DocPreprocessor:
    pipeline_name: doc_preprocessor
    SubModules:
      DocOrientationClassify:
        module_name: doc_text_orientation
        model_name: PP-LCNet_x1_0_doc_ori  # ← Model 3 (optional)
      DocUnwarping:
        module_name: image_unwarping
        model_name: UVDoc                   # ← Model 4 (optional)
```
