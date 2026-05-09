from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from calcium_imaging_cell_sorter.isxd_adapter import (
    _validate_cellset_collection,
    _validate_maxdff_compatibility,
)


@dataclass
class FakeSpacing:
    num_pixels: tuple[int, int]


@dataclass
class FakeImage:
    spacing: FakeSpacing


class FakeCellSet:
    def __init__(
        self,
        *,
        session_name: str,
        num_cells: int = 3,
        num_pixels: tuple[int, int] = (194, 316),
        cell_names: tuple[str, ...] = ("C000", "C001", "C002"),
    ) -> None:
        self.num_cells = num_cells
        self.spacing = FakeSpacing(num_pixels)
        self._cell_names = cell_names
        self._info = {"Session Name": session_name}

    def get_acquisition_info(self) -> dict[str, object]:
        return dict(self._info)

    def get_cell_name(self, index: int) -> str:
        return self._cell_names[index]


def test_validate_cellset_collection_rejects_mismatched_cell_counts():
    cellsets = [
        FakeCellSet(session_name="project_d5_a", num_cells=3),
        FakeCellSet(session_name="project_d5_b", num_cells=4, cell_names=("C000", "C001", "C002", "C003")),
    ]

    with pytest.raises(ValueError, match="same number of cells"):
        _validate_cellset_collection(cellsets, [Path("a.isxd"), Path("b.isxd")])


def test_validate_cellset_collection_rejects_mismatched_cell_names():
    cellsets = [
        FakeCellSet(session_name="project_d5_a"),
        FakeCellSet(session_name="project_d5_b", cell_names=("C000", "C009", "C002")),
    ]

    with pytest.raises(ValueError, match="same identified cells"):
        _validate_cellset_collection(cellsets, [Path("a.isxd"), Path("b.isxd")])


def test_validate_maxdff_compatibility_rejects_mismatched_spacing():
    cellset = FakeCellSet(session_name="project_d5_a")

    with pytest.raises(ValueError, match="same field of view"):
        _validate_maxdff_compatibility(
            [cellset],
            [Path("session-cellset.isxd")],
            Path("day 5-maxdff.isxd"),
            FakeImage(FakeSpacing((128, 128))),
        )


def test_validate_maxdff_compatibility_rejects_mismatched_day_when_available():
    cellset = FakeCellSet(session_name="project_d5_a")

    with pytest.raises(ValueError, match="does not match the cellset day"):
        _validate_maxdff_compatibility(
            [cellset],
            [Path("session-cellset.isxd")],
            Path("day 6-maxdff.isxd"),
            FakeImage(FakeSpacing((194, 316))),
        )
