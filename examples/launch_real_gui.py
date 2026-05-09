"""Launch the cell sorter GUI with two same-day cellsets from the shared drive."""

from __future__ import annotations

from pathlib import Path

from calcium_imaging_cell_sorter import ReviewInputs, launch_review

DATA_DIR = Path(r"\\fileservices.ad.jyu.fi\CommonShare\psy-hica\Weiyong_Backup\CFC_Females\processed_data\000")

CELLSETS = [
    DATA_DIR / "2022-10-24-09-26-54_video-PP-BP-MC-cnmfe-cellset-0.75-10.isxd",
    DATA_DIR / "2022-10-24-10-16-38_video-PP-BP-MC-cnmfe-cellset-0.75-10.isxd",
]
MAXDFF = DATA_DIR / "day 5-maxdff.isxd"
OUTPUT = Path(__file__).resolve().parent / "000_day5_two_session_review.csv"


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
