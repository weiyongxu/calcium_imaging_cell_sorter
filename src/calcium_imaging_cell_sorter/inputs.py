from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewInputs:
    """Simple schema for launching a review from another Python script."""

    cellset_files: tuple[Path, ...]
    maxdff_file: Path | None = None
    output_csv: Path | None = None
    read_only: bool = False

    def __post_init__(self) -> None:
        if not self.cellset_files:
            raise ValueError("At least one cellset file is required.")

    @classmethod
    def from_paths(
        cls,
        cellset_files: list[str | Path] | tuple[str | Path, ...],
        *,
        maxdff_file: str | Path | None = None,
        output_csv: str | Path | None = None,
        read_only: bool = False,
    ) -> "ReviewInputs":
        return cls(
            cellset_files=tuple(Path(path) for path in cellset_files),
            maxdff_file=Path(maxdff_file) if maxdff_file is not None else None,
            output_csv=Path(output_csv) if output_csv is not None else None,
            read_only=read_only,
        )

    def output_csv_path(self) -> Path:
        if self.output_csv is not None:
            return self.output_csv
        first_cellset = self.cellset_files[0]
        return first_cellset.with_name(first_cellset.stem + "-cell-status-review.csv")
