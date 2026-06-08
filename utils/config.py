"""
Configuration management for the document extraction pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Configuration for the pipeline."""

    # Output directory
    output_dir: str = "./results"

    # Tools to run
    tools: List[str] = field(default_factory=lambda: [
        "PaddleOCR15",
        "PaddleOCR16",
        "MinerU",
        "Docling",
        "GraniteDocling"
    ])

    # Timeout for each tool (seconds)
    timeout: int = 300

    # Number of retries for failed tools
    retries: int = 2

    # Logging level
    log_level: str = "INFO"

    # Specific tool configurations
    paddle_ocr_version: str = "1.6"
    mineru_path: str = "mineru"
    docling_path: str = "docling"

    def __post_init__(self):
        """Validate configuration."""
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file or environment.

    Priority:
    1. Explicit config file path
    2. Environment variable DOC_EXTRACTION_CONFIG
    3. Default config
    """
    if config_path:
        import yaml
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return Config(**data)

    config_env = os.getenv("DOC_EXTRACTION_CONFIG")
    if config_env and os.path.exists(config_env):
        import yaml
        with open(config_env, "r") as f:
            data = yaml.safe_load(f)
        return Config(**data)

    # Return default config
    return Config()


def get_config_dict(config: Config) -> Dict[str, Any]:
    """Convert config to dictionary."""
    return {
        "output_dir": config.output_dir,
        "tools": config.tools,
        "timeout": config.timeout,
        "retries": config.retries,
        "log_level": config.log_level,
        "paddle_ocr_version": config.paddle_ocr_version,
        "mineru_path": config.mineru_path,
        "docling_path": config.docling_path,
    }