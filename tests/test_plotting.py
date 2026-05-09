from __future__ import annotations

import numpy as np

from calcium_imaging_cell_sorter.plotting import _cell_contour, _crop_to_signal, _display_limits


# --- _display_limits ---

def test_display_limits_returns_none_for_empty():
    assert _display_limits(np.array([])) == (None, None)


def test_display_limits_returns_none_for_uniform():
    assert _display_limits(np.full((10, 10), 5.0)) == (None, None)


def test_display_limits_returns_finite_range():
    image = np.random.rand(50, 50) * 100
    vmin, vmax = _display_limits(image)
    assert vmin is not None and vmax is not None
    assert vmin < vmax


def test_display_limits_ignores_nan_and_inf():
    image = np.array([[np.nan, 1.0], [2.0, np.inf]])
    vmin, vmax = _display_limits(image)
    assert vmin is not None and vmax is not None


# --- _crop_to_signal ---

def test_crop_to_signal_shrinks_sparse_image():
    image = np.zeros((100, 100))
    image[45:55, 45:55] = 1.0
    cropped = _crop_to_signal(image, padding=5)
    assert cropped.shape[0] < 100
    assert cropped.shape[1] < 100


def test_crop_to_signal_returns_full_image_when_all_zero():
    image = np.zeros((20, 20))
    cropped = _crop_to_signal(image)
    assert cropped.shape == (20, 20)


def test_crop_to_signal_returns_empty_unchanged():
    image = np.array([])
    result = _crop_to_signal(image)
    assert result.size == 0


# --- _cell_contour ---

def test_cell_contour_returns_array_for_valid_cell():
    image = np.zeros((30, 30))
    image[10:20, 10:20] = 1.0
    contour = _cell_contour(image)
    assert contour is not None
    assert contour.ndim == 2
    assert contour.shape[1] == 2


def test_cell_contour_returns_none_for_empty():
    assert _cell_contour(np.array([])) is None


def test_cell_contour_returns_none_for_all_zeros():
    assert _cell_contour(np.zeros((10, 10))) is None
