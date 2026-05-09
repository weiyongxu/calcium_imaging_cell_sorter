from __future__ import annotations

import os
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_constructs_without_loaded_data():
    from PySide6.QtWidgets import QApplication

    from calcium_imaging_cell_sorter.gui import MainWindow

    _app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()

    assert window.windowTitle() == "Calcium Imaging Cell Sorter"
    assert window.loaded is None
    assert any("Ctrl+S" in button.text() for button in window.review_controls)
    window.close()


def test_build_application_prefers_software_rendering():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from calcium_imaging_cell_sorter.app import _build_application

    app = _build_application(sys.argv, QApplication, Qt)

    assert app is not None
    assert os.environ["QT_OPENGL"] == "software"


def test_load_inputs_prefills_form_without_opening_when_maxdff_missing():
    from PySide6.QtWidgets import QApplication

    from calcium_imaging_cell_sorter.gui import MainWindow
    from calcium_imaging_cell_sorter.inputs import ReviewInputs

    _app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.load_inputs(ReviewInputs.from_paths(["C:/data/session-a.isxd"]))

    assert window.loaded is None
    assert window.cellset_list.count() == 1
    assert window.maxdff_edit.text() == ""
    window.close()
