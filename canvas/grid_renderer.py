"""
AirWrite Studio - Grid / Template Background Renderer
========================================================
Paints configurable background grid patterns onto a QPainter surface.
Supports lined paper, graph paper, dot grid, music staff, and Cornell
notes templates. All colours are semi-transparent so they stay behind
user strokes without visual competition.
"""

from enum import Enum

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen


# ─── Grid Type Enum ───────────────────────────────────────────────────────────

class GridType(Enum):
    """Available background grid / template styles."""
    NONE = "none"
    LINES = "lines"
    GRAPH = "graph"
    DOTS = "dots"
    MUSIC_STAFF = "music"
    CORNELL = "cornell"


# ─── Grid Renderer ────────────────────────────────────────────────────────────

class GridRenderer:
    """
    Renders background grid patterns onto a QPainter.

    Usage::

        renderer = GridRenderer()
        renderer.draw(painter, width, height, GridType.GRAPH, zoom=1.5)

    All drawing respects the current painter transform; *zoom* is used only
    to scale the logical grid spacing so the pattern density stays comfortable
    at any zoom level.
    """

    # ── Colour palette (RGBA) ─────────────────────────────────────────────

    _LINE_COLOR = QColor(0x2A, 0x2A, 0x4A, 80)
    _LINE_MARGIN_COLOR = QColor(0xCC, 0x33, 0x33, 60)

    _GRAPH_MINOR_COLOR = QColor(0x2A, 0x2A, 0x4A, 50)
    _GRAPH_MAJOR_COLOR = QColor(0x3A, 0x3A, 0x5C, 70)

    _DOT_COLOR = QColor(0x3A, 0x3A, 0x5C, 90)

    _STAFF_COLOR = QColor(0x2A, 0x2A, 0x4A, 80)

    _CORNELL_DIVIDER_COLOR = QColor(0x3A, 0x3A, 0x5C, 70)
    _CORNELL_LABEL_COLOR = QColor(0x3A, 0x3A, 0x5C, 45)

    # ── Public API ────────────────────────────────────────────────────────

    def draw(
        self,
        painter: QPainter,
        width: int,
        height: int,
        grid_type: GridType,
        zoom: float = 1.0,
    ) -> None:
        """
        Paint the requested grid pattern onto *painter*.

        Args:
            painter: Active QPainter (caller manages begin/end).
            width:   Canvas width in logical pixels.
            height:  Canvas height in logical pixels.
            grid_type: Which background template to draw.
            zoom:    Current view zoom factor (scales grid spacing).
        """
        if grid_type is GridType.NONE:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        dispatch = {
            GridType.LINES: self._draw_lines,
            GridType.GRAPH: self._draw_graph,
            GridType.DOTS: self._draw_dots,
            GridType.MUSIC_STAFF: self._draw_music_staff,
            GridType.CORNELL: self._draw_cornell,
        }

        handler = dispatch.get(grid_type)
        if handler is not None:
            handler(painter, width, height, zoom)

        painter.restore()

    # ── Private: Lined Paper ──────────────────────────────────────────────

    def _draw_lines(
        self,
        painter: QPainter,
        width: int,
        height: int,
        zoom: float,
    ) -> None:
        """Horizontal ruled lines with a left margin rule."""
        spacing = 30.0 * zoom
        margin_x = 60.0 * zoom

        # Horizontal rules
        pen = QPen(self._LINE_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)

        y = spacing
        while y < height:
            painter.drawLine(QPointF(0.0, y), QPointF(float(width), y))
            y += spacing

        # Red margin line
        pen = QPen(self._LINE_MARGIN_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawLine(QPointF(margin_x, 0.0), QPointF(margin_x, float(height)))

    # ── Private: Graph Paper ──────────────────────────────────────────────

    def _draw_graph(
        self,
        painter: QPainter,
        width: int,
        height: int,
        zoom: float,
    ) -> None:
        """Square grid with minor and major division lines."""
        minor_spacing = 20.0 * zoom
        major_spacing = 100.0 * zoom

        # Minor grid lines
        pen_minor = QPen(self._GRAPH_MINOR_COLOR)
        pen_minor.setWidthF(0.5)
        painter.setPen(pen_minor)

        x = minor_spacing
        while x < width:
            painter.drawLine(QPointF(x, 0.0), QPointF(x, float(height)))
            x += minor_spacing

        y = minor_spacing
        while y < height:
            painter.drawLine(QPointF(0.0, y), QPointF(float(width), y))
            y += minor_spacing

        # Major grid lines (every 100px at zoom=1)
        pen_major = QPen(self._GRAPH_MAJOR_COLOR)
        pen_major.setWidthF(1.0)
        painter.setPen(pen_major)

        x = major_spacing
        while x < width:
            painter.drawLine(QPointF(x, 0.0), QPointF(x, float(height)))
            x += major_spacing

        y = major_spacing
        while y < height:
            painter.drawLine(QPointF(0.0, y), QPointF(float(width), y))
            y += major_spacing

    # ── Private: Dot Grid ─────────────────────────────────────────────────

    def _draw_dots(
        self,
        painter: QPainter,
        width: int,
        height: int,
        zoom: float,
    ) -> None:
        """Evenly spaced dot pattern."""
        spacing = 20.0 * zoom
        radius = 1.5 * zoom

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._DOT_COLOR)

        x = spacing
        while x < width:
            y = spacing
            while y < height:
                painter.drawEllipse(QPointF(x, y), radius, radius)
                y += spacing
            x += spacing

    # ── Private: Music Staff ──────────────────────────────────────────────

    def _draw_music_staff(
        self,
        painter: QPainter,
        width: int,
        height: int,
        zoom: float,
    ) -> None:
        """Groups of 5 horizontal lines (music staves)."""
        line_spacing = 8.0 * zoom
        group_spacing = 60.0 * zoom
        lines_per_staff = 5

        pen = QPen(self._STAFF_COLOR)
        pen.setWidthF(0.8)
        painter.setPen(pen)

        # Height of a single staff (4 gaps between 5 lines)
        staff_height = line_spacing * (lines_per_staff - 1)

        group_y = group_spacing  # start one group-spacing from the top
        while group_y + staff_height < height:
            for line_idx in range(lines_per_staff):
                y = group_y + line_idx * line_spacing
                painter.drawLine(QPointF(0.0, y), QPointF(float(width), y))
            group_y += staff_height + group_spacing

    # ── Private: Cornell Notes ────────────────────────────────────────────

    def _draw_cornell(
        self,
        painter: QPainter,
        width: int,
        height: int,
        zoom: float,
    ) -> None:
        """Cornell note-taking template with cue column and summary row."""
        cue_x = width * 0.30
        summary_y = height * 0.85

        pen = QPen(self._CORNELL_DIVIDER_COLOR)
        pen.setWidthF(1.5)
        painter.setPen(pen)

        # Vertical divider — cue column
        painter.drawLine(QPointF(cue_x, 0.0), QPointF(cue_x, summary_y))

        # Horizontal divider — summary row
        painter.drawLine(QPointF(0.0, summary_y), QPointF(float(width), summary_y))

        # Subtle zone labels
        label_font = QFont("Segoe UI", max(8, int(9 * zoom)))
        label_font.setItalic(True)
        painter.setFont(label_font)
        painter.setPen(self._CORNELL_LABEL_COLOR)

        label_margin = 8.0 * zoom

        # "Cue / Questions" label
        painter.drawText(
            QRectF(label_margin, label_margin, cue_x - 2 * label_margin, 30.0 * zoom),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "Cues / Questions",
        )

        # "Notes" label
        painter.drawText(
            QRectF(cue_x + label_margin, label_margin,
                   width - cue_x - 2 * label_margin, 30.0 * zoom),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "Notes",
        )

        # "Summary" label
        painter.drawText(
            QRectF(label_margin, summary_y + label_margin,
                   width - 2 * label_margin, 30.0 * zoom),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "Summary",
        )
