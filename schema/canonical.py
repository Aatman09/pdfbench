"""
Canonical document schema and normalization layer.

This module defines a standardized document representation that all tools
map to, and provides the JSON-to-Markdown conversion function.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class Block:
    """Represents a single content block within a page."""

    type: str  # 'heading', 'paragraph', 'list', 'table', 'figure', 'unknown'
    text: str = ""
    confidence: Optional[float] = None
    level: Optional[int] = None  # For headings (1-6)
    page_number: Optional[int] = None
    # Table-specific fields
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    # List-specific fields
    items: List[str] = field(default_factory=list)
    # Figure-specific fields
    image_url: Optional[str] = None
    caption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        result = {
            "type": self.type,
            "text": self.text,
            "confidence": self.confidence,
            "page_number": self.page_number,
        }
        if self.type == "heading":
            result["level"] = self.level
        elif self.type == "table":
            result["headers"] = self.headers
            result["rows"] = self.rows
        elif self.type == "list":
            result["items"] = self.items
        elif self.type == "figure":
            result["image_url"] = self.image_url
            result["caption"] = self.caption
        return result


@dataclass
class Page:
    """Represents a single page in the document."""

    page_number: int
    blocks: List[Block] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert page to dictionary."""
        return {
            "page_number": self.page_number,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class CanonicalDocument:
    """
    Canonical representation of a document.

    All tools map their outputs to this structure.
    """

    pages: List[Page] = field(default_factory=list)
    document_type: str = "unknown"
    source_file: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "document_type": self.document_type,
            "source_file": self.source_file,
            "metadata": self.metadata,
        }


