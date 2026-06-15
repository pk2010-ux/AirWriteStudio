"""
AirWrite Studio - Toast Widget
================================
A floating notification widget that appears at the top-centre of its
parent to show transient feedback messages.

Minimal, professional styling — solid background, subtle shadow,
clean typography. No gradient borders or glow effects.
"""

from typing import Optional

from PyQt6.QtCore import (
    Qt,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QTimer,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


# ─── Constants ───────────────────────────────────────────────────────────────

_BORDER_RADIUS: int = 8
_PADDING_H: int = 16
_PADDING_V: int = 8
_TOP_MARGIN: int = 16
_BG_COLOR = QColor(38, 38, 38, 240)        # #262626
_TEXT_COLOR = QColor(237, 237, 237)          # #EDEDED
_BORDER_COLOR = QColor(58, 58, 58, 180)     # subtle border
_BORDER_WIDTH: float = 1.0
_SHADOW_BLUR: int = 20
_SHADOW_COLOR = QColor(0, 0, 0, 80)
_FONT_SIZE: int = 12
_DEFAULT_DURATION_MS: int = 2000
_FADE_DURATION_MS: int = 300


class ToastWidget(QWidget):
    """
    Minimal floating notification toast.

    Displays a short message at the top-centre of its parent widget,
    then smoothly fades out after a configurable duration.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SubWindow
        )

        self._message: str = ''
        self._icon: str = ''

        self._msg_font = QFont('Inter', _FONT_SIZE)
        self._msg_font.setWeight(QFont.Weight.Medium)

        self._icon_font = QFont('Segoe UI', _FONT_SIZE)
        self._icon_font.setWeight(QFont.Weight.Medium)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(_SHADOW_BLUR)
        shadow.setColor(_SHADOW_COLOR)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        self._fade_anim = QPropertyAnimation(self, b'windowOpacity', self)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.setDuration(_FADE_DURATION_MS)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._start_fade_out)

        self.hide()

    def show_toast(
        self,
        message: str,
        icon: str = '',
        duration_ms: int = _DEFAULT_DURATION_MS,
    ) -> None:
        """Show (or replace) a toast notification."""
        self._fade_anim.stop()
        self._dismiss_timer.stop()

        self._message = message
        self._icon = icon

        self._resize_to_content()

        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

        self._dismiss_timer.start(duration_ms)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        half = _BORDER_WIDTH / 2.0

        rect = QRectF(half, half, w - _BORDER_WIDTH, h - _BORDER_WIDTH)
        path = QPainterPath()
        path.addRoundedRect(rect, _BORDER_RADIUS, _BORDER_RADIUS)

        # Solid background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_BG_COLOR)
        painter.drawPath(path)

        # Subtle border
        painter.setPen(QPen(_BORDER_COLOR, _BORDER_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, _BORDER_RADIUS, _BORDER_RADIUS)

        # Text
        x_cursor = _PADDING_H

        if self._icon:
            painter.setFont(self._icon_font)
            painter.setPen(_TEXT_COLOR)
            metrics = painter.fontMetrics()
            icon_w = metrics.horizontalAdvance(self._icon)
            y = (h + metrics.ascent() - metrics.descent()) // 2
            painter.drawText(x_cursor, y, self._icon)
            x_cursor += icon_w + 6

        if self._message:
            painter.setFont(self._msg_font)
            painter.setPen(_TEXT_COLOR)
            metrics = painter.fontMetrics()
            y = (h + metrics.ascent() - metrics.descent()) // 2
            painter.drawText(x_cursor, y, self._message)

        painter.end()

    def _resize_to_content(self) -> None:
        from PyQt6.QtGui import QFontMetrics

        total_width = _PADDING_H * 2

        if self._icon:
            fm_icon = QFontMetrics(self._icon_font)
            total_width += fm_icon.horizontalAdvance(self._icon) + 6

        fm_msg = QFontMetrics(self._msg_font)
        total_width += fm_msg.horizontalAdvance(self._message)

        total_height = fm_msg.height() + _PADDING_V * 2

        self.setFixedSize(total_width, total_height)
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = _TOP_MARGIN
        self.move(x, y)

    def _start_fade_out(self) -> None:
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        self.hide()
