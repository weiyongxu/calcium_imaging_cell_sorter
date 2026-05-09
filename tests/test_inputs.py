from __future__ import annotations

from pathlib import Path

from calcium_imaging_cell_sorter.inputs import ReviewInputs


def test_review_inputs_builds_paths_and_default_output():
    inputs = ReviewInputs.from_paths(
        ["C:/data/session-a.isxd", "C:/data/session-b.isxd"],
        maxdff_file="C:/data/day-5-maxdff.isxd",
        read_only=True,
    )

    assert inputs.cellset_files == (
        Path("C:/data/session-a.isxd"),
        Path("C:/data/session-b.isxd"),
    )
    assert inputs.maxdff_file == Path("C:/data/day-5-maxdff.isxd")
    assert inputs.read_only is True
    assert inputs.output_csv_path() == Path("C:/data/session-a-cell-status-review.csv")
