"""
AirWrite Studio — OCR Engine
==================================
Wrapper around Tesseract OCR for converting handwritten strokes rendered
on a QImage into recognized text.  All pytesseract imports are guarded
so the module is always importable even when Tesseract is not installed.
"""

import platform
import sys
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPainter, QPen, QColor

# ─── Optional Tesseract Import ───────────────────────────────────────────────

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    _PYTESSERACT_AVAILABLE = False


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _qimage_to_numpy(image: QImage) -> np.ndarray:
    """
    Convert a QImage to a NumPy array in RGB format.

    The QImage is first converted to Format_RGB888 so the resulting array
    has shape ``(height, width, 3)`` with dtype ``uint8``.

    Args:
        image: Source QImage (any format).

    Returns:
        NumPy array with shape (H, W, 3) and dtype uint8.
    """
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    width = image.width()
    height = image.height()
    bytes_per_line = image.bytesPerLine()

    ptr = image.bits()
    ptr.setsize(height * bytes_per_line)
    arr = np.array(ptr, dtype=np.uint8).reshape((height, bytes_per_line))

    # bytesPerLine may include padding; slice to actual pixel data
    return arr[:, : width * 3].reshape((height, width, 3))


# ─── OCR Engine ──────────────────────────────────────────────────────────────

class OCREngine:
    """
    Tesseract OCR wrapper for AirWrite Studio.

    Provides methods to:
    * Check Tesseract availability at runtime.
    * Convert QImage pixel data to a pre-processed OpenCV image.
    * Run OCR and return cleaned text.
    * Render a list of strokes to a high-contrast QImage suitable for OCR.
    """

    # ─── Availability ────────────────────────────────────────────────────

    @classmethod
    def is_available(cls) -> bool:
        """
        Check whether pytesseract is importable **and** the Tesseract
        binary can be found on the system PATH.

        Returns:
            True if OCR can be performed, False otherwise.
        """
        if not _PYTESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def get_install_instructions() -> str:
        """
        Return platform-specific installation instructions for Tesseract
        and the pytesseract Python binding.

        Returns:
            A human-readable multi-line string with install steps.
        """
        system = platform.system().lower()
        lines = ["Tesseract OCR is required for handwriting recognition.\n"]

        if system == "windows":
            lines.append("Windows:")
            lines.append("  1. Download the installer from:")
            lines.append(
                "     https://github.com/UB-Mannheim/tesseract/wiki"
            )
            lines.append("  2. Run the installer (add Tesseract to PATH).")
            lines.append("  3. pip install pytesseract")
        elif system == "darwin":
            lines.append("macOS:")
            lines.append("  1. brew install tesseract")
            lines.append("  2. pip install pytesseract")
        else:
            lines.append("Linux (Debian/Ubuntu):")
            lines.append("  1. sudo apt install tesseract-ocr")
            lines.append("  2. pip install pytesseract")

        return "\n".join(lines)

    # ─── Recognition ─────────────────────────────────────────────────────

    @classmethod
    def recognize(
        cls,
        image: QImage,
        region: Optional[QRectF] = None,
    ) -> str:
        """
        Run Tesseract OCR on *image* and return the recognized text.

        Processing pipeline:
        1. Optionally crop to *region*.
        2. Convert QImage → NumPy RGB array.
        3. Convert to grayscale.
        4. Apply adaptive thresholding.
        5. Invert colours (canvas has light strokes on a dark background,
           but Tesseract expects dark text on a light background).
        6. Run pytesseract with ``--psm 6 --oem 3``.
        7. Strip and return the result.

        Args:
            image:  Source QImage (typically rendered strokes).
            region: Optional sub-region to crop before OCR.

        Returns:
            Recognized text (may be empty if nothing is detected).

        Raises:
            RuntimeError: If Tesseract is not available.
        """
        if not cls.is_available():
            raise RuntimeError(
                "Tesseract OCR is not available.\n"
                + cls.get_install_instructions()
            )

        # ── Crop ──────────────────────────────────────────────────────
        if region is not None and region.isValid():
            x = max(0, int(region.x()))
            y = max(0, int(region.y()))
            w = min(int(region.width()), image.width() - x)
            h = min(int(region.height()), image.height() - y)
            image = image.copy(x, y, w, h)

        # ── QImage → NumPy ────────────────────────────────────────────
        rgb = _qimage_to_numpy(image)

        # ── Pre-process for OCR ───────────────────────────────────────
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        # Adaptive threshold handles uneven lighting / gradients
        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

        # Do NOT invert: canvas draws black strokes on white background in render_strokes_to_image
        # so thresh is already dark-on-light.

        # ── OCR ───────────────────────────────────────────────────────
        config = "--psm 6 --oem 3"
        raw_text: str = pytesseract.image_to_string(thresh, config=config)

        # Clean up
        text = raw_text.strip()
        return text

    # ─── Stroke Rendering ────────────────────────────────────────────────

    @staticmethod
    def render_strokes_to_image(
        strokes: list,
        width: int,
        height: int,
    ) -> QImage:
        """
        Render a list of stroke-like objects onto a high-contrast QImage
        suitable for OCR (black strokes on a white background).

        Each element in *strokes* must expose:
        * ``points`` — an iterable of ``QPointF``
        * ``width``  — stroke width (float)

        This matches :class:`canvas.objects.Stroke` and the ``stroke``
        attribute of :class:`canvas.objects.CanvasObject`.

        Args:
            strokes: Iterable of stroke objects.
            width:   Output image width in pixels.
            height:  Output image height in pixels.

        Returns:
            QImage with Format_RGB888, white background, black strokes.
        """
        image = QImage(width, height, QImage.Format.Format_RGB888)
        image.fill(QColor(255, 255, 255))  # white background

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(QColor(0, 0, 0))  # black ink
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        for stroke in strokes:
            pen.setWidthF(stroke.width)
            painter.setPen(pen)

            points = stroke.points
            if not points:
                continue

            if len(points) == 1:
                painter.drawPoint(points[0])
                continue

            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        painter.end()
        return image
