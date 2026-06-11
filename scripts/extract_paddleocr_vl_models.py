"""
Extract the list of models used internally by the PaddleOCR-VL 1.6 pipeline.

This script initializes the PaddleOCR-VL pipeline with ALL optional features enabled,
exports the full config to YAML, and then parses + prints every model_name found.

Requirements:
    pip install "paddleocr[doc-parser]>=3.6.0" paddlepaddle>=3.2.1

Usage:
    python extract_paddleocr_vl_models.py
"""

import yaml
import os
import tempfile


def extract_models_from_config(config, path=""):
    """Recursively walk a parsed YAML config dict and collect all model_name values."""
    models = []
    if isinstance(config, dict):
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            if key == "model_name" and isinstance(value, str):
                models.append((path, value))
            else:
                models.extend(extract_models_from_config(value, current_path))
    elif isinstance(config, list):
        for i, item in enumerate(config):
            models.extend(extract_models_from_config(item, f"{path}[{i}]"))
    return models


def method_1_export_yaml():
    """
    Method 1: Initialize PaddleOCRVL with ALL features enabled, export config, parse it.
    This gives you the ACTUAL models the pipeline will use at runtime.
    """
    print("=" * 70)
    print("METHOD 1: Export config from initialized PaddleOCRVL pipeline")
    print("=" * 70)

    try:
        from paddleocr import PaddleOCRVL
    except ImportError:
        print("ERROR: paddleocr not installed. Install with:")
        print('  pip install "paddleocr[doc-parser]>=3.6.0"')
        return

    # Initialize with ALL optional features turned ON so we see every model
    pipeline = PaddleOCRVL(
        pipeline_version="v1.6",
        use_doc_orientation_classify=True,
        use_doc_unwarping=True,
        use_layout_detection=True,
        use_chart_recognition=True,
        use_seal_recognition=True,
    )

    # Export the full pipeline config to a temp YAML file
    config_path = os.path.join(tempfile.gettempdir(), "paddleocr_vl_1.6_config.yaml")
    pipeline.export_paddlex_config_to_yaml(config_path)
    print(f"\nExported config to: {config_path}\n")

    # Read and parse the YAML
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Print the raw YAML for inspection
    print("--- Full Pipeline Config ---")
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True))
    print("----------------------------\n")

    # Extract all model names
    models = extract_models_from_config(config)
    print(f"Found {len(models)} model(s) in the pipeline:\n")
    print(f"{'Section':<60} {'Model Name'}")
    print("-" * 90)
    for section, model_name in models:
        print(f"{section:<60} {model_name}")

    return config_path


def method_2_paddlex_cli():
    """
    Method 2: Use PaddleX CLI to get the default pipeline config.
    Run this in your terminal:
        paddlex --get_pipeline_config PaddleOCR-VL-1.6
    """
    print("\n" + "=" * 70)
    print("METHOD 2: PaddleX CLI command")
    print("=" * 70)
    print("""
Run this command in your terminal to get the default config:

    paddlex --get_pipeline_config PaddleOCR-VL-1.6

Or for a specific save location:

    paddlex --get_pipeline_config PaddleOCR-VL-1.6 --save_path ./my_config.yaml

Then inspect the YAML file to see all model_name entries.
""")


def method_3_parse_existing_yaml(yaml_path=None):
    """
    Method 3: Parse an existing YAML config file (e.g., from the PaddleOCR repo).
    """
    if yaml_path is None:
        print("\n" + "=" * 70)
        print("METHOD 3: Parse an existing YAML config")
        print("=" * 70)
        print("Pass a YAML file path to this function to extract model names.")
        print("Example YAML files from the PaddleOCR repo:")
        print("  deploy/paddleocr_vl_docker/pipeline_config_vllm.yaml")
        print("  deploy/paddleocr_vl_docker/pipeline_config_fastdeploy.yaml")
        return

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    models = extract_models_from_config(config)
    print(f"\nModels found in {yaml_path}:")
    for section, model_name in models:
        print(f"  [{section}] -> {model_name}")


if __name__ == "__main__":
    print("PaddleOCR-VL 1.6 Pipeline Model Extractor")
    print("=" * 70)
    print()

    # Try Method 1 first (requires paddleocr installed)
    try:
        method_1_export_yaml()
    except Exception as e:
        print(f"Method 1 failed: {e}")
        print("This is expected if paddleocr is not installed or GPU is not available.")

    # Show Method 2 instructions
    method_2_paddlex_cli()

    # Show Method 3 instructions
    method_3_parse_existing_yaml()
