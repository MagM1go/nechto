import logging
import time

import numpy as np
from numpy.typing import NDArray

from deskar.config import config
from deskar.excel_builder import ExcelBuilder
from deskar.image_processing import ImageProcessor
from deskar.models import (
    CatalogRecord,
    ProcessingResult,
)
from deskar.pdf_processor import PDFBatchProcessor

logger = logging.getLogger(__name__)


class CatalogProcessor:
    def __init__(self) -> None:
        self._image_processor = ImageProcessor(
            max_column_distance=config.max_column_distance,
            max_row_distance=config.max_row_distance,
        )
        self._pdf_processor = PDFBatchProcessor()

    def process_page(
        self,
        image: NDArray[np.uint8],
    ) -> list[CatalogRecord]:
        height = image.shape[0]
        columns, alloy_x_start = self._image_processor.detect_column_centers(image)
        rows, table_y_start = self._image_processor.extract_model_rows(image)

        if not rows:
            return []

        dots = self._image_processor.detect_dots(
            image,
            alloy_x_start,
            table_y_start,
            height - 50,
        )

        matched = self._image_processor.match_dots_to_records(
            dots,
            columns,
            rows,
        )

        records: list[CatalogRecord] = []
        for row, column in matched:
            record = CatalogRecord(
                model=row.model,
                dimensions=row.dimensions,
                alloy=column.alloy.code,
                group=column.alloy.group,
            )
            records.append(record)

        return records

    def process_all_pages(self) -> list[CatalogRecord]:
        all_records: list[CatalogRecord] = []
        page_count = 0
        error_pages: list[int] = []

        pdf_files = self._pdf_processor.get_pdf_files()
        total_pdfs = len(pdf_files)

        for pdf_idx, pdf_path in enumerate(pdf_files, start=1):
            logger.info(
                f"\n=== Processing PDF {pdf_idx}/{total_pdfs}: {pdf_path.name} ==="
            )

            try:
                for page_num, image in self._pdf_processor.pdf_processor.process_pdf(
                    pdf_path
                ):
                    page_count += 1

                    try:
                        records = self.process_page(image)
                        all_records.extend(records)

                        logger.info(
                            f"  [{page_num:3d}] +{len(records):3d} records  "
                            + f"(total: {len(all_records)})"
                        )

                    except Exception as e:
                        error_pages.append(page_num)
                        logger.warning(f"  [{page_num:3d}] Error: {e}")

            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {e}")

        if error_pages:
            logger.warning(f"\nPages with errors: {error_pages}")

        return all_records

    def run(self) -> ProcessingResult:
        start_time = time.time()
        config.ensure_output_dir()

        records = self.process_all_pages()
        builder = ExcelBuilder(config.output_file)
        record_count = builder.build_and_save(records)

        elapsed = time.time() - start_time

        return ProcessingResult(
            total_pages=self._count_total_pages(),
            total_records=record_count,
            pages_with_errors=[],
            processing_time_seconds=round(elapsed, 2),
        )

    def _count_total_pages(self) -> int:
        total = 0
        for pdf_path in self._pdf_processor.get_pdf_files():
            count = self._pdf_processor.pdf_processor.get_page_count(pdf_path)
            if count:
                total += count
        return total


def process_catalog() -> ProcessingResult:
    processor = CatalogProcessor()
    return processor.run()
