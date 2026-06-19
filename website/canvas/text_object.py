"""
AirWrite Studio — Text Object
==================================
A placeable text block for the drawing canvas.  Recognized handwriting
(or user-typed text) is wrapped in a :class:`TextBlock` that supports
selection, hit-testing, and drag-move — exactly like
:class:`canvas.objects.CanvasObject`.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)


# ─── Text Block ──────────────────────────────────────────────────────────────

class TextBlock:
    """
    A block of text that can be rendered on the canvas.

    The public interface intentionally mirrors
    :class:`canvas.objects.CanvasObject` so the canvas engine can manage
    both stroke objects and text objects uniformly:

    * ``offset``  / ``selected``
    * ``contains_point(point, threshold)``
    * ``translated_bounding_rect()``
    * ``apply_offset()``

    Attributes:
        text:        The recognized (or user-supplied) text content.
        position:    Top-left anchor point on the canvas.
        font_size:   Font size in points.
        color:       Text foreground colour.
        font_family: Font family name.
        offset:      Temporary translation for drag/move operations.
        selected:    Whether this text block is currently selected.
    """

    def __init__(
        self,
        text: str,
        position: QPointF,
        font_size: float = 16.0,
        color: QColor | None = None,
        font_family: str = "Segoe UI",
    ) -> None:
        self.text: str = text
        self.position: QPointF = QPointF(position)
        self.font_size: float = font_size
        self.color: QColor = QColor(color) if color is not None else QColor("#FFFFFF")
        self.font_family: str = font_family

        # CanvasObject-compatible state
        self.offset: QPointF = QPointF(0.0, 0.0)
        self.scale: float = 1.0
        self.selected: bool = False

    # ─── Font Helper ─────────────────────────────────────────────────────

    def _font(self) -> QFont:
        """Build the QFont from the current family and size."""
        font = QFont(self.font_family)
        font.setPointSizeF(self.font_size)
        return font

    # ─── Geometry ────────────────────────────────────────────────────────

    def bounding_rect(self) -> QRectF:
        """
        Compute the bounding rectangle of the text at its current
        position using :class:`QFontMetricsF`.

        Multi-line text is handled by :pymethod:`QFontMetricsF.boundingRect`
        with a sufficiently large bounding box.

        Returns:
            QRectF that tightly encloses the rendered text, anchored at
            :attr:`position`.
        """
        fm = QFontMetricsF(self._font())

        # Split into lines and measure each independently for accuracy
        lines = self.text.split("\n") if self.text else [""]
        line_height = fm.height()
        max_width = 0.0
        for line in lines:
            w = fm.horizontalAdvance(line)
            if w > max_width:
                max_width = w

        total_height = line_height * len(lines)

        # Small padding for visual comfort
        padding = 6.0
        return QRectF(
            self.position.x() - padding,
            self.position.y() - padding,
            max_width + 2 * padding,
            total_height + 2 * padding,
        )

    def translated_bounding_rect(self) -> QRectF:
        """
        Bounding rectangle with the current drag/move :attr:`offset`
        and :attr:`scale` applied.

        Returns:
            QRectF translated by *offset* and scaled by *scale*.
        """
        rect = self.bounding_rect()
        if self.scale != 1.0:
            c = rect.center()
            rect = QRectF(
                c.x() + (rect.x() - c.x()) * self.scale,
                c.y() + (rect.y() - c.y()) * self.scale,
                rect.width() * self.scale,
                rect.height() * self.scale
            )
        if self.offset.x() != 0.0 or self.offset.y() != 0.0:
            rect.translate(self.offset)
        return rect

    def translated_position(self) -> QPointF:
        """
        The anchor position with the drag/move :attr:`offset` applied.

        Returns:
            QPointF equal to ``position + offset``.
        """
        return QPointF(
            self.position.x() + self.offset.x(),
            self.position.y() + self.offset.y(),
        )

    # ─── Hit Testing ─────────────────────────────────────────────────────

    def contains_point(self, point: QPointF, threshold: float) -> bool:
        """
        Determine whether *point* falls inside the bounding rectangle
        (expanded by *threshold* on every side).

        Args:
            point:     Query point in canvas coordinates.
            threshold: Extra margin in pixels added around the bounding
                       rect to make selection easier.

        Returns:
            True if *point* is inside the expanded rect.
        """
        rect = self.translated_bounding_rect().adjusted(
            -threshold, -threshold, threshold, threshold
        )
        return rect.contains(point)

    # ─── Transform ───────────────────────────────────────────────────────

    def apply_transforms(self) -> None:
        """
        Bake the current :attr:`offset` and :attr:`scale` into :attr:`position` permanently.

        Called after a move/scale operation is finalised.
        """
        if self.offset.x() == 0.0 and self.offset.y() == 0.0 and self.scale == 1.0:
            return
        
        # Apply scaling to the position (relative to center)
        if self.scale != 1.0:
            rect = self.bounding_rect()
            c = rect.center()
            self.position = QPointF(
                c.x() + (self.position.x() - c.x()) * self.scale,
                c.y() + (self.position.y() - c.y()) * self.scale
            )
            self.font_size *= self.scale
            
        self.position = QPointF(
            self.position.x() + self.offset.x(),
            self.position.y() + self.offset.y(),
        )
        self.offset = QPointF(0.0, 0.0)
        self.scale = 1.0

    # ─── Rendering ───────────────────────────────────────────────────────

    def render(self, painter: QPainter) -> None:
        """
        Draw the text block onto *painter*.

        Rendering steps:
        1. Draw a semi-transparent rounded-rectangle background behind the
           text for readability.
        2. Draw the text itself with antialiasing using the configured font,
           colour, family, and size.

        Args:
            painter: An active QPainter to draw on.
        """
        painter.save()

        # Build font, resolving the current visual font size (including scale)
        font = QFont(self.font_family)
        font.setPointSizeF(self.font_size * self.scale)
        fm = QFontMetricsF(font)

        # Draw from the translated bounding rect (which includes offset and scale)
        rect = self.translated_bounding_rect()
        padding = 6.0 * self.scale

        lines = self.text.split("\n") if self.text else [""]
        line_height = fm.height()

        # ── Background rect ───────────────────────────────────────────
        rect = self.translated_bounding_rect()
        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, 6.0, 6.0)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # transparent background
        painter.drawPath(bg_path)

        # ── Selection highlight ───────────────────────────────────────
        if self.selected:
            sel_pen = QPen(QColor("#4FC3F7"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(bg_path)

        # ── Text ──────────────────────────────────────────────────────
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(font)
        painter.setPen(QPen(self.color))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw each line; baseline is offset from the top by ascent plus scaled padding
        x = rect.x() + padding
        y = rect.y() + padding + fm.ascent()
        for line in lines:
            painter.drawText(QPointF(x, y), line)
            y += line_height

        painter.restore()
