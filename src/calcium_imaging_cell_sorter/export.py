from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .model import ReviewState


CSV_COLUMNS = [
    "cell_index",
    "original_status",
    "status",
    "changed",
    "saved_at",
    "cellset_files",
    "maxdff_file",
]


def build_status_rows(state: ReviewState, saved_at: datetime | None = None) -> list[dict[str, str]]:
    """Build sidecar CSV rows from the current review state."""
    timestamp = (saved_at or datetime.now(timezone.utc)).astimezone().isoformat(timespec="seconds")
    cellset_files = "|".join(str(path) for path in state.cellset_files)
    return [
        {
            "cell_index": str(idx + 1),
            "original_status": state.original_statuses[idx],
            "status": state.statuses[idx],
            "changed": str(state.statuses[idx] != state.original_statuses[idx]),
            "saved_at": timestamp,
            "cellset_files": cellset_files,
            "maxdff_file": str(state.maxdff_file),
        }
        for idx in range(state.num_cells)
    ]


def write_status_csv(
    state: ReviewState,
    output_file: str | Path,
    saved_at: datetime | None = None,
) -> Path:
    """Write the default non-mutating sidecar CSV."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_status_rows(state, saved_at=saved_at)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
