"""
AirWrite Studio - Canvas Widget
==================================
PyQt6 widget that renders the drawing canvas with all strokes,
cursor indicators, selection highlights, and background support.

Extended with:
- Grid/template background rendering
- Laser pointer strokes with glow and fade effects
- Highlighter strokes (behind regular strokes)
- Variable-width stroke rendering
- Shape rendering (recognized geometry)
- Text block rendering (from OCR)
- Zoom and pan viewport transforms
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QImage, QPainterPath,
    QRadialGradient, QFont, QTransform,
)

from canvas.canvas_engine import CanvasEngine
from config import (
    GestureMode, DEFAULT_PEN_COLOR, DEFAULT_PEN_SIZE, DEFAULT_ERASER_SIZE,
    CANVAS_BACKGROUND_COLOR, LASER_FADE_DURATION, LASER_GLOW_RADIUS,
)


class CanvasWidget(QOpenGLWidget):
    """
    Widget that renders the drawing canvas.

    Displays:
    - Background color or image
    - Grid/template overlays
    - All completed strokes from the engine (highlighter → regular → laser)
    - Current in-progress stroke
    - Text blocks
    - Selection highlights (dashed rectangle)
    - Cursor indicator (varies by gesture mode)

    Supports:
    - Variable-width strokes
    - Shape rendering

    The widget repaints whenever:
    - The engine emits objects_changed
    - The cursor position or mode changes
    - A laser fade tick fires
    """

    def __init__(self, engine: CanvasEngine, parent=None):
        super().__init__(parent)
        self.engine = engine

        # Connect engine signal to trigger repaint
        self.engine.objects_changed.connect(self.update)

        # Cursor state
        self._cursor_pos: QPointF | None = None
        self._cursor_mode: GestureMode = GestureMode.NEUTRAL

        # Tool settings
        self.pen_color = QColor(DEFAULT_PEN_COLOR)
        self.pen_size = DEFAULT_PEN_SIZE
        self.eraser_size = DEFAULT_ERASER_SIZE

        # Background
        self._background_image: QImage | None = None
        self._bg_color = QColor(CANVAS_BACKGROUND_COLOR)

        # Grid
        self._grid_type = None  # GridType enum or None
        self._grid_renderer = None



        # Laser fade timer (runs at 60fps when laser strokes exist)
        self._laser_timer = QTimer(self)
        self._laser_timer.setInterval(16)  # ~60fps
        self._laser_timer.timeout.connect(self._on_laser_tick)

        # Widget settings
        self.setMinimumSize(400, 300)
        self.setSizePolicy(
            self.sizePolicy().Policy.Expanding,
            self.sizePolicy().Policy.Expanding,
        )

        # Enable Drag and Drop
        self.setAcceptDrops(True)

        # Cursor trail for visual feedback
        self._cursor_trail: list[QPointF] = []
        self._max_trail = 5

    # ─── Public API ──────────────────────────────────────────────────────

    def set_cursor(self, pos: QPointF | None, mode: GestureMode):
        """
        Update the cursor position and mode, then trigger repaint.

        Args:
            pos: Cursor position in canvas coordinates, or None
            mode: Current gesture mode (determines cursor appearance)
        """
        self._cursor_pos = pos
        self._cursor_mode = mode

        # Update cursor trail for smooth visual feedback
        if pos is not None:
            self._cursor_trail.append(QPointF(pos))
            if len(self._cursor_trail) > self._max_trail:
                self._cursor_trail.pop(0)
        else:
            self._cursor_trail.clear()

        self.update()

    def set_pen_color(self, color: QColor):
        """Set the pen color for future strokes."""
        self.pen_color = QColor(color)

    def set_pen_size(self, size: float):
        """Set the pen size for future strokes."""
        self.pen_size = size

    def set_eraser_size(self, size: float):
        """Set the eraser circle radius."""
        self.eraser_size = size

    def set_background_image(self, image: QImage | None):
        """Set a background image for the canvas."""
        self._background_image = image
        self.update()

    def clear_background(self):
        """Remove the background image."""
        self._background_image = None
        self.update()

    def set_light_mode(self, is_light: bool):
        """Toggle canvas between dark blueprint and light paper theme."""
        if is_light:
            self._bg_color = QColor("#F8F9FA") # Light paper
        else:
            self._bg_color = QColor(CANVAS_BACKGROUND_COLOR) # Dark blueprint
        self.update()

    def set_grid_type(self, grid_type):
        """
        Set the grid/template background type.

        Args:
            grid_type: GridType enum value, or None for no grid
        """
        self._grid_type = grid_type
        # Lazy-initialize grid renderer
        if grid_type is not None and self._grid_renderer is None:
            try:
                from canvas.grid_renderer import GridRenderer
                self._grid_renderer = GridRenderer()
            except ImportError:
                pass
        self.update()

    # ─── Coordinates ───────────────────────────────────────────────────────

    def screen_to_canvas(self, screen_point: QPointF) -> QPointF:
        """
        Convert a screen/widget coordinate to canvas coordinate.
        (Now 1:1 since global zoom/pan is removed)
        """
        return QPointF(screen_point.x(), screen_point.y())

    def canvas_to_screen(self, canvas_point: QPointF) -> QPointF:
        """
        Convert a canvas coordinate to screen/widget coordinate.
        (Now 1:1 since global zoom/pan is removed)
        """
        return QPointF(canvas_point.x(), canvas_point.y())

    # ─── Laser Timer ─────────────────────────────────────────────────────

    def start_laser_timer(self):
        """Start the laser fade timer if not already running."""
        if not self._laser_timer.isActive():
            self._laser_timer.start()

    def _on_laser_tick(self):
        """Called by the laser timer — update fading and remove expired strokes."""
        has_active_laser = self.engine.tick_laser_strokes()
        if has_active_laser:
            self.update()  # Continue repainting for fade animation
        else:
            self._laser_timer.stop()  # No more laser strokes, stop timer

    # ─── Paint Event ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Render the entire canvas.

        Draw order (back to front):
        1. Background (color or image)
        2. Grid overlay
        3. Highlighter strokes (behind everything)
        4. Regular strokes + shape strokes
        5. Laser strokes (with glow + fade)
        6. Variable-width strokes
        7. In-progress stroke
        8. Text blocks
        9. Selection highlights
        10. Cursor indicator (always on top, no transform)
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Draw background (no transform — fills entire widget)
        self._draw_background(painter)

        # 2. Draw grid overlay (no transform — fills entire widget)
        self._draw_grid(painter)

        painter.save()

        # 3. Draw highlighter strokes (behind everything)
        self._draw_highlighter_strokes(painter)

        # 4. Draw regular strokes
        self._draw_strokes(painter)

        # 5. Draw laser strokes
        self._draw_laser_strokes(painter)

        # 6. Draw current in-progress stroke
        self._draw_current_stroke(painter)

        # 6.5 Draw images (below text blocks)
        self._draw_images(painter)

        # 7. Draw text blocks
        self._draw_text_blocks(painter)

        # 8. Draw selection highlights
        self._draw_selections(painter)

        # 8.5 Draw lasso path
        self._draw_lasso(painter)

        # Restore transform (cursor is in screen space)
        painter.restore()

        # 9. Draw cursor indicator (screen space, on top of everything)
        self._draw_cursor(painter)

        painter.end()

    def _draw_background(self, painter: QPainter):
        """Fill background with color or draw background image."""
        if self._background_image is not None:
            # Scale image to fill the widget while maintaining aspect ratio
            scaled = self._background_image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center the image
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        else:
            painter.fillRect(self.rect(), self._bg_color)

    def _draw_grid(self, painter: QPainter):
        """Draw the grid/template overlay if active."""
        if self._grid_type is None or self._grid_renderer is None:
            return
        # Check if grid type is NONE
        if hasattr(self._grid_type, 'value') and self._grid_type.value == "none":
            return
        self._grid_renderer.draw(painter, self.width(), self.height(),
                                  self._grid_type, 1.0)

    def _draw_highlighter_strokes(self, painter: QPainter):
        """Draw highlighter strokes with semi-transparency (behind regular strokes)."""
        for obj in self.engine.objects:
            if not obj.stroke.is_highlighter:
                continue
            color = QColor(obj.stroke.color)
            color.setAlpha(80)
            pen = QPen(color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(obj.translated_path())

    def _draw_strokes(self, painter: QPainter):
        """Draw all completed regular strokes from the engine."""
        for obj in self.engine.objects:
            # Skip special stroke types
            if obj.stroke.is_highlighter or obj.stroke.is_laser:
                continue

            # Galaxy strokes
            if getattr(obj.stroke, 'is_galaxy', False):
                self._draw_galaxy_stroke(painter, obj)
                continue

            # Variable-width strokes
            if obj.stroke.point_widths and len(obj.stroke.point_widths) > 1:
                self._draw_variable_width_stroke(painter, obj)
                continue

            # Shape strokes
            if obj.stroke.shape_type != "none" and obj.stroke.shape_params:
                self._draw_shape_stroke(painter, obj)
                continue

            # Regular stroke
            pen = QPen(obj.stroke.color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(obj.translated_path())

    def _draw_galaxy_stroke(self, painter: QPainter, obj):
        """Draw a stroke with a beautiful shifting galaxy gradient."""
        from PyQt6.QtGui import QLinearGradient
        rect = obj.translated_bounding_rect()
        if rect.isEmpty():
            return
            
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#FF6B6B")) # Pinkish red
        grad.setColorAt(0.33, QColor("#BB8FCE")) # Purple
        grad.setColorAt(0.66, QColor("#45B7D1")) # Blue
        grad.setColorAt(1.0, QColor("#4ECDC4")) # Teal
        
        pen = QPen(QBrush(grad), obj.stroke.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(obj.translated_path())

    def _draw_variable_width_stroke(self, painter: QPainter, obj):
        """Draw a stroke with per-point variable width."""
        stroke = obj.stroke
        if len(stroke.points) < 2:
            return

        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(stroke.points) - 1):
            # Get width for this segment (average of two endpoints)
            w_idx = min(i, len(stroke.point_widths) - 1)
            w_idx_next = min(i + 1, len(stroke.point_widths) - 1)
            seg_width = (stroke.point_widths[w_idx] + stroke.point_widths[w_idx_next]) / 2.0

            pen = QPen(stroke.color, seg_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            p1 = stroke.points[i]
            p2 = stroke.points[i + 1]
            if obj.offset.x() != 0 or obj.offset.y() != 0:
                p1 = QPointF(p1.x() + obj.offset.x(), p1.y() + obj.offset.y())
                p2 = QPointF(p2.x() + obj.offset.x(), p2.y() + obj.offset.y())
            painter.drawLine(p1, p2)

    def _draw_shape_stroke(self, painter: QPainter, obj):
        """Draw a recognized shape using clean geometry."""
        try:
            from canvas.shape_recognizer import ShapeRecognizer
            shape_path = ShapeRecognizer.shape_to_path(
                obj.stroke.shape_type, obj.stroke.shape_params
            )
            if obj.offset.x() != 0 or obj.offset.y() != 0:
                shape_path.translate(obj.offset)

            pen = QPen(obj.stroke.color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(shape_path)
        except ImportError:
            # Fallback to raw stroke
            pen = QPen(obj.stroke.color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(obj.translated_path())

    def _draw_laser_strokes(self, painter: QPainter):
        """Draw laser pointer strokes with glow effect and fade animation."""
        for obj in self.engine.objects:
            if not obj.stroke.is_laser:
                continue

            opacity = obj.stroke.laser_opacity(LASER_FADE_DURATION)
            if opacity <= 0:
                continue

            # Glow effect
            glow_color = QColor(obj.stroke.color)
            glow_color.setAlpha(int(30 * opacity))
            glow_pen = QPen(glow_color, obj.stroke.width + LASER_GLOW_RADIUS)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(obj.translated_path())

            # Core stroke
            core_color = QColor(obj.stroke.color)
            core_color.setAlpha(int(255 * opacity))
            pen = QPen(core_color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(obj.translated_path())

    def _draw_current_stroke(self, painter: QPainter):
        """Draw the in-progress stroke (if any)."""
        current = self.engine.current_stroke_object
        if current is None:
            return

        stroke = current.stroke

        # Laser in-progress stroke
        if stroke.is_laser:
            glow_color = QColor(stroke.color)
            glow_color.setAlpha(30)
            glow_pen = QPen(glow_color, stroke.width + LASER_GLOW_RADIUS)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(current.translated_path())

            pen = QPen(stroke.color, stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(current.translated_path())
            return

        # Highlighter in-progress stroke
        if stroke.is_highlighter:
            color = QColor(stroke.color)
            color.setAlpha(80)
            pen = QPen(color, stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(current.translated_path())
            return
            
        # Galaxy in-progress stroke
        if getattr(stroke, 'is_galaxy', False):
            self._draw_galaxy_stroke(painter, current)
            return

        # Variable-width in-progress stroke
        if stroke.point_widths and len(stroke.points) >= 2:
            self._draw_variable_width_stroke(painter, current)
            return

        # Regular in-progress stroke
        pen = QPen(stroke.color, stroke.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(current.translated_path())

    def _draw_images(self, painter: QPainter):
        """Draw imported image blocks."""
        for img_obj in self.engine.images:
            img_obj.render(painter)

    def _draw_text_blocks(self, painter: QPainter):
        """Draw OCR text blocks."""
        for text_block in self.engine.text_blocks:
            text_block.render(painter)

    def _draw_selections(self, painter: QPainter):
        """Draw dashed rectangles around selected objects."""
        if not self.engine.selected_objects:
            return

        # Selection highlight style
        sel_pen = QPen(QColor("#4ECDC4"), 2.0, Qt.PenStyle.DashLine)
        painter.setPen(sel_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for obj in self.engine.selected_objects:
            rect = obj.translated_bounding_rect()
            # Add some padding
            rect = rect.adjusted(-4, -4, 4, 4)
            painter.drawRoundedRect(rect, 4, 4)

            # Draw corner handles
            handle_size = 6
            handle_brush = QBrush(QColor("#4ECDC4"))
            painter.setBrush(handle_brush)
            painter.setPen(Qt.PenStyle.NoPen)
            for corner in [rect.topLeft(), rect.topRight(),
                          rect.bottomLeft(), rect.bottomRight()]:
                painter.drawEllipse(corner, handle_size / 2, handle_size / 2)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(sel_pen)

    def _draw_lasso(self, painter: QPainter):
        """Draw the current lasso selection path."""
        lasso = self.engine._lasso_path
        if not lasso or len(lasso) < 2:
            return
            
        lasso_pen = QPen(QColor("#45B7D1"), 2.0, Qt.PenStyle.DashLine)
        painter.setPen(lasso_pen)
        
        # Add light blue semi-transparent fill
        fill_color = QColor("#45B7D1")
        fill_color.setAlpha(40)
        painter.setBrush(QBrush(fill_color))
        
        from PyQt6.QtGui import QPolygonF
        poly = QPolygonF(lasso)
        painter.drawPolygon(poly)

    def _draw_cursor(self, painter: QPainter):
        """Draw the cursor indicator based on current gesture mode."""
        if self._cursor_pos is None:
            return

        x, y = self._cursor_pos.x(), self._cursor_pos.y()

        if self._cursor_mode == GestureMode.PEN:
            self._draw_pen_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.ERASER:
            self._draw_eraser_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.SELECT:
            self._draw_select_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.DRAG:
            self._draw_drag_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.ZOOM_IN:
            self._draw_zoom_in_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.ZOOM_OUT:
            self._draw_zoom_out_cursor(painter, x, y)
        elif self._cursor_mode == GestureMode.NEUTRAL:
            self._draw_neutral_cursor(painter, x, y)

    def _draw_pen_cursor(self, painter: QPainter, x: float, y: float):
        """Pen mode: filled circle in pen color with glow effect."""
        # Outer glow
        glow_radius = self.pen_size + 6
        gradient = QRadialGradient(x, y, glow_radius)
        glow_color = QColor(self.pen_color)
        glow_color.setAlpha(60)
        gradient.setColorAt(0.0, glow_color)
        glow_color.setAlpha(0)
        gradient.setColorAt(1.0, glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(x, y), glow_radius, glow_radius)

        # Inner dot
        painter.setBrush(QBrush(self.pen_color))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.0))
        radius = max(self.pen_size / 2.0, 3.0)
        painter.drawEllipse(QPointF(x, y), radius, radius)

    def _draw_eraser_cursor(self, painter: QPainter, x: float, y: float):
        """Eraser mode: hollow circle showing eraser radius."""
        # Outer circle
        eraser_pen = QPen(QColor("#FF6B6B"), 2.0, Qt.PenStyle.DashLine)
        painter.setPen(eraser_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(x, y), self.eraser_size, self.eraser_size)

        # Inner X mark
        cross_size = 6
        painter.setPen(QPen(QColor("#FF6B6B"), 2.0))
        painter.drawLine(
            QPointF(x - cross_size, y - cross_size),
            QPointF(x + cross_size, y + cross_size),
        )
        painter.drawLine(
            QPointF(x - cross_size, y + cross_size),
            QPointF(x + cross_size, y - cross_size),
        )

    def _draw_select_cursor(self, painter: QPainter, x: float, y: float):
        """Select mode: crosshair cursor."""
        cross_size = 12
        gap = 4
        painter.setPen(QPen(QColor("#45B7D1"), 2.0))

        # Crosshair lines with gap in center
        painter.drawLine(QPointF(x - cross_size, y), QPointF(x - gap, y))
        painter.drawLine(QPointF(x + gap, y), QPointF(x + cross_size, y))
        painter.drawLine(QPointF(x, y - cross_size), QPointF(x, y - gap))
        painter.drawLine(QPointF(x, y + gap), QPointF(x, y + cross_size))

        # Center dot
        painter.setBrush(QBrush(QColor("#45B7D1")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, y), 2, 2)

    def _draw_drag_cursor(self, painter: QPainter, x: float, y: float):
        """Drag mode: four-way arrow cursor."""
        arrow_size = 14
        painter.setPen(QPen(QColor("#FF8C42"), 2.5))

        # Four arrows
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            # Arrow line
            end_x = x + dx * arrow_size
            end_y = y + dy * arrow_size
            painter.drawLine(QPointF(x, y), QPointF(end_x, end_y))

            # Arrow head
            head_size = 4
            if dx != 0:
                painter.drawLine(
                    QPointF(end_x, end_y),
                    QPointF(end_x - dx * head_size, end_y - head_size),
                )
                painter.drawLine(
                    QPointF(end_x, end_y),
                    QPointF(end_x - dx * head_size, end_y + head_size),
                )
            else:
                painter.drawLine(
                    QPointF(end_x, end_y),
                    QPointF(end_x - head_size, end_y - dy * head_size),
                )
                painter.drawLine(
                    QPointF(end_x, end_y),
                    QPointF(end_x + head_size, end_y - dy * head_size),
                )

    def _draw_zoom_in_cursor(self, painter: QPainter, x: float, y: float):
        """Zoom In mode: magnifying glass with plus."""
        painter.setPen(QPen(QColor("#BB8FCE"), 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(x, y), 10, 10)
        painter.drawLine(QPointF(x + 7, y + 7), QPointF(x + 14, y + 14))
        painter.setPen(QPen(QColor("#BB8FCE"), 1.5))
        painter.drawLine(QPointF(x - 4, y), QPointF(x + 4, y))
        painter.drawLine(QPointF(x, y - 4), QPointF(x, y + 4))

    def _draw_zoom_out_cursor(self, painter: QPainter, x: float, y: float):
        """Zoom Out mode: magnifying glass with minus."""
        painter.setPen(QPen(QColor("#BB8FCE"), 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(x, y), 10, 10)
        painter.drawLine(QPointF(x + 7, y + 7), QPointF(x + 14, y + 14))
        painter.setPen(QPen(QColor("#BB8FCE"), 1.5))
        painter.drawLine(QPointF(x - 4, y), QPointF(x + 4, y))

    def _draw_neutral_cursor(self, painter: QPainter, x: float, y: float):
        """Neutral mode: subtle dot indicator."""
        painter.setPen(Qt.PenStyle.NoPen)
        color = QColor("#6C757D")
        color.setAlpha(120)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(x, y), 4, 4)

    # ─── Drag and Drop & Clipboard ───────────────────────────────────────

    def dragEnterEvent(self, event):
        """Accept image drops."""
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle dropped images or files."""
        mime = event.mimeData()
        image = QImage()

        if mime.hasImage():
            image = QImage(mime.imageData())
        elif mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    image.load(url.toLocalFile())
                    if not image.isNull():
                        break

        if not image.isNull():
            pos = self.screen_to_canvas(QPointF(event.position()))
            # Center the image on the drop point
            pos.setX(pos.x() - image.width() / 2)
            pos.setY(pos.y() - image.height() / 2)
            self.engine.add_image(image, pos)
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """Handle clipboard paste for images."""
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtWidgets import QApplication

        if event.matches(QKeySequence.StandardKey.Paste):
            clipboard = QApplication.clipboard()
            mime = clipboard.mimeData()
            image = QImage()

            if mime.hasImage():
                image = QImage(mime.imageData())
            elif mime.hasUrls():
                for url in mime.urls():
                    if url.isLocalFile():
                        image.load(url.toLocalFile())
                        if not image.isNull():
                            break
            
            if not image.isNull():
                # Center on canvas
                pos = QPointF(
                    (self.width() - image.width()) / 2,
                    (self.height() - image.height()) / 2
                )
                self.engine.add_image(image, pos)
                event.accept()
                return

        super().keyPressEvent(event)
