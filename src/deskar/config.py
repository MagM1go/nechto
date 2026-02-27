from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

from deskar.models import DEFAULT_DPI, MAX_COLUMN_DISTANCE, MAX_ROW_DISTANCE


@dataclass
class Config:
    input_dir: Path = Path("input")
    output_dir: Path = Path("output")

    dpi: int = DEFAULT_DPI
    max_column_distance: int = MAX_COLUMN_DISTANCE
    max_row_distance: int = MAX_ROW_DISTANCE

    output_filename: str = "deskar_catalog.xlsx"

    verbose: bool = False

    @property
    def input_path(self) -> Path:
        return self.input_dir.resolve()

    @property
    def output_path(self) -> Path:
        return self.output_dir.resolve()

    @property
    def output_file(self) -> Path:
        return self.output_path / self.output_filename

    def get_pdf_files(self) -> list[Path]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_path}")

        pdf_files = sorted(self.input_path.glob("*.pdf"))
        return pdf_files

    def ensure_output_dir(self) -> None:
        self.output_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        return cls(
            input_dir=Path(data.get("input_dir", "input")),
            output_dir=Path(data.get("output_dir", "output")),
            dpi=data.get("dpi", DEFAULT_DPI),
            max_column_distance=data.get("max_column_distance", MAX_COLUMN_DISTANCE),
            max_row_distance=data.get("max_row_distance", MAX_ROW_DISTANCE),
            output_filename=data.get("output_filename", "deskar_catalog.xlsx"),
            verbose=data.get("verbose", False),
        )

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        if overrides.get("input_dir") is not None:
            value = overrides["input_dir"]
            self.input_dir = Path(value) if isinstance(value, str) else value

        if overrides.get("output_dir") is not None:
            value = overrides["output_dir"]
            self.output_dir = Path(value) if isinstance(value, str) else value

        if overrides.get("dpi") is not None:
            self.dpi = int(overrides["dpi"])

        if overrides.get("max_column_distance") is not None:
            self.max_column_distance = int(overrides["max_column_distance"])

        if overrides.get("max_row_distance") is not None:
            self.max_row_distance = int(overrides["max_row_distance"])

        if overrides.get("output_filename") is not None:
            self.output_filename = str(overrides["output_filename"])

        if overrides.get("verbose") is not None:
            self.verbose = bool(overrides["verbose"])

    def merge_with(self, overrides: dict[str, Any]) -> "Config":
        current = {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "dpi": self.dpi,
            "max_column_distance": self.max_column_distance,
            "max_row_distance": self.max_row_distance,
            "output_filename": self.output_filename,
            "verbose": self.verbose,
        }

        for key, value in overrides.items():
            if value is not None:
                current[key] = value

        return Config.from_dict(current)

    @override
    def __repr__(self) -> str:
        return (
            f"Config(\n"
            f"  input_dir={self.input_dir!r},\n"
            f"  output_dir={self.output_dir!r},\n"
            f"  dpi={self.dpi},\n"
            f"  max_column_distance={self.max_column_distance},\n"
            f"  max_row_distance={self.max_row_distance},\n"
            f"  output_filename={self.output_filename!r},\n"
            f"  verbose={self.verbose}\n"
            f")"
        )


config = Config()
