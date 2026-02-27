# pyright: ignore[reportCallIssue=false]
import logging
import re
from typing import Final, TypedDict, cast

import cv2
import numpy as np
import pytesseract
from numpy.typing import NDArray
from PIL import Image

from deskar.models import (
    ALL_ALLOYS,
    ColumnCenter,
    DotPosition,
    ModelDimensions,
    ModelRow,
)

logger = logging.getLogger(__name__)

MODEL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{2,5}\d{6}[\w-]+$")
NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d+\.?\d*$")


def fix_numeric_value(value: str) -> str:
    value = value.strip()

    if not NUMBER_PATTERN.match(value):
        return value

    if "." in value:
        return value

    float_val = float(value)
    if float_val in (2, 4, 8, 12, 16, 24, 32):
        return str(float_val / 10)

    for divisor in (1000, 100, 10):
        result = float_val / divisor
        if 3 <= result <= 25:
            return str(round(result, 3))

    return value


class TesseractDict(TypedDict):
    level: list[str]
    page_num: list[str]
    block_num: list[str]
    par_num: list[str]
    line_num: list[str]
    word_num: list[str]
    left: list[str]
    top: list[str]
    width: list[str]
    height: list[str]
    conf: list[str]
    text: list[str]


class ImageProcessor:
    def __init__(
        self,
        max_column_distance: int = 25,
        max_row_distance: int = 40,
    ) -> None:
        self.max_column_distance = max_column_distance
        self.max_row_distance = max_row_distance

    def detect_column_centers(
        self,
        image: NDArray[np.uint8],
    ) -> tuple[list[ColumnCenter], int]:
        height, width = image.shape[:2]

        alloy_x_start = int(width * 0.62)
        alloy_x_end = width - 10
        header_y1 = int(height * 0.25)
        header_y2 = int(height * 0.38)
        header = image[header_y1:header_y2, alloy_x_start:alloy_x_end]
        header_rotated = cv2.rotate(header, cv2.ROTATE_90_CLOCKWISE)

        ocr_data = cast(
            TesseractDict,
            pytesseract.image_to_data(  # pyright: ignore[reportUnknownMemberType]
                Image.fromarray(header_rotated),
                lang="eng",
                config="--psm 11",
                output_type=pytesseract.Output.DICT,
            ),
        )

        detected_positions: dict[str, int] = {}
        for i, word in enumerate(ocr_data["text"]):
            match = re.search(r"(LF\d+)", word.strip())
            if match:
                code = match.group(1)
                top = int(ocr_data["top"][i])
                height = int(ocr_data["height"][i])
                center_y_rotated = top / height

                full_x = alloy_x_start + center_y_rotated
                detected_positions[code] = full_x

        num_alloys = len(ALL_ALLOYS)
        column_width = (alloy_x_end - alloy_x_start) / num_alloys

        results: list[ColumnCenter] = []
        for idx, alloy in enumerate(ALL_ALLOYS):
            x_pos = detected_positions.get(
                alloy.code, int(alloy_x_start + (idx + 0.5) * column_width)
            )
            results.append(ColumnCenter(alloy=alloy, x_position=x_pos))

        return results, alloy_x_start

    def detect_dots(
        self,
        image: NDArray[np.uint8],
        alloy_x_start: int,
        table_y_start: int,
        table_y_end: int,
    ) -> list[DotPosition]:
        section = image[table_y_start:table_y_end, alloy_x_start - 20 :]
        gray = cv2.cvtColor(section, cv2.COLOR_RGB2GRAY)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=15,
            param1=50,
            param2=18,
            minRadius=6,
            maxRadius=20,
        )

        dots: list[DotPosition] = []

        for cx, cy, radius in circles[0]:
            cx, cy, radius = int(cx), int(cy), int(radius)

            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.circle(mask, (cx, cy), max(1, radius - 3), 255, -1)

            mean_brightness = cv2.mean(gray, mask=mask)[0]

            if mean_brightness < 200:
                dots.append(
                    DotPosition(
                        x=cx + alloy_x_start - 20,
                        y=cy + table_y_start,
                    )
                )

        return dots

    def extract_model_rows(
        self,
        image: NDArray[np.uint8],
    ) -> tuple[list[ModelRow], int]:
        height, width = image.shape[:2]

        crop_x_end = int(width * 0.65)
        table_y_start = int(height * 0.35)
        crop = image[table_y_start : height - 50, 200:crop_x_end]

        ocr_data = cast(
            TesseractDict,
            pytesseract.image_to_data(  # pyright: ignore[reportUnknownMemberType]
                Image.fromarray(crop),
                lang="eng+rus",
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            ),
        )

        bands: dict[int, list[tuple[int, str]]] = {}

        for i, word in enumerate(ocr_data["text"]):
            word_str = word.strip()
            if not word_str:
                continue

            top = int(ocr_data["top"][i])
            height = int(ocr_data["height"][i])
            center_y = top + height // 2 + table_y_start
            x_pos = ocr_data["left"][i]

            band_y = next(
                (by for by in bands if abs(by - center_y) < 15),
                None,
            )

            if band_y is None:
                band_y = center_y
                bands[band_y] = []

            bands[band_y].append((x_pos, word_str))

        rows: list[ModelRow] = []

        for band_y, words in bands.items():
            sorted_words = sorted(words, key=lambda w: w[0])
            texts = [w[1] for w in sorted_words]
            model = next((t for t in texts if MODEL_PATTERN.match(t)), None)

            if not model:
                continue

            numbers = [t for t in texts if NUMBER_PATTERN.match(t)]
            dimension_keys = ["L", "IC", "S", "d", "r"]
            dimensions = ModelDimensions()

            for idx, key in enumerate(dimension_keys):
                if idx < len(numbers):
                    fixed_value = fix_numeric_value(numbers[idx])
                    setattr(dimensions, key, fixed_value)

            rows.append(
                ModelRow(
                    model=model,
                    y_position=band_y,
                    dimensions=dimensions,
                )
            )

        return rows, table_y_start

    def match_dots_to_records(
        self,
        dots: list[DotPosition],
        columns: list[ColumnCenter],
        rows: list[ModelRow],
    ) -> list[tuple[ModelRow, ColumnCenter]]:
        matched: list[tuple[ModelRow, ColumnCenter]] = []
        seen: set[tuple[str, str]] = set()

        for dot in dots:
            best_column = min(
                columns,
                key=lambda c: abs(c.x_position - dot.x),
            )

            if abs(best_column.x_position - dot.x) > self.max_column_distance:
                continue

            best_row = min(
                rows,
                key=lambda r: abs(r.y_position - dot.y),
            )

            if abs(best_row.y_position - dot.y) > self.max_row_distance:
                continue

            # Avoid duplicates
            key = (best_row.model, best_column.alloy.code)
            if key in seen:
                continue

            seen.add(key)
            matched.append((best_row, best_column))

        return matched
