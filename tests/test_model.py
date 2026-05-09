from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from calcium_imaging_cell_sorter.model import ReviewState, VALID_STATUSES


def _make_state(
    num_cells: int = 4,
    statuses: list[str] | None = None,
    num_cellsets: int = 1,
    samples_per_cellset: int = 100,
) -> ReviewState:
    if statuses is None:
        statuses = ["undecided"] * num_cells
    cell_images = [np.zeros((10, 10)) for _ in range(num_cells)]
    traces = [
        [np.random.randn(samples_per_cellset) for _ in range(num_cellsets)]
        for _ in range(num_cells)
    ]
    return ReviewState(
        cellset_files=tuple(Path(f"session_{i}.isxd") for i in range(num_cellsets)),
        maxdff_file=Path("maxdff.isxd"),
        maxdff_image=np.zeros((20, 20)),
        cell_images=cell_images,
        traces_by_cell=traces,
        num_samples=[samples_per_cellset] * num_cellsets,
        original_statuses=tuple(statuses),
        statuses=list(statuses),
    )


# --- Validation ---

def test_requires_at_least_one_cellset():
    with pytest.raises(ValueError, match="cellset file"):
        ReviewState(
            cellset_files=(),
            maxdff_file=Path("maxdff.isxd"),
            maxdff_image=np.zeros((5, 5)),
            cell_images=[np.zeros((5, 5))],
            traces_by_cell=[[np.zeros(10)]],
            num_samples=[10],
            original_statuses=("undecided",),
            statuses=["undecided"],
        )


def test_requires_at_least_one_cell():
    with pytest.raises(ValueError, match="cell is required"):
        ReviewState(
            cellset_files=(Path("s.isxd"),),
            maxdff_file=Path("maxdff.isxd"),
            maxdff_image=np.zeros((5, 5)),
            cell_images=[],
            traces_by_cell=[],
            num_samples=[10],
            original_statuses=(),
            statuses=[],
        )


def test_rejects_invalid_status():
    with pytest.raises(ValueError, match="must be one of"):
        _make_state(statuses=["accepted", "invalid", "rejected", "undecided"])


# --- Properties ---

def test_num_cells():
    state = _make_state(num_cells=5)
    assert state.num_cells == 5


def test_current_cell_number_is_1_indexed():
    state = _make_state()
    assert state.current_cell_number == 1


def test_current_status():
    state = _make_state(statuses=["accepted", "rejected", "undecided", "undecided"])
    assert state.current_status == "accepted"


# --- Navigation ---

def test_next_cell_wraps():
    state = _make_state(num_cells=3)
    state.current_index = 2
    state.next_cell()
    assert state.current_index == 0


def test_next_cell_clamp_at_end():
    state = _make_state(num_cells=3)
    state.current_index = 2
    state.next_cell(clamp_at_end=True)
    assert state.current_index == 2


def test_previous_cell_wraps():
    state = _make_state(num_cells=3)
    state.current_index = 0
    state.previous_cell()
    assert state.current_index == 2


def test_jump_to_cell_number():
    state = _make_state(num_cells=5)
    state.jump_to_cell_number(3)
    assert state.current_index == 2


def test_jump_clamps_below_one():
    state = _make_state(num_cells=5)
    state.jump_to_cell_number(-1)
    assert state.current_index == 0


def test_jump_clamps_above_max():
    state = _make_state(num_cells=5)
    state.jump_to_cell_number(100)
    assert state.current_index == 4


# --- Status changes ---

def test_accept_current_sets_status_and_advances():
    state = _make_state(num_cells=3)
    state.accept_current()
    assert state.statuses[0] == "accepted"
    assert state.current_index == 1


def test_reject_current():
    state = _make_state(num_cells=3)
    state.reject_current()
    assert state.statuses[0] == "rejected"


def test_undecide_current():
    state = _make_state(num_cells=3, statuses=["accepted", "accepted", "accepted"])
    state.undecide_current()
    assert state.statuses[0] == "undecided"


def test_set_status_without_advance():
    state = _make_state(num_cells=3)
    state.set_status("accepted", advance=False)
    assert state.statuses[0] == "accepted"
    assert state.current_index == 0


def test_set_status_rejects_invalid():
    state = _make_state()
    with pytest.raises(ValueError, match="Unknown cell status"):
        state.set_status("bad_value")


# --- Counts ---

def test_status_counts():
    state = _make_state(statuses=["accepted", "rejected", "undecided", "accepted"])
    counts = state.status_counts()
    assert counts == {"accepted": 2, "rejected": 1, "undecided": 1}


def test_changed_count():
    state = _make_state(statuses=["undecided", "undecided", "undecided", "undecided"])
    state.statuses[0] = "accepted"
    state.statuses[2] = "rejected"
    assert state.changed_count() == 2


def test_changed_count_zero_when_unchanged():
    state = _make_state()
    assert state.changed_count() == 0


# --- Traces and boundaries ---

def test_current_trace_concatenates_sessions():
    state = _make_state(num_cells=2, num_cellsets=3, samples_per_cellset=50)
    trace = state.current_trace()
    assert trace.shape == (150,)


def test_session_boundaries():
    state = _make_state(num_cells=2, num_cellsets=3, samples_per_cellset=50)
    assert state.session_boundaries() == [50, 100]


def test_session_boundaries_single_cellset():
    state = _make_state(num_cells=2, num_cellsets=1, samples_per_cellset=50)
    assert state.session_boundaries() == []
