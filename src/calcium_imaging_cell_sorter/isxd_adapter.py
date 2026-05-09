from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol

import numpy as np

from .model import ReviewState


class CellSetLike(Protocol):
    num_cells: int
    timing: object
    spacing: object

    def get_cell_image_data(self, index: int): ...

    def get_acquisition_info(self) -> dict[str, object]: ...

    def get_cell_name(self, index: int) -> str: ...

    def get_cell_trace_data(self, index: int): ...

    def get_cell_status(self, index: int) -> str: ...

    def set_cell_status(self, index: int, status: str) -> None: ...

    def flush(self) -> None: ...


@dataclass(frozen=True)
class LoadedCellSets:
    cellsets: list[CellSetLike]
    state: ReviewState
    can_apply: bool = True


_CELLSET_DAY_PATTERN = re.compile(r"(?:^|[_-])d(?P<day>\d+)(?:[_-]|$)", re.IGNORECASE)
_MAXDFF_DAY_PATTERN = re.compile(r"day[ _-]?(?P<day>\d+)", re.IGNORECASE)


def import_isx():
    """Import Inscopix isx lazily so installation can be documented cleanly."""
    try:
        import isx  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The Inscopix 'isx' package is required to open real .isxd files. "
            "Install isx into this Python environment, then launch the app again."
        ) from exc
    return isx


def _num_samples(cellset: CellSetLike) -> int:
    """Return the number of temporal samples (frames) in a cellset."""
    return int(getattr(cellset.timing, "num_samples"))


def _spacing_num_pixels(obj) -> tuple[int, int] | None:
    """Extract the (rows, cols) pixel dimensions from an isx object's spacing."""
    spacing = getattr(obj, "spacing", None)
    num_pixels = getattr(spacing, "num_pixels", None)
    if num_pixels is None:
        return None
    return (int(num_pixels[0]), int(num_pixels[1]))


def _cellset_acquisition_info(cellset: CellSetLike) -> dict[str, object]:
    getter = getattr(cellset, "get_acquisition_info", None)
    if getter is None:
        return {}
    info = getter()
    return info if isinstance(info, dict) else {}


def _cellset_day_token(path: Path, cellset: CellSetLike) -> str | None:
    """Extract a normalised day identifier (e.g. 'd5') from a cellset.

    Checks the acquisition-info session name first, then falls back to
    the filename stem.  Returns *None* when no day tag is found.
    """
    info = _cellset_acquisition_info(cellset)
    session_name = str(info.get("Session Name", "")).strip()
    for text in (session_name, path.stem):
        match = _CELLSET_DAY_PATTERN.search(text)
        if match:
            return f"d{int(match.group('day'))}"
    return None


def _maxdff_day_token(path: Path) -> str | None:
    match = _MAXDFF_DAY_PATTERN.search(path.stem)
    if not match:
        return None
    return f"d{int(match.group('day'))}"


def _cell_name_sequence(cellset: CellSetLike) -> tuple[str, ...] | None:
    getter = getattr(cellset, "get_cell_name", None)
    if getter is None:
        return None
    try:
        return tuple(str(getter(index)) for index in range(int(cellset.num_cells)))
    except Exception:
        return None


def _shared_cellset_day_token(cellsets: list[CellSetLike], cellset_paths: list[Path]) -> str | None:
    day_tokens = {
        token
        for cellset, path in zip(cellsets, cellset_paths)
        if (token := _cellset_day_token(path, cellset)) is not None
    }
    if len(day_tokens) == 1:
        return next(iter(day_tokens))
    return None


def _validate_cellset_collection(cellsets: list[CellSetLike], cellset_paths: list[Path]) -> None:
    """Verify that all selected cellsets belong to the same processing run.

    Checks that the cell count, field-of-view spacing, and cell name
    sequence are consistent across all cellsets.  Raises ``ValueError``
    with an actionable message when a mismatch is found.
    """
    num_cells_set = {int(cellset.num_cells) for cellset in cellsets}
    if len(num_cells_set) != 1:
        counts = ", ".join(str(cellset.num_cells) for cellset in cellsets)
        raise ValueError(f"All cellsets must have the same number of cells. Found: {counts}.")

    spacings = {
        spacing
        for cellset in cellsets
        if (spacing := _spacing_num_pixels(cellset)) is not None
    }
    if len(spacings) > 1:
        raise ValueError(
            "Selected cellsets do not share the same field of view. Load only sessions that were processed together."
        )

    name_sequences = {
        names
        for cellset in cellsets
        if (names := _cell_name_sequence(cellset)) is not None
    }
    if len(name_sequences) > 1:
        raise ValueError(
            "Selected cellsets do not appear to contain the same identified cells. Load only sessions that were processed together."
        )


