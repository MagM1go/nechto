from dataclasses import dataclass, field
from enum import Enum
from typing import Final, NamedTuple, TypedDict


class AlloyGroup(str, Enum):
    P = "P"
    M = "M"
    K = "K"


@dataclass(frozen=True, slots=True)
class Alloy:
    code: str
    group: AlloyGroup

    def __post_init__(self) -> None:
        if not self.code.startswith("LF"):
            raise ValueError(f"Invalid alloy code format: {self.code}")


@dataclass(frozen=True, slots=True)
class ColumnCenter:
    alloy: Alloy
    x_position: int


@dataclass(frozen=True, slots=True)
class DotPosition:
    x: int
    y: int


@dataclass
class ModelDimensions:
    L: str = field(default="")
    IC: str = field(default="")
    S: str = field(default="")
    d: str = field(default="")
    r: str = field(default="")

    def to_dict(self) -> dict[str, str]:
        return {
            "L": self.L,
            "IC": self.IC,
            "S": self.S,
            "d": self.d,
            "r": self.r,
        }


@dataclass
class ModelRow:
    model: str
    y_position: int
    dimensions: ModelDimensions = field(default_factory=ModelDimensions)


@dataclass
class CatalogRecord:
    model: str
    dimensions: ModelDimensions
    alloy: str
    group: AlloyGroup

    def to_excel_row(self) -> list[str]:
        dims = self.dimensions.to_dict()
        return [
            self.model,
            dims["L"],
            dims["IC"],
            dims["S"],
            dims["d"],
            dims["r"],
            self.alloy if self.group == AlloyGroup.P else "",
            self.alloy if self.group == AlloyGroup.M else "",
            self.alloy if self.group == AlloyGroup.K else "",
        ]


class ProcessingResult(TypedDict):
    total_pages: int
    total_records: int
    pages_with_errors: list[int]
    processing_time_seconds: float


class PageProcessingStats(NamedTuple):
    page_number: int
    records_found: int
    cumulative_total: int


DEFAULT_DPI: Final[int] = 200
MAX_COLUMN_DISTANCE: Final[int] = 25
MAX_ROW_DISTANCE: Final[int] = 40

ALL_ALLOYS: Final[tuple[Alloy, ...]] = (
    Alloy("LF9008", AlloyGroup.P),
    Alloy("LF9018", AlloyGroup.P),
    Alloy("LF9028", AlloyGroup.P),
    Alloy("LF9218", AlloyGroup.P),
    Alloy("LF9118", AlloyGroup.P),
    Alloy("LF918", AlloyGroup.P),
    Alloy("LF6008", AlloyGroup.M),
    Alloy("LF6018", AlloyGroup.M),
    Alloy("LF6028", AlloyGroup.M),
    Alloy("LF6118", AlloyGroup.M),
    Alloy("LF618", AlloyGroup.M),
    Alloy("LF3018", AlloyGroup.K),
    Alloy("LF3028", AlloyGroup.K),
)

EXCEL_HEADERS: Final[tuple[str, ...]] = (
    "model",
    "L",
    "I.C",
    "S",
    "d",
    "r",
    "P",
    "M",
    "K",
)
EXCEL_COLUMN_WIDTHS: Final[tuple[int, ...]] = (22, 7, 8, 7, 7, 6, 10, 10, 10)