def normalize_paddleocr_output(
    tool_name: str,
    raw_output: Dict[str, Any],
    input_path: str,
) -> CanonicalDocument:
    """
    Normalize PaddleOCR output to canonical schema.

    PaddleOCR returns a list of pages, each with text blocks and
    associated confidence scores.
    """
    doc = CanonicalDocument(source_file=input_path, document_type="document")
    doc.metadata["tool_name"] = tool_name

    pages_data = raw_output.get("pages", raw_output.get("predictions", []))

    for page_data in pages_data:
        page_num = page_data.get("page_number", page_data.get("page", 0))
        if isinstance(page_num, str):
            try:
                page_num = int(page_num)
            except ValueError:
                page_num = 0

        page = Page(page_number=page_num)

        # Process text blocks
        blocks = page_data.get("blocks", page_data.get("text_blocks", []))
        for block in blocks:
            canonical_block = Block(
                type="paragraph",
                text=block.get("text", ""),
                confidence=block.get("confidence"),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        # Process tables
        tables = page_data.get("tables", [])
        for table in tables:
            canonical_block = Block(
                type="table",
                headers=table.get("headers", []),
                rows=table.get("rows", []),
                confidence=table.get("confidence"),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        doc.pages.append(page)

    # Sort pages by page number
    doc.pages.sort(key=lambda p: p.page_number)

    return doc


def normalize_mineru_output(
    tool_name: str,
    raw_output: Dict[str, Any],
    input_path: str,
) -> CanonicalDocument:
    """
    Normalize MinerU output to canonical schema.

    MinerU returns a structure with 'content' containing pages,
    each with various block types including PDF pages, images, etc.
    """
    doc = CanonicalDocument(source_file=input_path, document_type="document")
    doc.metadata["tool_name"] = tool_name

    content = raw_output.get("content", raw_output)

    if isinstance(content, dict):
        pages_data = content.get("pages", [])
    elif isinstance(content, list):
        pages_data = content
    else:
        pages_data = []

    for idx, page_data in enumerate(pages_data):
        page_num = page_data.get("page_number", idx + 1)

        page = Page(page_number=page_num)

        # Process text blocks
        for item in page_data.get("text_blocks", []):
            block_type = item.get("type", "paragraph")
            if block_type == "title":
                block_type = "heading"

            canonical_block = Block(
                type=block_type,
                text=item.get("text", ""),
                confidence=item.get("score"),
                page_number=page_num,
                level=item.get("level"),
            )
            page.blocks.append(canonical_block)

        # Process tables
        for table in page_data.get("tables", []):
            canonical_block = Block(
                type="table",
                headers=table.get("headers", []),
                rows=table.get("rows", []),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        doc.pages.append(page)

    doc.pages.sort(key=lambda p: p.page_number)
    return doc


def normalize_docling_output(
    tool_name: str,
    raw_output: Dict[str, Any],
    input_path: str,
) -> CanonicalDocument:
    """
    Normalize Docling output to canonical schema.

    Docling returns a structured document with pages containing
    text blocks, tables, and figures.
    """
    doc = CanonicalDocument(source_file=input_path, document_type="document")
    doc.metadata["tool_name"] = tool_name

    # Docling uses 'pages' key
    pages_data = raw_output.get("pages", [])

    for page_data in pages_data:
        page_num = page_data.get("page_number", page_data.get("page_idx", 0) + 1)

        page = Page(page_number=page_num)

        # Process text blocks
        for text_block in page_data.get("text_blocks", []):
            canonical_block = Block(
                type="paragraph",
                text=text_block.get("text", ""),
                confidence=text_block.get("confidence"),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        # Process tables
        for table in page_data.get("tables", []):
            canonical_block = Block(
                type="table",
                headers=table.get("headers", []),
                rows=table.get("rows", []),
                confidence=table.get("confidence"),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        # Process figures
        for figure in page_data.get("figures", []):
            canonical_block = Block(
                type="figure",
                image_url=figure.get("image_url"),
                caption=figure.get("caption"),
                page_number=page_num,
            )
            page.blocks.append(canonical_block)

        doc.pages.append(page)

    doc.pages.sort(key=lambda p: p.page_number)
    return doc


def normalize_granite_docling_output(
    tool_name: str,
    raw_output: Dict[str, Any],
    input_path: str,
) -> CanonicalDocument:
    """
    Normalize Granite Docling output to canonical schema.

    Granite Docling uses similar structure to Docling but may have
    different field names.
    """
    # Granite Docling output is similar to Docling
    return normalize_docling_output(tool_name, raw_output, input_path)


def json_to_markdown(canonical_doc: CanonicalDocument) -> str:
    """
    Convert a canonical document to markdown.

    This function walks the canonical schema and produces deterministic
    markdown output. The conversion is identical for all tools.
    """
    lines = []

    for page in canonical_doc.pages:
        # Add page number as comment if there are multiple pages
        if len(canonical_doc.pages) > 1:
            lines.append(f"\n<!-- Page {page.page_number} -->\n")

        for block in page.blocks:
            if block.type == "heading":
                level = block.level or 1
                level = max(1, min(6, level))  # Clamp to valid range
                lines.append(f"{'#' * level} {block.text}\n")

            elif block.type == "paragraph":
                lines.append(f"{block.text}\n")

            elif block.type == "list":
                for item in block.items:
                    lines.append(f"- {item}\n")

            elif block.type == "table":
                if block.headers:
                    header_row = "| " + " | ".join(block.headers) + " |"
                    separator = "| " + " | ".join(["---"] * len(block.headers)) + " |"
                    lines.append(header_row)
                    lines.append(separator)
                    for row in block.rows:
                        lines.append("| " + " | ".join(row) + " |")
                else:
                    # Table without headers, render as plain rows
                    for row in block.rows:
                        lines.append("| " + " | ".join(row) + " |")

            elif block.type == "figure":
                if block.image_url:
                    lines.append(f"![Figure]({block.image_url})")
                if block.caption:
                    lines.append(f"*{block.caption}*\n")

            else:
                # Unknown type, just output text
                if block.text:
                    lines.append(f"{block.text}\n")

        # Add spacing between pages
        if page != canonical_doc.pages[-1]:
            lines.append("\n---\n")

    return "".join(lines)