from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .export import write_status_csv
from .inputs import ReviewInputs
from .isxd_adapter import LoadedCellSets, apply_statuses_to_cellsets, load_review_state
from .plotting import ReviewCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT


class MainWindow(QMainWindow):
    """Main desktop window for file selection and cell review."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Calcium Imaging Cell Sorter")
        self.resize(1440, 960)
        self.setMinimumSize(1200, 800)
        self.loaded: LoadedCellSets | None = None
        self.canvas = ReviewCanvas()

        # Inputs
        self.cellset_list = QListWidget()
        self.cellset_list.setMaximumHeight(140)
        self.maxdff_edit = QLineEdit()
        self.maxdff_edit.setReadOnly(True)
        self.maxdff_edit.setPlaceholderText("Select max-dFF image...")
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output CSV path...")

        # Header Indicators
        self.cell_label = QLabel("CELL 0 / 0")
        self.status_label = QLabel("NONE")
        self.count_accepted = QLabel("0")
        self.count_rejected = QLabel("0")
        self.count_undecided = QLabel("0")
        self.count_changed = QLabel("0")

        self.review_controls: list[QPushButton] = []
        self.apply_button: QPushButton | None = None
        self.shortcuts: list[QShortcut] = []

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_review_panel(), stretch=1)
        layout.addLayout(body)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self._apply_style()
        self._install_shortcuts()
        self._set_review_enabled(False)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(70)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(30)

        self.cell_label.setObjectName("HeaderCellLabel")
        layout.addWidget(self.cell_label)
        
        status_box = QFrame()
        status_box.setObjectName("HeaderStatusBox")
        status_layout = QHBoxLayout(status_box)
        status_layout.setContentsMargins(12, 4, 12, 4)
        self.status_label.setObjectName("HeaderStatusLabel")
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_box)

        layout.addStretch(1)

        def create_stat(label: str, widget: QLabel, color: str):
            container = QFrame()
            l_layout = QVBoxLayout(container)
            l_layout.setContentsMargins(0, 0, 0, 0)
            l_layout.setSpacing(2)
            txt = QLabel(label.upper())
            txt.setStyleSheet("font-size: 8pt; font-weight: 700; color: #656d76;")
            widget.setStyleSheet(f"font-size: 14pt; font-weight: 700; color: {color};")
            l_layout.addWidget(txt, alignment=Qt.AlignmentFlag.AlignCenter)
            l_layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)
            return container

        layout.addWidget(create_stat("Accepted", self.count_accepted, "#2da44e"))
        layout.addWidget(create_stat("Rejected", self.count_rejected, "#cf222e"))
        layout.addWidget(create_stat("Undecided", self.count_undecided, "#8250df"))
        layout.addWidget(create_stat("Changed", self.count_changed, "#0969da"))

        return header

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Sidebar")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Cell Sorter")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        
        layout.addWidget(self._build_input_group())
        layout.addWidget(self._build_action_group())
        layout.addStretch(1)
        
        return panel

    def _build_input_group(self) -> QWidget:
        group = QGroupBox("Project Configuration")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Input Cellsets"))
        layout.addWidget(self.cellset_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._choose_cellsets)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.cellset_list.clear)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Max-dFF Overlay"))
        max_row = QHBoxLayout()
        max_row.addWidget(self.maxdff_edit)
        browse_max = QPushButton("...")
        browse_max.setFixedWidth(32)
        browse_max.clicked.connect(self._choose_maxdff)
        max_row.addWidget(browse_max)
        layout.addLayout(max_row)

        layout.addWidget(QLabel("Export Path (CSV)"))
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        browse_out = QPushButton("...")
        browse_out.setFixedWidth(32)
        browse_out.clicked.connect(self._choose_output)
        out_row.addWidget(browse_out)
        layout.addLayout(out_row)

        open_btn = QPushButton("Initialize Review Session")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(lambda: self._open_review())
        layout.addWidget(open_btn)
        
        return group

    def _build_action_group(self) -> QWidget:
        group = QGroupBox("Sorting Controls")
        layout = QGridLayout(group)
        layout.setSpacing(8)

        actions = self._review_actions()
        # Sort indices to put Accept/Reject/Undecide at the top
        for index, (label, shortcut, _key, callback, obj_name) in enumerate(actions):
            btn = QPushButton(f"{label}\n({shortcut})")
            if obj_name:
                btn.setObjectName(obj_name)
            btn.clicked.connect(callback)
            layout.addWidget(btn, index // 2, index % 2)
            self.review_controls.append(btn)
            if callback == self._apply_to_isxd:
                self.apply_button = btn
        
        return group

    def _build_review_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ReviewPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        
        toolbar = NavigationToolbar2QT(self.canvas, panel)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        return panel

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f6f8fa;
                color: #1f2328;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 9pt;
            }
            QFrame#Header {
                background: #ffffff;
                border-bottom: 1px solid #d0d7de;
            }
            QLabel#HeaderCellLabel {
                font-size: 16pt;
                font-weight: 800;
                color: #1f2328;
            }
            QFrame#HeaderStatusBox {
                background: transparent;
                border: none;
            }
            QLabel#HeaderStatusLabel {
                font-size: 11pt;
                font-weight: 800;
                color: #ffffff;
                text-transform: uppercase;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QFrame#Sidebar {
                background: #ffffff;
                border-right: 1px solid #d0d7de;
            }
            QLabel#AppTitle {
                font-size: 15pt;
                font-weight: 700;
                color: #1f2328;
                margin-bottom: 5px;
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #d0d7de;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget, QLineEdit {
                background: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget:focus, QLineEdit:focus {
                border-color: #0969da;
            }
            QPushButton {
                background: #f6f8fa;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                font-weight: 600;
                min-height: 34px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: #f3f4f6;
                border-color: #1f2328;
            }
            QPushButton#AcceptButton {
                background: #2da44e;
                color: #ffffff;
                border: 1px solid rgba(27, 31, 36, 0.15);
            }
            QPushButton#AcceptButton:hover {
                background: #2c974b;
            }
            QPushButton#RejectButton {
                background: #cf222e;
                color: #ffffff;
                border: 1px solid rgba(27, 31, 36, 0.15);
            }
            QPushButton#RejectButton:hover {
                background: #a40e26;
            }
            QPushButton#UndecideButton {
                background: #8250df;
                color: #ffffff;
                border: 1px solid rgba(27, 31, 36, 0.15);
            }
            QPushButton#UndecideButton:hover {
                background: #6e40c9;
            }
            QPushButton#SaveButton {
                background: #1f6feb;
                color: #ffffff;
                border: 1px solid rgba(27, 31, 36, 0.15);
            }
            QPushButton#SaveButton:hover {
                background: #1158c7;
            }
            QPushButton:disabled {
                color: #8c959f;
                background: #f6f8fa;
                border-color: #d0d7de;
            }
            """
        )

    def _review_actions(self):
        return [
            ("Accept", "→", Qt.Key_Right, self._accept_current, "AcceptButton"),
            ("Reject", "←", Qt.Key_Left, self._reject_current, "RejectButton"),
            ("Undecide", "U", QKeySequence("u"), self._undecide_current, "UndecideButton"),
            ("Jump", "J", QKeySequence("j"), self._jump_to_cell, ""),
            ("Previous", "↑", Qt.Key_Up, self._previous_cell, ""),
            ("Next", "↓", Qt.Key_Down, self._next_cell, ""),
            ("Save CSV", "Ctrl+S", QKeySequence("Ctrl+S"), self._save_csv, "SaveButton"),
            ("Apply to ISXD", "Ctrl+Shift+A", QKeySequence("Ctrl+Shift+A"), self._apply_to_isxd, ""),
        ]


    def _install_shortcuts(self) -> None:
        for _label, _shortcut_text, key, callback, _object_name in self._review_actions():
            shortcut = QShortcut(key, self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def _set_review_enabled(self, enabled: bool) -> None:
        for button in self.review_controls:
            button.setEnabled(enabled)

    def _choose_cellsets(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select cellset files",
            "",
            "ISXD files (*.isxd);;All files (*.*)",
        )
        for filename in files:
            self._add_cellset_path(filename)
        if files and not self.output_edit.text():
            first_path = Path(files[0])
            self.output_edit.setText(str(first_path.with_name(first_path.stem + "-cell-status-review.csv")))

    def _choose_maxdff(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select max-dFF file",
            "",
            "ISXD files (*.isxd);;All files (*.*)",
        )
        if filename:
            self.maxdff_edit.setText(filename)

    def _choose_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select output CSV",
            self.output_edit.text() or "cell-status-review.csv",
            "CSV files (*.csv);;All files (*.*)",
        )
        if filename:
            self.output_edit.setText(filename)

    def _selected_cellsets(self) -> list[str]:
        return [
            self.cellset_list.item(index).data(Qt.ItemDataRole.UserRole) or self.cellset_list.item(index).text()
            for index in range(self.cellset_list.count())
        ]

    def _add_cellset_path(self, filename: str) -> None:
        if filename in self._selected_cellsets():
            return
        item = QListWidgetItem(Path(filename).name)
        item.setData(Qt.ItemDataRole.UserRole, filename)
        item.setToolTip(filename)
        self.cellset_list.addItem(item)

    def load_inputs(self, inputs: ReviewInputs) -> None:
        """Populate the input form from a simple Python input schema."""
        self.cellset_list.clear()
        for filename in inputs.cellset_files:
            self._add_cellset_path(str(filename))
        self.maxdff_edit.setText("" if inputs.maxdff_file is None else str(inputs.maxdff_file))
        self.output_edit.setText(str(inputs.output_csv_path()))
        if inputs.maxdff_file is not None:
            self._open_review(read_only=inputs.read_only)
        else:
            self.statusBar().showMessage("Select a matching max-dFF image to open the review.", 5000)

    def _open_review(self, *, read_only: bool = False) -> None:
        cellsets = self._selected_cellsets()
        maxdff = self.maxdff_edit.text().strip()
        output = self.output_edit.text().strip()
        if not cellsets:
            self._show_error("Select at least one cellset .isxd file.")
            return
        if not maxdff:
            self._show_error("Select a max-dFF .isxd file.")
            return
        if not output:
            self._show_error("Choose an output CSV path.")
            return

        try:
            self.loaded = load_review_state(cellsets, maxdff, read_only=read_only)
        except Exception as exc:
            self._show_error(str(exc))
            return

        self.canvas.set_state(self.loaded.state)
        self._set_review_enabled(True)
        if self.apply_button is not None:
            self.apply_button.setEnabled(self.loaded.can_apply)
        self._refresh_summary()
        mode = "read-only" if read_only else "writable"
        self.statusBar().showMessage(f"Review loaded ({mode}).", 5000)

    def _change_state(self, action_name: str) -> None:
        if not self._has_state():
            return
        state = self.loaded.state
        match action_name:
            case "accept_current":
                state.accept_current()
            case "reject_current":
                state.reject_current()
            case "undecide_current":
                state.undecide_current()
            case "previous_cell":
                state.previous_cell()
            case "next_cell":
                state.next_cell()
            case _:
                raise ValueError(f"Unknown action: {action_name}")
        self._refresh_review()

    def _accept_current(self) -> None:
        self._change_state("accept_current")

    def _reject_current(self) -> None:
        self._change_state("reject_current")

    def _undecide_current(self) -> None:
        self._change_state("undecide_current")

    def _previous_cell(self) -> None:
        self._change_state("previous_cell")

    def _next_cell(self) -> None:
        self._change_state("next_cell")

    def _jump_to_cell(self) -> None:
        if not self._has_state():
            return
        state = self.loaded.state
        cell_number, ok = QInputDialog.getInt(
            self,
            "Jump to Cell",
            "Cell number",
            state.current_cell_number,
            1,
            state.num_cells,
        )
        if ok:
            state.jump_to_cell_number(cell_number)
            self._refresh_review()

    def _save_csv(self) -> None:
        if not self._has_state():
            return
        output = self.output_edit.text().strip()
        if not output:
            self._show_error("Choose an output CSV path.")
            return
        try:
            path = write_status_csv(self.loaded.state, output)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self.statusBar().showMessage(f"Saved CSV: {path}", 8000)

    def _apply_to_isxd(self) -> None:
        if not self._has_state():
            return
        if not self.loaded.can_apply:
            self._show_error("This review was opened read-only. Reopen without --read-only to apply statuses to ISXD.")
            return
        answer = QMessageBox.question(
            self,
            "Apply statuses to ISXD",
            "This will write current statuses into every selected .isxd cellset. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            apply_statuses_to_cellsets(self.loaded.cellsets, self.loaded.state)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self.statusBar().showMessage("Statuses applied to ISXD files.", 8000)

    def _has_state(self) -> bool:
        return self.loaded is not None

    def _refresh_review(self) -> None:
        self.canvas.refresh()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        if self.loaded is None:
            self.cell_label.setText("CELL 0 / 0")
            self.status_label.setText("NONE")
            return
        state = self.loaded.state
        counts = state.status_counts()
        
        self.cell_label.setText(f"CELL {state.current_cell_number} / {state.num_cells}")
        
        status = state.current_status.upper()
        self.status_label.setText(status)
        
        # Solid colored badge for status
        color_map = {
            "ACCEPTED": ("#2da44e", "#ffffff"),
            "REJECTED": ("#cf222e", "#ffffff"),
            "UNDECIDED": ("#8250df", "#ffffff"),
        }
        bg_color, text_color = color_map.get(status, ("#e1e4e8", "#24292f"))
        self.status_label.setStyleSheet(f"""
            font-size: 11pt; 
            font-weight: 800; 
            color: {text_color}; 
            background-color: {bg_color};
            border-radius: 4px;
            padding: 4px 12px;
            text-transform: uppercase;
        """)
        
        self.count_accepted.setText(str(counts['accepted']))
        self.count_rejected.setText(str(counts['rejected']))
        self.count_undecided.setText(str(counts['undecided']))
        self.count_changed.setText(str(state.changed_count()))

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Calcium Imaging Cell Sorter", message)
