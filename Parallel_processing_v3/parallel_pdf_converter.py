#!/usr/bin/env python3
"""
Parallel PDF to Markdown Converter Wrapper

This script processes multiple PDF files in parallel using the PDFConverter class.

Usage:
    python parallel_pdf_converter.py source_dir output_dir [--embed-images] [--workers N]
"""

import logging
import argparse
import multiprocessing as mp
from pathlib import Path
from typing import List, Tuple

# Import our PDF converter class
from pdf_converter import PDFConverter

# Configure logging for multiprocessing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
)


def process_single_pdf(pdf_info: Tuple[Path, Path, Path, bool]) -> bool:
    """Process a single PDF file - worker function for multiprocessing"""
    pdf_path, source_dir, output_dir, embed_images = pdf_info
    
    try:
        # Create converter instance for this worker
        converter = PDFConverter(embed_images=embed_images)
        converter.process_pdf(pdf_path, source_dir, output_dir)
        return True
        
    except Exception as e:
        logging.error(f"Failed to process {pdf_path}: {e}")
        return False


def collect_pdf_files(source_dir: Path) -> List[Path]:
    """Collect all PDF files from the source directory recursively"""
    pdf_files = []
    for pdf_path in source_dir.rglob("*.pdf"):
        pdf_files.append(pdf_path)
    return pdf_files


def process_pdfs_parallel(source_dir: Path, output_dir: Path, 
                         embed_images: bool, num_workers: int = None):
    """Process PDFs in parallel using multiprocessing"""
    
    # Collect all PDF files
    pdf_files = collect_pdf_files(source_dir)
    total_files = len(pdf_files)
    
    if total_files == 0:
        logging.info("No PDF files found in source directory")
        return
    
    logging.info(f"Found {total_files} PDF files to process")
    
    # Determine number of workers
    if num_workers is None:
        num_workers = min(mp.cpu_count(), total_files)
    
    logging.info(f"Using {num_workers} worker processes")
    
    # Prepare arguments for worker processes
    pdf_info_list = [
        (pdf_path, source_dir, output_dir, embed_images)
        for pdf_path in pdf_files
    ]
    
    # Process files in parallel
    with mp.Pool(processes=num_workers) as pool:
        try:
            results = pool.map(process_single_pdf, pdf_info_list)
            successful = sum(results)
            logging.info(f"Successfully processed {successful}/{total_files} PDF files")
            
        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
            pool.terminate()
            pool.join()
        except Exception as e:
            logging.error(f"Error in parallel processing: {e}")
            pool.terminate()
            pool.join()


def estimate_optimal_workers(memory_gb: int = 128, cpu_cores: int = 12) -> int:
    """
    Estimate optimal number of worker processes based on system resources.
    
    PDF processing is primarily CPU-intensive with moderate memory usage.
    Each worker might use 100-500MB of RAM depending on PDF size and complexity.
    """
    # Conservative memory estimate: 400MB per worker process
    memory_based_limit = (memory_gb * 1024) // 400  # Convert GB to MB, divide by 400MB
    
    # CPU-based limit: typically 1-2x CPU cores for CPU-intensive tasks
    cpu_based_limit = int(cpu_cores * 1.5)
    
    # Take the minimum to avoid resource exhaustion
    optimal = min(memory_based_limit, cpu_based_limit, 32)  # Cap at 32 processes
    
    return max(1, optimal)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parallel PDF to Markdown converter with image extraction."
    )
    parser.add_argument("source_dir", type=Path, 
                       help="Source directory containing PDF files")
    parser.add_argument("output_dir", type=Path, 
                       help="Output directory for Markdown files")
    parser.add_argument("--embed-images", action="store_true", 
                       help="Embed images as base64 in Markdown")
    parser.add_argument("--workers", type=int, default=None,
                       help="Number of worker processes (default: auto-detect)")
    parser.add_argument("--estimate-workers", action="store_true",
                       help="Show estimated optimal worker count and exit")

    args = parser.parse_args()
    
    if args.estimate_workers:
        # For M4 Max: 12 CPU cores, 128GB RAM
        optimal = estimate_optimal_workers(memory_gb=128, cpu_cores=12)
        print(f"Estimated optimal worker processes for M4 Max (128GB RAM, 12 cores): {optimal}")
        print(f"Conservative recommendation: {optimal // 2}")
        print(f"Aggressive recommendation: {optimal}")
        exit(0)
    
    source_dir = args.source_dir
    output_dir = args.output_dir
    embed_images = args.embed_images
    num_workers = args.workers
    
    if not source_dir.exists():
        logging.error(f"Source directory does not exist: {source_dir}")
        exit(1)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    process_pdfs_parallel(source_dir, output_dir, embed_images, num_workers)