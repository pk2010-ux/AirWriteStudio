"""
AirWrite Studio — Image Object
==================================
A placeable image block for the drawing canvas. Imported images
are wrapped in an :class:`ImageObject` that supports selection, hit-testing,
and drag-move — exactly like :class:`canvas.text_object.TextBlock`.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)


# ─── Image Object ────────────────────────────────────────────────────────────

class ImageObject:
    """
    An image that can be rendered on the canvas.

    The public interface intentionally mirrors CanvasObject and TextBlock:
    * ``offset``  / ``selected`` / ``scale``
    * ``contains_point(point, threshold)``
    * ``translated_bounding_rect()``
    * ``apply_transforms()``

    Attributes:
        image:       The QImage content.
        position:    Top-left anchor point on the canvas.
        offset:      Temporary translation for drag/move operations.
        scale:       Current scaling factor.
        selected:    Whether this image is currently selected.
    """

    def __init__(
        self,
        image: QImage,
        position: QPointF,
    ) -> None:
        self.image: QImage = image
        self.position: QPointF = QPointF(position)

        # CanvasObject-compatible state
        self.offset: QPointF = QPointF(0.0, 0.0)
        self.scale: float = 1.0
        self.selected: bool = False

    # ─── Geometry ────────────────────────────────────────────────────────

    def bounding_rect(self) -> QRectF:
        """
        Compute the bounding rectangle of the image at its base position.
        """
        if self.image.isNull():
            return QRectF(self.position, self.position)
        return QRectF(self.position.x(), self.position.y(),
                      self.image.width(), self.image.height())

    def translated_bounding_rect(self) -> QRectF:
        """
        Bounding rectangle with the current drag/move offset and scale applied.
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
        """The anchor position with the offset applied."""
        return QPointF(
            self.position.x() + self.offset.x(),
            self.position.y() + self.offset.y(),
        )

    # ─── Hit Testing ─────────────────────────────────────────────────────

    def contains_point(self, point: QPointF, threshold: float) -> bool:
        """Determine whether point falls inside the bounding rectangle."""
        rect = self.translated_bounding_rect().adjusted(
            -threshold, -threshold, threshold, threshold
        )
        return rect.contains(point)

    # ─── Transform ───────────────────────────────────────────────────────

    def apply_transforms(self) -> None:
        """Bake offset and scale into position permanently."""
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
            
            # Actually scale the QImage so bounding_rect size matches visual scale
            new_width = int(self.image.width() * self.scale)
            new_height = int(self.image.height() * self.scale)
            if new_width > 0 and new_height > 0:
                self.image = self.image.scaled(
                    new_width, new_height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
        self.position = QPointF(
            self.position.x() + self.offset.x(),
            self.position.y() + self.offset.y(),
        )
        self.offset = QPointF(0.0, 0.0)
        self.scale = 1.0

    # ─── Rendering ───────────────────────────────────────────────────────

    def render(self, painter: QPainter) -> None:
        """Draw the image onto painter."""
        if self.image.isNull():
            return

        painter.save()
        rect = self.translated_bounding_rect()

        # Draw Image
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(rect, self.image)

        # Draw selection highlight
        if self.selected:
            sel_pen = QPen(QColor("#4FC3F7"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        painter.restore()
