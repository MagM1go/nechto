import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from pdf2image import convert_from_path
from PIL import Image

from deskar.config import config

logger = logging.getLogger(__name__)


class PDFProcessor:
    def load_pdf(self, pdf_path: Path) -> list[Image.Image]:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise ValueError(f"File is not a PDF: {pdf_path}")

        logger.info(f"Loading PDF: {pdf_path}")

        pages = convert_from_path(
            pdf_path,
            dpi=config.dpi,
        )

        logger.info(f"Loaded {len(pages)} pages from {pdf_path.name}")
        return pages

    def process_pdf(
        self,
        pdf_path: Path,
    ) -> Iterator[tuple[int, NDArray[np.uint8]]]:
        pages = self.load_pdf(pdf_path)

        for page_num, page_image in enumerate(pages, start=1):
            image_array = np.array(page_image)
            yield page_num, image_array

            page_image.close()

    def get_page_count(self, pdf_path: Path) -> int | None:
        try:
            pages = self.load_pdf(pdf_path)
            count = len(pages)

            for page in pages:
                page.close()
            return count
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return None


class PDFBatchProcessor:
    def __init__(self) -> None:
        self.pdf_processor = PDFProcessor()

    def get_pdf_files(self) -> list[Path]:
        return config.get_pdf_files()

    def process_all_pdfs(
        self,
    ) -> Iterator[tuple[Path, int, NDArray[np.uint8]]]:
        pdf_files = self.get_pdf_files()

        if not pdf_files:
            logger.warning(f"No PDF files found in {config.input_path}")
            return

        logger.info(f"Found {len(pdf_files)} PDF file(s) to process")

        for pdf_path in pdf_files:
            logger.info(f"Processing: {pdf_path.name}")

            for page_num, image_array in self.pdf_processor.process_pdf(pdf_path):
                yield pdf_path, page_num, image_array