def _validate_maxdff_compatibility(
    cellsets: list[CellSetLike],
    cellset_paths: list[Path],
    maxdff_path: Path,
    maxdff,
) -> None:
    """Verify that the max-dFF image matches the selected cellsets.

    Checks field-of-view pixel dimensions and, when available, the day
    metadata embedded in the filenames.  Raises ``ValueError`` when the
    max-dFF image clearly belongs to a different session set.
    """
    maxdff_spacing = _spacing_num_pixels(maxdff)
    for cellset in cellsets:
        cellset_spacing = _spacing_num_pixels(cellset)
        if maxdff_spacing is not None and cellset_spacing is not None and cellset_spacing != maxdff_spacing:
            raise ValueError(
                "Selected cellset and max-dFF files do not share the same field of view. Choose a max-dFF image from the same sessions."
            )

    shared_day = _shared_cellset_day_token(cellsets, cellset_paths)
    maxdff_day = _maxdff_day_token(maxdff_path)
    if shared_day is not None and maxdff_day is not None and shared_day != maxdff_day:
        raise ValueError(
            f"Selected max-dFF file '{maxdff_path.name}' does not match the cellset day ({shared_day}). Choose the matching max-dFF image from the same sessions."
        )


def _resolve_maxdff(
    isx,
    cellsets: list[CellSetLike],
    cellset_paths: list[Path],
    maxdff_file: str | Path | None,
):
    if maxdff_file is None or not str(maxdff_file).strip():
        raise ValueError("Select a matching max-dFF .isxd file for the selected cellset sessions.")
    maxdff_path = Path(maxdff_file)

    maxdff = isx.Image.read(str(maxdff_path))
    _validate_maxdff_compatibility(cellsets, cellset_paths, maxdff_path, maxdff)
    return maxdff_path, maxdff


def load_review_state(
    cellset_files: list[str | Path],
    maxdff_file: str | Path | None = None,
    *,
    read_only: bool = True,
) -> LoadedCellSets:
    """Load real .isxd files into an in-memory review state."""
    if not cellset_files:
        raise ValueError("Select at least one cellset .isxd file.")

    isx = import_isx()
    cellset_paths = [Path(path) for path in cellset_files]
    cellsets = [
        isx.CellSet.read(str(path), read_only=read_only)
        for path in cellset_paths
    ]
    _validate_cellset_collection(cellsets, cellset_paths)
    maxdff_path, maxdff = _resolve_maxdff(isx, cellsets, cellset_paths, maxdff_file)
    maxdff_image = np.asarray(maxdff.get_data())
    state = build_review_state_from_cellsets(
        cellsets=cellsets,
        cellset_files=cellset_paths,
        maxdff_file=maxdff_path,
        maxdff_image=maxdff_image,
    )
    return LoadedCellSets(cellsets=cellsets, state=state, can_apply=not read_only)


def build_review_state_from_cellsets(
    *,
    cellsets: list[CellSetLike],
    cellset_files: list[str | Path],
    maxdff_file: str | Path,
    maxdff_image,
) -> ReviewState:
    """Build review state from already opened cellset-like objects."""
    if not cellsets:
        raise ValueError("At least one cellset is required.")
    _validate_cellset_collection(cellsets, [Path(path) for path in cellset_files])

    first = cellsets[0]
    num_cells = int(first.num_cells)
    cell_images = [
        np.asarray(first.get_cell_image_data(cell_index))
        for cell_index in range(num_cells)
    ]
    traces_by_cell = [
        [
            np.asarray(cellset.get_cell_trace_data(cell_index)).squeeze()
            for cellset in cellsets
        ]
        for cell_index in range(num_cells)
    ]
    statuses = [
        str(first.get_cell_status(cell_index))
        for cell_index in range(num_cells)
    ]
    num_samples = [_num_samples(cellset) for cellset in cellsets]

    return ReviewState(
        cellset_files=tuple(Path(path) for path in cellset_files),
        maxdff_file=Path(maxdff_file),
        maxdff_image=np.asarray(maxdff_image),
        cell_images=cell_images,
        traces_by_cell=traces_by_cell,
        num_samples=num_samples,
        original_statuses=tuple(statuses),
        statuses=list(statuses),
    )


def apply_statuses_to_cellsets(cellsets: list[CellSetLike], state: ReviewState) -> None:
    """Write current review statuses into all opened cellsets."""
    if len(cellsets) != len(state.cellset_files):
        raise ValueError("Opened cellsets do not match the review state.")

    for cell_index, status in enumerate(state.statuses):
        for cellset in cellsets:
            cellset.set_cell_status(cell_index, status)
    for cellset in cellsets:
        cellset.flush()
