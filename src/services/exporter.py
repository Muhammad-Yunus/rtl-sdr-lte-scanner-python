"""Persist scan results to disk.

The exporter reuses the formatter for content generation and the filesystem
helpers for atomic writes, so disk I/O never gets tangled with rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..domain.models import LTECell
from ..infrastructure.filesystem import ensure_directory, write_text_atomic
from .formatter import render_csv, render_json


@dataclass(frozen=True, slots=True)
class ExportedFile:
    """Summary of one successful export."""

    path: Path
    cells_written: int


class ScanExporter:
    """Write cells to a destination directory using a known format."""

    def __init__(self, export_dir: Path) -> None:
        self._export_dir = Path(export_dir)

    def export_json(self, cells: list[LTECell], filename: str) -> ExportedFile:
        ensure_directory(self._export_dir)
        path = self._export_dir / filename
        content = render_json(cells)
        write_text_atomic(path, content)
        return ExportedFile(path=path, cells_written=len(cells))

    def export_csv(self, cells: list[LTECell], filename: str) -> ExportedFile:
        ensure_directory(self._export_dir)
        path = self._export_dir / filename
        content = render_csv(cells)
        write_text_atomic(path, content)
        return ExportedFile(path=path, cells_written=len(cells))


__all__ = ["ExportedFile", "ScanExporter"]
