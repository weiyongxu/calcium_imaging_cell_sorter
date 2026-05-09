from __future__ import annotations

import argparse
import os
import sys

from .inputs import ReviewInputs
from .isxd_adapter import load_review_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calcium-cell-sorter",
        description="Review calcium-imaging cellsets and export cell status decisions.",
    )
    parser.add_argument(
        "--cellset",
        action="append",
        default=[],
        help="Cellset .isxd file. Repeat this option for multiple sessions that contain the same identified cells.",
    )
    parser.add_argument("--maxdff", help="Matching max-dFF .isxd image file.")
    parser.add_argument("--output", help="Sidecar CSV output path.")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Open cellsets read-only and disable writing statuses back to .isxd files.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Load and validate the .isxd inputs without opening the GUI or writing outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch the desktop cell sorter."""
    args = build_parser().parse_args(argv)
    inputs = _review_inputs_from_args(args)

    if args.check_only:
        try:
            return _check_inputs(inputs)
        except Exception as exc:
            print(f"Input check failed: {exc}", file=sys.stderr)
            return 1

    return launch_review(inputs=inputs)


def _review_inputs_from_args(args) -> ReviewInputs | None:
    if not args.cellset and not args.maxdff:
        return None
    if not args.cellset:
        raise SystemExit("--cellset must be provided when launching a review.")
    return ReviewInputs.from_paths(
        args.cellset,
        maxdff_file=args.maxdff,
        output_csv=args.output,
        read_only=args.read_only,
    )


def launch_review(
    *,
    inputs: ReviewInputs | None = None,
    app_argv: list[str] | None = None,
) -> int:
    """Launch the GUI from a simple Python input schema.

    Parameters
    ----------
    inputs : ReviewInputs | None
        Pre-selected file paths.  When *None* the GUI opens in file-selection
        mode so the user can browse manually.
    app_argv : list[str] | None
        Arguments forwarded to ``QApplication``.  Defaults to ``sys.argv``.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from .gui import MainWindow

    app = _build_application(app_argv or sys.argv, QApplication, Qt)
    window = MainWindow()
    if inputs is not None:
        window.load_inputs(inputs)
    window.show()
    return app.exec()


def _build_application(app_argv: list[str], QApplication, Qt):
    """Create the Qt application with a conservative rendering backend."""
    # Prefer software rendering for stability on remote filesystems and
    # machines where the desktop OpenGL stack is fragile.
    os.environ.setdefault("QT_OPENGL", "software")
    if QApplication.instance() is None:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    return QApplication.instance() or QApplication(app_argv)


def _check_inputs(inputs: ReviewInputs | None) -> int:
    if inputs is None or inputs.maxdff_file is None:
        raise SystemExit("--check-only requires at least one --cellset and one --maxdff.")
    loaded = load_review_state(inputs.cellset_files, inputs.maxdff_file, read_only=True)
    state = loaded.state
    counts = state.status_counts()
    print("Real ISXD input check passed.")
    print(f"Cellsets: {len(state.cellset_files)}")
    print(f"Cells: {state.num_cells}")
    print(f"Samples per cellset: {', '.join(str(count) for count in state.num_samples)}")
    print(
        "Statuses: "
        f"accepted={counts['accepted']}, "
        f"rejected={counts['rejected']}, "
        f"undecided={counts['undecided']}"
    )
    return 0
