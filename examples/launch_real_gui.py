"""Launch the cell sorter GUI with two same-day cellsets from the shared drive."""

from __future__ import annotations

from pathlib import Path

from calcium_imaging_cell_sorter import ReviewInputs, launch_review

# Replace this with the path to your actual data directory
DATA_DIR = Path(r"C:\path\to\your\data")

CELLSETS = [
    DATA_DIR / "session-1-cellset.isxd",
    DATA_DIR / "session-2-cellset.isxd",
]
MAXDFF = DATA_DIR / "matching-maxdff.isxd"
OUTPUT = Path(__file__).resolve().parent / "review_output.csv"


def main() -> int:
    missing = [p for p in [*CELLSETS, MAXDFF] if not p.exists()]
    if missing:
        raise SystemExit("Data files not found:\n" + "\n".join(str(p) for p in missing))

    return launch_review(
        inputs=ReviewInputs.from_paths(
            CELLSETS,
            maxdff_file=MAXDFF,
            output_csv=OUTPUT,
            read_only=True,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
