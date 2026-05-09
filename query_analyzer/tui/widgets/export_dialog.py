"""Export dialog widget for query analysis reports."""

from __future__ import annotations

import re
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from query_analyzer.adapters.models import QueryAnalysisReport
from query_analyzer.tui.export_analysis import (
    AnalysisExporter,
    ExportFormat,
)


class ExportDialog(ModalScreen[str | None]):
    """Modal dialog for exporting analysis reports.

    Returns the export path if successful, None if cancelled.
    """

    DEFAULT_CSS = """
    ExportDialog {
        align: center middle;
    }

    ExportDialog > Container {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $panel;
        padding: 1;
    }

    ExportDialog .dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }

    ExportDialog .field-label {
        width: 15;
        text-align: right;
        margin-right: 1;
        text-style: bold;
    }

    ExportDialog .field-row {
        height: auto;
        margin-bottom: 1;
    }

    ExportDialog Input {
        width: 1fr;
    }

    ExportDialog Select {
        width: 1fr;
    }

    ExportDialog .button-row {
        height: auto;
        margin-top: 1;
        align: right middle;
    }

    ExportDialog Button {
        margin-left: 1;
    }

    ExportDialog #btn-export {
        width: 12;
    }

    ExportDialog #btn-cancel {
        width: 10;
    }

    ExportDialog .error-message {
        color: $error;
        margin-top: 1;
    }
    """

    def __init__(self, report: QueryAnalysisReport) -> None:
        super().__init__()
        self.report = report
        self._exporter = AnalysisExporter(report)

    def compose(self) -> ComposeResult:
        """Compose dialog layout."""
        with Container():
            with Vertical():
                yield Label("Export Analysis", classes="dialog-title")

                # Format selection
                with Horizontal(classes="field-row"):
                    yield Label("Format:", classes="field-label")
                    yield Select(
                        options=[
                            ("JSON", ExportFormat.JSON),
                            ("Markdown", ExportFormat.MARKDOWN),
                            ("SQL", ExportFormat.SQL),
                        ],
                        id="export-format",
                        value=ExportFormat.JSON,
                    )

                # Filename
                with Horizontal(classes="field-row"):
                    yield Label("Filename:", classes="field-label")
                    default_filename = AnalysisExporter.auto_filename(
                        self.report.query,
                        self.report.engine,
                        ExportFormat.JSON,
                    )
                    yield Input(
                        value=default_filename,
                        id="export-filename",
                    )

                # Directory
                with Horizontal(classes="field-row"):
                    yield Label("Directory:", classes="field-label")
                    yield Input(
                        value=str(Path.home() / "Downloads"),
                        id="export-directory",
                    )

                # Error message placeholder
                yield Static(id="error-message", classes="error-message")

                # Buttons
                with Horizontal(classes="button-row"):
                    yield Button("Cancel", id="btn-cancel", variant="default")
                    yield Button("Export", id="btn-export", variant="primary")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle format selection change.

        Args:
            event: Select changed event
        """
        format = event.value
        filename_input = self.query_one("#export-filename", Input)

        # Update filename with new extension
        current = Path(filename_input.value)
        extension = f".{format}"
        new_filename = current.stem + extension
        filename_input.value = new_filename

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button pressed event
        """
        button_id = event.button.id

        if button_id == "btn-cancel":
            self.dismiss(None)
        elif button_id == "btn-export":
            self._handle_export()

    def _handle_export(self) -> None:
        """Handle export action."""
        error_widget = self.query_one("#error-message", Static)
        error_widget.update("")

        try:
            format_select = self.query_one("#export-format", Select)
            filename_input = self.query_one("#export-filename", Input)
            directory_input = self.query_one("#export-directory", Input)

            format = str(format_select.value)
            filename = filename_input.value.strip()
            directory = directory_input.value.strip()

            if not filename:
                error_widget.update("[red]Error: Filename cannot be empty[/red]")
                return

            if not directory:
                error_widget.update("[red]Error: Directory cannot be empty[/red]")
                return

            # Sanitize invalid filename characters (especially for Windows)
            sanitized_filename = self._sanitize_filename(filename)
            if not sanitized_filename:
                error_widget.update("[red]Error: Invalid filename[/red]")
                return

            if sanitized_filename != filename:
                filename = sanitized_filename
                filename_input.value = sanitized_filename

            # Build full path
            filepath = Path(directory) / filename

            # Export
            saved_path = self._exporter.save_to_file(filepath, format)

            # Dismiss with success message
            self.dismiss(str(saved_path))

        except Exception as e:
            error_widget.update(f"[red]Error: {str(e)}[/red]")

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename while preserving extension when possible."""
        cleaned = filename.strip().strip('"').strip("'")
        if not cleaned:
            return ""

        path_obj = Path(cleaned)
        stem = path_obj.stem
        suffix = path_obj.suffix

        # Windows invalid chars: <>:"/\|?*
        stem = re.sub(r"[<>:\"/\\|?*]+", "_", stem)
        stem = re.sub(r"\s+", "_", stem)
        stem = re.sub(r"_+", "_", stem).strip("._ ")

        if not stem:
            return ""

        if suffix and re.fullmatch(r"\.[a-zA-Z0-9]+", suffix):
            return f"{stem}{suffix.lower()}"

        return stem
