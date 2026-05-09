from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


VALID_STATUSES = ("accepted", "rejected", "undecided")


@dataclass
class ReviewState:
    """In-memory review state independent of any GUI toolkit."""

    cellset_files: tuple[Path, ...]
    maxdff_file: Path
    maxdff_image: np.ndarray
    cell_images: list[np.ndarray]
    traces_by_cell: list[list[np.ndarray]]
    num_samples: list[int]
    original_statuses: tuple[str, ...]
    statuses: list[str]
    current_index: int = 0
    _trace_cache: dict[int, np.ndarray] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.validate()

    @property
    def num_cells(self) -> int:
        return len(self.statuses)

    @property
    def current_cell_number(self) -> int:
        return self.current_index + 1

    @property
    def current_status(self) -> str:
        return self.statuses[self.current_index]

    def validate(self) -> None:
        if not self.cellset_files:
            raise ValueError("At least one cellset file is required.")
        if not self.statuses:
            raise ValueError("At least one cell is required.")
        expected_cells = len(self.statuses)
        if len(self.original_statuses) != expected_cells:
            raise ValueError("Original status count must match current status count.")
        if len(self.cell_images) != expected_cells:
            raise ValueError("Cell image count must match cell status count.")
        if len(self.traces_by_cell) != expected_cells:
            raise ValueError("Trace count must match cell status count.")
        if any(status not in VALID_STATUSES for status in self.statuses):
            raise ValueError(f"Statuses must be one of: {', '.join(VALID_STATUSES)}.")
        if any(status not in VALID_STATUSES for status in self.original_statuses):
            raise ValueError(f"Original statuses must be one of: {', '.join(VALID_STATUSES)}.")
        if self.current_index < 0 or self.current_index >= expected_cells:
            raise ValueError("Current cell index is outside the available cell range.")
        for cell_traces in self.traces_by_cell:
            if len(cell_traces) != len(self.cellset_files):
                raise ValueError("Each cell must have one trace per selected cellset.")
        if len(self.num_samples) != len(self.cellset_files):
            raise ValueError("Number of sample counts must match selected cellsets.")

    def status_counts(self) -> dict[str, int]:
        return {status: self.statuses.count(status) for status in VALID_STATUSES}

    def changed_count(self) -> int:
        return sum(
            1
            for original, current in zip(self.original_statuses, self.statuses)
            if original != current
        )

    def set_status(self, status: str, *, advance: bool = True) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Unknown cell status: {status}")
        self.statuses[self.current_index] = status
        if advance:
            self.next_cell(clamp_at_end=True)

    def accept_current(self) -> None:
        self.set_status("accepted")

    def reject_current(self) -> None:
        self.set_status("rejected")

    def undecide_current(self) -> None:
        self.set_status("undecided")

    def next_cell(self, *, clamp_at_end: bool = False) -> None:
        if clamp_at_end:
            self.current_index = min(self.current_index + 1, self.num_cells - 1)
        else:
            self.current_index = (self.current_index + 1) % self.num_cells

    def previous_cell(self) -> None:
        self.current_index = (self.current_index - 1) % self.num_cells

    def jump_to_cell_number(self, cell_number: int) -> None:
        if cell_number < 1:
            self.current_index = 0
        elif cell_number > self.num_cells:
            self.current_index = self.num_cells - 1
        else:
            self.current_index = cell_number - 1

    def current_trace(self) -> np.ndarray:
        if self.current_index in self._trace_cache:
            return self._trace_cache[self.current_index]

        traces = self.traces_by_cell[self.current_index]
        if not traces:
            concatenated = np.asarray([])
        else:
            concatenated = np.concatenate([np.asarray(trace).squeeze() for trace in traces])

        self._trace_cache[self.current_index] = concatenated
        return concatenated

    def session_boundaries(self) -> list[int]:
        boundaries: list[int] = []
        running_total = 0
        for sample_count in self.num_samples[:-1]:
            running_total += sample_count
            boundaries.append(running_total)
        return boundaries
