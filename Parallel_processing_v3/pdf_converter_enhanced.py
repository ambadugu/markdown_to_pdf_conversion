#!/usr/bin/env python3
"""
PDF to Markdown Converter with Image Extraction and Embedding

This script recursively converts all PDF files in a source directory
to Markdown format using PyMuPDF (preferred) or markitdown (fallback),
while optionally extracting and embedding images.

Usage:
    python pdf_converter.py source_dir output_dir [--embed-images]
"""

import os
import logging
import argparse
import base64
from pathlib import Path
from typing import Optional

# PDF libraries
import fitz  # PyMuPDF
import markitdown

logging.basicConfig(level=logging.INFO)


class PDFConverter:
    """PDF to Markdown converter with image extraction capabilities"""
    
    def __init__(self, embed_images: bool = False, image_format: str = "png", dpi: int = 300):
        self.embed_images = embed_images
        self.image_format = image_format
        self.dpi = dpi


    def convert_pdf_with_pymupdf(self, pdf_path: Path, output_path: Path,
                                  image_folder: Optional[Path] = None) -> bool:
        try:
            logging.info(f"Converting with PyMuPDF: {pdf_path} -> {output_path}")
            doc = fitz.open(str(pdf_path))
            markdown_parts = []
            image_count = 0

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                markdown_parts.append(f"### Page {page_num}\n\n{text}\n")

                images = page.get_images(full=True)
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]

                    image_count += 1
                    image_filename = f"image_{page_num:03d}_{img_index+1:02d}.{img_ext}"

                    if self.embed_images:
                        encoded = base64.b64encode(img_bytes).decode()
                        markdown_parts.append(
                            f"![Image](data:image/{img_ext};base64,{encoded})\n"
                        )
                    else:
                        # Create images folder in the same directory as the markdown file
                        image_folder.mkdir(parents=True, exist_ok=True)
                        image_path = image_folder / image_filename
                        with open(image_path, "wb") as img_out:
                            img_out.write(img_bytes)
                        # Use relative path from markdown to images folder
                        rel_path = f"images/{image_filename}"
                        markdown_parts.append(f"![Image]({rel_path})\n")

            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write("\n".join(markdown_parts))

            logging.info(f"PyMuPDF converted {pdf_path.name} with {image_count} images.")
            doc.close()
            return True

        except Exception as e:
            logging.error(f"PyMuPDF failed on {pdf_path}: {e}")
            return False

    def convert_pdf_with_markitdown(self, pdf_path: Path, output_path: Path):
        logging.info(f"Converting with markitdown: {pdf_path} -> {output_path}")
        try:
            output = markitdown.convert(str(pdf_path))
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
            logging.info(f"Markitdown converted {pdf_path.name}")
        except Exception as e:
            logging.error(f"Markitdown failed on {pdf_path}: {e}")

    def process_pdf(self, pdf_path: Path, source_dir: Path, output_dir: Path):
        """Process a single PDF file"""
        relative_path = pdf_path.relative_to(source_dir)
        output_path = output_dir / relative_path.with_suffix(".md")

        # Create images folder in the same directory as the markdown file
        local_image_folder = None
        if not self.embed_images:
            local_image_folder = output_path.parent / "images"

        # Convert with PyMuPDF, fallback to markitdown
        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = self.convert_pdf_with_pymupdf(pdf_path, output_path,
                                               image_folder=local_image_folder)

        if not success:
            self.convert_pdf_with_markitdown(pdf_path, output_path)

    def process_directory(self, source_dir: Path, output_dir: Path):
        """Process all PDFs in a directory recursively"""
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_path = Path(root) / file
                    self.process_pdf(pdf_path, source_dir, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to Markdown converter with image extraction.")
    parser.add_argument("source_dir", type=Path, help="Source directory containing PDF files")
    parser.add_argument("output_dir", type=Path, help="Output directory for Markdown files")
    parser.add_argument("--embed-images", action="store_true", help="Embed images as base64 in Markdown")

    args = parser.parse_args()
    
    converter = PDFConverter(embed_images=args.embed_images)
    converter.process_directory(args.source_dir, args.output_dir)