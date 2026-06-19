"""
AirWrite Studio - Camera Widget
=================================
Small webcam preview widget for the sidebar with rounded corners
and a placeholder display when no camera feed is available.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPainter, QPixmap, QPainterPath, QColor, QFont

from config import CAMERA_PREVIEW_WIDTH, CAMERA_PREVIEW_HEIGHT


class CameraWidget(QWidget):
    """
    Compact webcam preview widget designed to embed in the sidebar.
    
    Features:
    - Displays camera frames with rounded corners
    - Shows a placeholder when no frame is available
    - Maintains aspect ratio during scaling
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame: QPixmap | None = None
        self._corner_radius = 12

        # Fixed size for sidebar embedding
        self.setFixedSize(CAMERA_PREVIEW_WIDTH, CAMERA_PREVIEW_HEIGHT)

    def update_frame(self, qimage: QImage):
        """
        Update the displayed camera frame.
        
        Args:
            qimage: Camera frame as QImage (from HandTracker)
        """
        # Scale to widget size maintaining aspect ratio
        pixmap = QPixmap.fromImage(qimage)
        self._frame = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.update()

    def paintEvent(self, event):
        """
        Draw the camera frame with rounded corners, or a placeholder.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Create rounded clipping path
        clip_path = QPainterPath()
        clip_path.addRoundedRect(
            QRectF(0, 0, self.width(), self.height()),
            self._corner_radius, self._corner_radius,
        )
        painter.setClipPath(clip_path)

        if self._frame is not None:
            # Draw the camera frame, centered
            x = (self.width() - self._frame.width()) // 2
            y = (self.height() - self._frame.height()) // 2
            painter.drawPixmap(x, y, self._frame)
        else:
            # Draw placeholder
            self._draw_placeholder(painter)

        # Draw subtle border
        painter.setClipping(False)
        painter.setPen(QColor("#2a2a4a"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            self._corner_radius, self._corner_radius,
        )

        painter.end()

    def _draw_placeholder(self, painter: QPainter):
        """Draw a placeholder with camera icon when no feed is available."""
        # Dark background
        painter.fillRect(self.rect(), QColor("#12121f"))

        # Camera icon (emoji)
        painter.setPen(QColor("#3a3a5c"))
        icon_font = QFont("Segoe UI Emoji", 32)
        painter.setFont(icon_font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "📷")

        # "No camera" text below
        painter.setPen(QColor("#5a5a7a"))
        text_font = QFont("Segoe UI", 10)
        painter.setFont(text_font)
        text_rect = QRectF(0, self.height() * 0.6, self.width(), 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter, "Camera Off")
