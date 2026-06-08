#!/usr/bin/env python3
"""
Annotate PaddleOCR-VL bounding boxes onto the source PDF pages.

Reads the JSON produced by the pipeline (results/<pdf>/<tool>/<pdf>_json.json),
renders each PDF page to an image matching the JSON's page width/height, and
draws every detected block's bounding box with its label and reading order.

Usage:
    python annotate_bboxes.py \
        --json "results/drylab/PaddleOCR_VL_1.6/drylab_json.json" \
        --pdf  "/home/aries/silvertouch/ocr/data/drylab.pdf" \
        --output ./annotated

Run it with the paddle venv (it has pypdfium2 + pillow):
    venv-paddle/bin/python annotate_bboxes.py ...
"""

import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

# A stable, readable color per block label. Anything not listed falls back to gray.
LABEL_COLORS = {
    "doc_title": (220, 20, 60),       # crimson
    "paragraph_title": (255, 140, 0), # dark orange
    "text": (30, 144, 255),           # dodger blue
    "image": (34, 139, 34),           # forest green
    "table": (148, 0, 211),           # violet
    "figure": (34, 139, 34),
    "figure_caption": (0, 139, 139),  # teal
    "table_caption": (0, 139, 139),
    "formula": (199, 21, 133),        # medium violet red
    "header": (105, 105, 105),
    "footer": (105, 105, 105),
    "reference": (139, 69, 19),       # saddle brown
}
DEFAULT_COLOR = (128, 128, 128)


def _unwrap_page(page_obj):
    """Pipeline JSON wraps each page as {"res": {...}}; return the inner dict."""
    if isinstance(page_obj, dict) and "res" in page_obj and isinstance(page_obj["res"], dict):
        return page_obj["res"]
    return page_obj


def _load_font(size):
    """Try a real TTF for crisp labels, else fall back to PIL's bitmap font."""
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_pdf_page(pdf, page_index, target_w, target_h):
    """Render a single PDF page to a PIL image sized to (target_w, target_h)."""
    page = pdf[page_index]
    page_w_pts = page.get_width()
    # Scale so the rendered bitmap width matches the JSON's page width.
    scale = target_w / page_w_pts if page_w_pts else 2.0
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil().convert("RGB")
    # Snap to the exact JSON dimensions so bbox coordinates line up perfectly.
    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.LANCZOS)
    return img


def annotate_page(img, blocks, font):
    """Draw every block's bbox + label/order onto a copy of img."""
    draw = ImageDraw.Draw(img)
    for blk in blocks:
        bbox = blk.get("block_bbox")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = (int(round(v)) for v in bbox)
        label = blk.get("block_label", "unknown")
        order = blk.get("block_order", "")
        color = LABEL_COLORS.get(label, DEFAULT_COLOR)

        # Box.
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        # Label tag with a filled background for readability.
        tag = f"{order}:{label}" if order != "" else label
        tb = draw.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ty = max(0, y1 - th - 4)
        draw.rectangle([x1, ty, x1 + tw + 6, ty + th + 4], fill=color)
        draw.text((x1 + 3, ty + 2), tag, fill=(255, 255, 255), font=font)
    return img


def main():
    ap = argparse.ArgumentParser(description="Annotate PaddleOCR-VL bounding boxes onto PDF pages")
    ap.add_argument("--json", required=True, help="Path to the *_json.json file from the pipeline")
    ap.add_argument("--pdf", required=True, help="Path to the source PDF")
    ap.add_argument("--output", default="./annotated", help="Output directory for annotated PNGs")
    args = ap.parse_args()

    json_path = Path(args.json)
    pdf_path = Path(args.pdf)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]

    pdf = pdfium.PdfDocument(str(pdf_path))
    stem = pdf_path.stem
    font = _load_font(18)

    saved = []
    for i, page_obj in enumerate(data):
        page = _unwrap_page(page_obj)
        width = page.get("width")
        height = page.get("height")
        page_index = page.get("page_index", i)
        # page_index can be 1-based; map to a valid 0-based pdfium index.
        pidx = page_index - 1 if isinstance(page_index, int) and page_index >= len(pdf) else page_index
        if not isinstance(pidx, int) or pidx < 0 or pidx >= len(pdf):
            pidx = i

        blocks = page.get("parsing_res_list", [])
        if not (width and height):
            print(f"  page {i}: missing width/height in JSON, skipping")
            continue

        img = render_pdf_page(pdf, pidx, int(width), int(height))
        annotate_page(img, blocks, font)
        out_path = out_dir / f"{stem}_page{i + 1}_annotated.png"
        img.save(out_path)
        saved.append(out_path)
        print(f"  page {i + 1}: {len(blocks)} boxes -> {out_path}")

    pdf.close()
    print(f"\nDone. {len(saved)} annotated image(s) written to {out_dir}/")


if __name__ == "__main__":
    main()
