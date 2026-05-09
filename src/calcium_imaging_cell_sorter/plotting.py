from __future__ import annotations

import numpy as np
from contourpy import LineType, contour_generator
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .model import ReviewState


class ReviewCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas embedded in the Qt review window."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(11, 8), constrained_layout=True, facecolor="#ffffff")
        super().__init__(self.figure)
        self._state: ReviewState | None = None
        grid = self.figure.add_gridspec(2, 2, height_ratios=[1.05, 1.35])
        self.ax_trace = self.figure.add_subplot(grid[0, :])
        self.ax_cell = self.figure.add_subplot(grid[1, 0])
        self.ax_maxdff = self.figure.add_subplot(grid[1, 1])

    def set_state(self, state: ReviewState) -> None:
        self._state = state
        self.refresh()

    def refresh(self) -> None:
        if self._state is None:
            return

        state = self._state
        cell_image = np.asarray(state.cell_images[state.current_index])
        cell_zoom = _crop_to_signal(cell_image)
        maxdff = np.asarray(state.maxdff_image)
        trace = state.current_trace()

        self.ax_trace.clear()
        self.ax_cell.clear()
        self.ax_maxdff.clear()

        self.ax_trace.plot(np.arange(trace.size), trace, lw=0.55, color="#1f6feb")
        for boundary in state.session_boundaries():
            self.ax_trace.axvline(boundary, color="#2da44e", lw=1.5, alpha=0.8)
        self.ax_trace.grid(True, color="#e5e7eb", linewidth=0.6)
        
        # Modernize trace plot by removing top/right spines
        self.ax_trace.spines['top'].set_visible(False)
        self.ax_trace.spines['right'].set_visible(False)
        
        self.ax_trace.set_title("Calcium Trace", fontsize=11, fontweight="bold")
        self.ax_trace.set_xlabel("Frame")
        self.ax_trace.set_ylabel("Signal")

        # Use aspect="equal" to prevent distortion of the biological cell shape
        self.ax_cell.imshow(cell_zoom, cmap="viridis", interpolation="nearest", aspect="equal")
        self.ax_cell.set_title("Current Cell Footprint", fontsize=11, fontweight="bold")
        self.ax_cell.set_axis_off()

        vmin, vmax = _display_limits(maxdff)
        self.ax_maxdff.imshow(maxdff, cmap="gray", vmin=vmin, vmax=vmax, interpolation="nearest", aspect="equal")
        contour = _cell_contour(cell_image)
        if contour is not None:
            # Thicker contour line for better visibility against bright cells
            self.ax_maxdff.plot(contour[:, 0], contour[:, 1], color="#ff2d20", lw=2.0, alpha=0.95)
        self.ax_maxdff.set_title("Max-dFF Overlay", fontsize=11, fontweight="bold")
        self.ax_maxdff.set_axis_off()

        self.draw_idle()


def _display_limits(image: np.ndarray) -> tuple[float | None, float | None]:
    if image.size == 0:
        return None, None
    finite = image[np.isfinite(image)]
    if finite.size == 0:
        return None, None
    vmin = float(np.percentile(finite, 1))
    vmax = float(np.percentile(finite, 99))
    if vmin == vmax:
        return None, None
    return vmin, vmax


def _cell_contour(cell_image: np.ndarray) -> np.ndarray | None:
    if cell_image.size == 0:
        return None
    maximum = float(np.nanmax(cell_image))
    if not np.isfinite(maximum) or maximum <= 0:
        return None
    thresholded = cell_image > (0.8 * maximum)
    try:
        lines = contour_generator(
            z=thresholded.astype(int),
            line_type=LineType.ChunkCombinedCode,
        ).lines(0.5)
    except ValueError:
        return None
    if not lines or not lines[0] or len(lines[0][0]) == 0:
        return None
    return np.asarray(lines[0][0])


def _crop_to_signal(image: np.ndarray, threshold_fraction: float = 0.2, padding: int = 12) -> np.ndarray:
    if image.size == 0:
        return image
    maximum = float(np.nanmax(image))
    if not np.isfinite(maximum) or maximum <= 0:
        return image

    rows, cols = np.where(image > maximum * threshold_fraction)
    if rows.size == 0 or cols.size == 0:
        return image

    row_start = max(int(rows.min()) - padding, 0)
    row_stop = min(int(rows.max()) + padding + 1, image.shape[0])
    col_start = max(int(cols.min()) - padding, 0)
    col_stop = min(int(cols.max()) + padding + 1, image.shape[1])
    return image[row_start:row_stop, col_start:col_stop]
