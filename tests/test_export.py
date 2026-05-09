from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from calcium_imaging_cell_sorter.export import CSV_COLUMNS, build_status_rows, write_status_csv
from calcium_imaging_cell_sorter.model import ReviewState


def _make_state() -> ReviewState:
    return ReviewState(
        cellset_files=(Path("session_a.isxd"), Path("session_b.isxd")),
        maxdff_file=Path("day5-maxdff.isxd"),
        maxdff_image=np.zeros((10, 10)),
        cell_images=[np.zeros((5, 5)) for _ in range(3)],
        traces_by_cell=[[np.zeros(20), np.zeros(20)] for _ in range(3)],
        num_samples=[20, 20],
        original_statuses=("accepted", "rejected", "undecided"),
        statuses=["rejected", "rejected", "accepted"],
    )


def test_build_status_rows_produces_correct_count():
    state = _make_state()
    rows = build_status_rows(state)
    assert len(rows) == 3


def test_build_status_rows_columns():
    state = _make_state()
    rows = build_status_rows(state)
    for row in rows:
        assert set(row.keys()) == set(CSV_COLUMNS)


def test_build_status_rows_cell_index_is_1_indexed():
    state = _make_state()
    rows = build_status_rows(state)
    assert [row["cell_index"] for row in rows] == ["1", "2", "3"]


def test_build_status_rows_changed_flag():
    state = _make_state()
    rows = build_status_rows(state)
    assert rows[0]["changed"] == "True"   # accepted -> rejected
    assert rows[1]["changed"] == "False"  # rejected -> rejected
    assert rows[2]["changed"] == "True"   # undecided -> accepted


def test_build_status_rows_cellset_files_pipe_separated():
    state = _make_state()
    rows = build_status_rows(state)
    assert rows[0]["cellset_files"] == "session_a.isxd|session_b.isxd"


def test_build_status_rows_uses_provided_timestamp():
    state = _make_state()
    ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    rows = build_status_rows(state, saved_at=ts)
    for row in rows:
        assert "2025-06-15" in row["saved_at"]


def test_write_status_csv_round_trip(tmp_path):
    state = _make_state()
    output = tmp_path / "review.csv"
    result_path = write_status_csv(state, output)

    assert result_path == output
    assert output.exists()

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 3
    assert reader.fieldnames == CSV_COLUMNS
    assert rows[0]["status"] == "rejected"
    assert rows[2]["status"] == "accepted"


def test_write_status_csv_creates_parent_directories(tmp_path):
    state = _make_state()
    output = tmp_path / "deep" / "nested" / "review.csv"
    write_status_csv(state, output)
    assert output.exists()
