"""
AirWrite Studio - Canvas Engine
==================================
Central engine managing all canvas objects, undo/redo history,
stroke building, erasing, selection, and movement operations.

Extended with:
- Laser pointer strokes (auto-fading, non-undoable)
- Highlighter strokes (semi-transparent, rendered behind)
- Dynamic width strokes (speed-based per-point widths)
- Shape recognition (auto-snap to clean geometry)
- OCR text conversion (strokes → typed text blocks)
"""

import time
from PyQt6.QtCore import QObject, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtCore import Qt

from canvas.objects import Stroke, CanvasObject
from config import MAX_UNDO_STEPS, CANVAS_BACKGROUND_COLOR, LASER_FADE_DURATION


# ─── Undoable Actions ────────────────────────────────────────────────────────

class CanvasAction:
    """Base class for undoable canvas actions."""

    def undo(self, engine: "CanvasEngine"):
        raise NotImplementedError

    def redo(self, engine: "CanvasEngine"):
        raise NotImplementedError


class AddStrokeAction(CanvasAction):
    """Action: a new stroke was added to the canvas."""

    def __init__(self, canvas_object: CanvasObject):
        self.canvas_object = canvas_object

    def undo(self, engine: "CanvasEngine"):
        if self.canvas_object in engine.objects:
            engine.objects.remove(self.canvas_object)

    def redo(self, engine: "CanvasEngine"):
        engine.objects.append(self.canvas_object)


class AddObjectsAction(CanvasAction):
    """Action: one or more objects (strokes, text, or images) were added."""

    def __init__(self, added_objects: list):
        self.added_objects = added_objects

    def undo(self, engine: "CanvasEngine"):
        for obj in self.added_objects:
            from canvas.image_object import ImageObject
            if isinstance(obj, ImageObject):
                if obj in engine.images:
                    engine.images.remove(obj)
            elif hasattr(obj, 'text'):
                if obj in engine.text_blocks:
                    engine.text_blocks.remove(obj)
            else:
                if obj in engine.objects:
                    engine.objects.remove(obj)

    def redo(self, engine: "CanvasEngine"):
        for obj in self.added_objects:
            from canvas.image_object import ImageObject
            if isinstance(obj, ImageObject):
                engine.images.append(obj)
            elif hasattr(obj, 'text'):
                engine.text_blocks.append(obj)
            else:
                engine.objects.append(obj)



class EraseStrokesAction(CanvasAction):
    """Action: one or more strokes were erased."""

    def __init__(self, erased: list[tuple[int, CanvasObject]]):
        """
        Args:
            erased: List of (original_index, canvas_object) tuples
        """
        self.erased = erased

    def undo(self, engine: "CanvasEngine"):
        # Re-insert in original order
        for idx, obj in sorted(self.erased, key=lambda x: x[0]):
            from canvas.image_object import ImageObject
            if isinstance(obj, ImageObject):
                insert_idx = min(idx, len(engine.images))
                engine.images.insert(insert_idx, obj)
            elif hasattr(obj, 'text'): # TextBlock
                insert_idx = min(idx, len(engine.text_blocks))
                engine.text_blocks.insert(insert_idx, obj)
            else:
                insert_idx = min(idx, len(engine.objects))
                engine.objects.insert(insert_idx, obj)

    def redo(self, engine: "CanvasEngine"):
        for _, obj in self.erased:
            if obj in engine.objects:
                engine.objects.remove(obj)
            elif obj in engine.text_blocks:
                engine.text_blocks.remove(obj)
            elif hasattr(engine, 'images') and obj in engine.images:
                engine.images.remove(obj)


class MoveObjectAction(CanvasAction):
    """Action: selected objects were moved."""

    def __init__(self, moved_objects: list[CanvasObject],
                 delta: QPointF):
        self.moved_objects = moved_objects
        self.delta = delta

    def undo(self, engine: "CanvasEngine"):
        reverse = QPointF(-self.delta.x(), -self.delta.y())
        for obj in self.moved_objects:
            obj.stroke.points = [
                QPointF(p.x() + reverse.x(), p.y() + reverse.y())
                for p in obj.stroke.points
            ]

    def redo(self, engine: "CanvasEngine"):
        for obj in self.moved_objects:
            obj.stroke.points = [
                QPointF(p.x() + self.delta.x(), p.y() + self.delta.y())
                for p in obj.stroke.points
            ]

class ScaleObjectAction(CanvasAction):
    """Action: selected objects were scaled."""

    def __init__(self, scaled_objects: list, scale_factors: dict):
        # scale_factors: dict mapping id(obj) to scale factor used
        self.scaled_objects = scaled_objects
        self.scale_factors = scale_factors

    def undo(self, engine: "CanvasEngine"):
        for obj in self.scaled_objects:
            # Apply inverse scale
            inv_scale = 1.0 / self.scale_factors[id(obj)]
            obj.scale = inv_scale
            obj.apply_transforms()

    def redo(self, engine: "CanvasEngine"):
        for obj in self.scaled_objects:
            obj.scale = self.scale_factors[id(obj)]
            obj.apply_transforms()
class ClearAllAction(CanvasAction):
    """Action: all objects were cleared from the canvas."""

    def __init__(self, objects: list[CanvasObject], text_blocks: list, images: list):
        self.objects = objects
        self.text_blocks = text_blocks
        self.images = images

    def undo(self, engine: "CanvasEngine"):
        engine.objects.extend(self.objects)
        engine.text_blocks.extend(self.text_blocks)
        engine.images.extend(self.images)

    def redo(self, engine: "CanvasEngine"):
        engine.objects.clear()
        engine.text_blocks.clear()
        engine.images.clear()


class ConvertToTextAction(CanvasAction):
    """Action: strokes were converted to a text block via OCR."""

    def __init__(self, removed_objects: list[CanvasObject], text_object):
        self.removed_objects = removed_objects
        self.text_object = text_object

    def undo(self, engine: "CanvasEngine"):
        # Remove the text block and restore the original strokes
        if self.text_object in engine.text_blocks:
            engine.text_blocks.remove(self.text_object)
        engine.objects.extend(self.removed_objects)

    def redo(self, engine: "CanvasEngine"):
        for obj in self.removed_objects:
            if obj in engine.objects:
                engine.objects.remove(obj)
        engine.text_blocks.append(self.text_object)


class ShapeSnapAction(CanvasAction):
    """Action: a stroke was snapped to a recognized shape."""

    def __init__(self, canvas_object: CanvasObject,
                 original_points: list[QPointF],
                 original_shape_type: str,
                 original_shape_params: dict | None,
                 new_shape_type: str,
                 new_shape_params: dict):
        self.canvas_object = canvas_object
        self.original_points = original_points
        self.original_shape_type = original_shape_type
        self.original_shape_params = original_shape_params
        self.new_shape_type = new_shape_type
        self.new_shape_params = new_shape_params

    def undo(self, engine: "CanvasEngine"):
        self.canvas_object.stroke.points = self.original_points
        self.canvas_object.stroke.shape_type = self.original_shape_type
        self.canvas_object.stroke.shape_params = self.original_shape_params

    def redo(self, engine: "CanvasEngine"):
        self.canvas_object.stroke.shape_type = self.new_shape_type
        self.canvas_object.stroke.shape_params = self.new_shape_params


# ─── Canvas Engine ───────────────────────────────────────────────────────────

class CanvasEngine(QObject):
    """
    Central engine for the drawing canvas.

    Manages:
    - Object storage (ordered list of CanvasObject)
    - Current stroke building (begin/add/end)
    - Laser pointer strokes (auto-fading)
    - Highlighter strokes
    - Erasing (remove strokes that intersect with eraser circle)
    - Selection and hit testing
    - Move/drag operations
    - Shape recognition
    - OCR text conversion
    - Undo/redo history (command pattern)
    - Export to image

    Signals:
        objects_changed: Emitted whenever the canvas needs repainting
        shape_recognized: Emitted when a shape is auto-detected (shape_type_str)
    """

    objects_changed = pyqtSignal()
    shape_recognized = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # All completed canvas objects
        self.objects: list[CanvasObject] = []

        # Text blocks from OCR conversion
        self.text_blocks: list = []  # List of TextBlock objects

        # Images imported by user
        self.images: list = []  # List of ImageObject objects

        # Current stroke being built (in-progress)
        self._current_stroke: Stroke | None = None
        self._current_object: CanvasObject | None = None

        # Selection state
        self.selected_objects: list[CanvasObject] = []

        # Move/Scale state
        self._move_start: QPointF | None = None
        self._move_objects: list = []
        self._scale_objects: list = []

        # Lasso Selection state
        self._lasso_path: list[QPointF] | None = None

        # Undo/Redo stacks
        self.undo_stack: list[CanvasAction] = []
        self.redo_stack: list[CanvasAction] = []

        # Accumulate erased strokes within a single erase gesture
        self._erase_accumulator: list[tuple[int, CanvasObject]] = []
        self._erasing = False

        # Feature toggles
        self.shape_recognition_enabled = False
        self.dynamic_width_enabled = False

    # ─── Stroke Building ─────────────────────────────────────────────────

    def begin_stroke(self, point: QPointF, color: QColor, width: float,
                     is_laser: bool = False, is_highlighter: bool = False):
        """
        Begin a new stroke at the given point.

        Args:
            point: Starting point in canvas coordinates
            color: Stroke color
            width: Stroke width in pixels
            is_laser: Whether this is a laser pointer stroke
            is_highlighter: Whether this is a highlighter stroke
        """
        self._current_stroke = Stroke(
            points=[point],
            color=QColor(color),  # Copy to avoid reference issues
            width=width,
            timestamp=time.time(),
            is_laser=is_laser,
            is_highlighter=is_highlighter,
            point_widths=[width] if self.dynamic_width_enabled else None,
        )
        self._current_object = CanvasObject(self._current_stroke)
        self.objects_changed.emit()

    def add_point(self, point: QPointF, width_override: float | None = None):
        """
        Add a point to the current in-progress stroke.

        Args:
            point: New point in canvas coordinates
            width_override: Optional per-point width for dynamic width mode
        """
        if self._current_stroke is not None:
            self._current_stroke.points.append(point)
            # Track per-point width for dynamic width strokes
            if self._current_stroke.point_widths is not None and width_override is not None:
                self._current_stroke.point_widths.append(width_override)
            elif self._current_stroke.point_widths is not None:
                self._current_stroke.point_widths.append(self._current_stroke.width)
            self.objects_changed.emit()

    def end_stroke(self) -> CanvasObject | None:
        """
        Finalize the current stroke and add it to the canvas.

        Returns:
            The completed CanvasObject, or None if no stroke was in progress
        """
        if self._current_object is None or self._current_stroke is None:
            return None

        # Only keep strokes with at least 2 points
        if len(self._current_stroke.points) < 2:
            self._current_stroke = None
            self._current_object = None
            self.objects_changed.emit()
            return None

        obj = self._current_object

        # Attempt shape recognition if enabled (not for laser/highlighter)
        if (self.shape_recognition_enabled
                and not self._current_stroke.is_laser
                and not self._current_stroke.is_highlighter):
            self._try_shape_recognition(obj)

        self.objects.append(obj)

        # Laser strokes are not undoable (they vanish on their own)
        if not self._current_stroke.is_laser:
            self._push_action(AddStrokeAction(obj))

        self._current_stroke = None
        self._current_object = None
        self.objects_changed.emit()
        return obj

    @property
    def current_stroke_object(self) -> CanvasObject | None:
        """The in-progress stroke object, for rendering."""
        return self._current_object

    # ─── Shape Recognition ───────────────────────────────────────────────

    def _try_shape_recognition(self, obj: CanvasObject):
        """
        Attempt to recognize a shape in the completed stroke.
        If recognized, replaces the stroke data with clean geometry.
        """
        try:
            from canvas.shape_recognizer import ShapeRecognizer
            recognizer = ShapeRecognizer()
            shape_type, params = recognizer.recognize(obj.stroke.points)

            if shape_type.value != "none" and params is not None:
                # Store original for undo
                original_points = list(obj.stroke.points)
                original_type = obj.stroke.shape_type
                original_params = obj.stroke.shape_params

                # Apply shape
                obj.stroke.shape_type = shape_type.value
                obj.stroke.shape_params = params

                # Emit signal for UI feedback
                self.shape_recognized.emit(shape_type.value)
        except ImportError:
            pass  # shape_recognizer not available

    # ─── Laser Stroke Management ─────────────────────────────────────────

    def tick_laser_strokes(self) -> bool:
        """
        Remove expired laser strokes. Called periodically by a timer.

        Returns:
            True if any strokes were removed (canvas needs repaint)
        """
        expired = [
            obj for obj in self.objects
            if obj.stroke.is_laser and obj.stroke.is_expired(LASER_FADE_DURATION)
        ]
        if expired:
            for obj in expired:
                self.objects.remove(obj)
            return True
        # Check if any laser strokes are still fading (need continuous repaint)
        return any(obj.stroke.is_laser for obj in self.objects)

    # ─── Erasing ─────────────────────────────────────────────────────────

    def begin_erase(self):
        """Start an erase gesture (accumulates erased strokes for one undo action)."""
        self._erase_accumulator = []
        self._erasing = True

    def erase_at(self, point: QPointF, radius: float) -> list[CanvasObject]:
        """
        Erase strokes that intersect with a circle at the given point.

        Args:
            point: Center of the eraser circle
            radius: Eraser radius in pixels

        Returns:
            List of erased CanvasObject instances
        """
        if not self._erasing:
            self.begin_erase()

        erased = []
        for i in range(len(self.objects) - 1, -1, -1):
            obj = self.objects[i]
            # Don't erase laser strokes (they fade on their own)
            if obj.stroke.is_laser:
                continue
            if obj.contains_point(point, radius + obj.stroke.width / 2):
                erased.append((i, obj))
                self.objects.pop(i)
                # Also remove from selection
                if obj in self.selected_objects:
                    self.selected_objects.remove(obj)

        erased_text = []
        for i in range(len(self.text_blocks) - 1, -1, -1):
            tb = self.text_blocks[i]
            if tb.contains_point(point, radius):
                erased_text.append((i, tb))
                self.text_blocks.pop(i)
                if tb in self.selected_objects:
                    self.selected_objects.remove(tb)
                    
        erased_images = []
        for i in range(len(self.images) - 1, -1, -1):
            img = self.images[i]
            if img.contains_point(point, radius):
                erased_images.append((i, img))
                self.images.pop(i)
                if img in self.selected_objects:
                    self.selected_objects.remove(img)

        if erased or erased_text or erased_images:
            self._erase_accumulator.extend(erased)
            self._erase_accumulator.extend(erased_text)
            self._erase_accumulator.extend(erased_images)
            self.objects_changed.emit()

        return [obj for _, obj in erased] + [tb for _, tb in erased_text] + [img for _, img in erased_images]

    def end_erase(self):
        """Finalize the erase gesture and push accumulated erases as one undo action."""
        if self._erase_accumulator:
            self._push_action(EraseStrokesAction(self._erase_accumulator))
        self._erase_accumulator = []
        self._erasing = False

    # ─── Selection ───────────────────────────────────────────────────────

    def select_at(self, point: QPointF, threshold: float = 15.0) -> CanvasObject | None:
        """Select the topmost object at the given point."""
        self.clear_selection()
        
        # Check text blocks first (they render on top)
        for tb in reversed(self.text_blocks):
            if tb.contains_point(point, threshold):
                tb.selected = True
                self.selected_objects.append(tb)
                self.objects_changed.emit()
                return tb

        # Check strokes
        for obj in reversed(self.objects):
            if obj.stroke.is_laser:
                continue
            if obj.contains_point(point, threshold):
                obj.selected = True
                self.selected_objects.append(obj)
                self.objects_changed.emit()
                return obj
                
        # Check images
        for img in reversed(self.images):
            if img.contains_point(point, threshold):
                img.selected = True
                self.selected_objects.append(img)
                self.objects_changed.emit()
                return img

        self.objects_changed.emit()
        return None

    def begin_lasso(self, point: QPointF):
        """Start drawing a lasso selection polygon."""
        self._lasso_path = [point]
        self.clear_selection()
        
    def update_lasso(self, point: QPointF):
        """Add a point to the lasso path."""
        if self._lasso_path is not None:
            self._lasso_path.append(point)
            self.objects_changed.emit()
            
    def end_lasso(self):
        """Finish the lasso and select objects within the polygon."""
        if not self._lasso_path or len(self._lasso_path) < 3:
            self._lasso_path = None
            self.objects_changed.emit()
            return
            
        from PyQt6.QtGui import QPolygonF
        poly = QPolygonF(self._lasso_path)
        
        # We check if an object's bounding box center is inside the polygon
        # Or better, if its bounding rect intersects the polygon
        for tb in self.text_blocks:
            if poly.intersects(QPolygonF(tb.translated_bounding_rect())):
                tb.selected = True
                self.selected_objects.append(tb)
                
        for obj in self.objects:
            if obj.stroke.is_laser:
                continue
            rect = obj.translated_bounding_rect()
            if poly.intersects(QPolygonF(rect)):
                obj.selected = True
                self.selected_objects.append(obj)
                
        for img in self.images:
            if poly.intersects(QPolygonF(img.translated_bounding_rect())):
                img.selected = True
                self.selected_objects.append(img)
                
        self._lasso_path = None
        self.objects_changed.emit()

    def clear_selection(self):
        """Deselect all objects."""
        for obj in self.selected_objects:
            obj.selected = False
        self.selected_objects.clear()
        self.objects_changed.emit()

    # ─── Move/Scale ──────────────────────────────────────────────────────

    def begin_move(self, point: QPointF):
        """
        Start dragging the currently selected objects.

        Args:
            point: Starting drag point in canvas coordinates
        """
        if not self.selected_objects:
            return

        self._move_start = QPointF(point)
        self._move_objects = list(self.selected_objects)

        # Store original offsets
        for obj in self._move_objects:
            obj._move_original_offset = QPointF(obj.offset)

    def update_move(self, point: QPointF):
        """
        Update the drag position for selected objects.

        Args:
            point: Current drag point in canvas coordinates
        """
        if self._move_start is None or not self._move_objects:
            return

        # Calculate delta from move start
        dx = point.x() - self._move_start.x()
        dy = point.y() - self._move_start.y()

        for obj in self._move_objects:
            orig = getattr(obj, '_move_original_offset', QPointF(0, 0))
            obj.offset = QPointF(orig.x() + dx, orig.y() + dy)

        self.objects_changed.emit()

    def end_move(self):
        """
        Finalize the move operation: bake offsets into stroke points
        and push to undo stack.
        """
        if self._move_start is None or not self._move_objects:
            self._move_start = None
            self._move_objects = []
            return

        # Calculate total delta
        total_delta = QPointF(0, 0)
        if self._move_objects:
            obj = self._move_objects[0]
            orig = getattr(obj, '_move_original_offset', QPointF(0, 0))
            total_delta = QPointF(
                obj.offset.x() - orig.x(),
                obj.offset.y() - orig.y(),
            )

        # Bake transforms into points
        for obj in self._move_objects:
            obj.apply_transforms()
            if hasattr(obj, '_move_original_offset'):
                del obj._move_original_offset

        # Push undo action (only if there was actual movement)
        if abs(total_delta.x()) > 1 or abs(total_delta.y()) > 1:
            self._push_action(MoveObjectAction(
                list(self._move_objects), total_delta
            ))

        self._move_start = None
        self._move_objects = []
        self.objects_changed.emit()

    def begin_scale(self):
        """Start scaling the currently selected objects."""
        if not self.selected_objects:
            return
        self._scale_objects = list(self.selected_objects)
        for obj in self._scale_objects:
            obj._scale_original = obj.scale

    def update_scale(self, scale_delta: float):
        """
        Update the scale for selected objects.
        
        Args:
            scale_delta: Relative scaling factor (e.g., 1.05 for 5% increase)
        """
        if not self._scale_objects:
            return
        
        for obj in self._scale_objects:
            orig = getattr(obj, '_scale_original', 1.0)
            from config import OBJECT_SCALE_MIN, OBJECT_SCALE_MAX
            new_scale = max(OBJECT_SCALE_MIN, min(OBJECT_SCALE_MAX, obj.scale * scale_delta))
            obj.scale = new_scale
            
        self.objects_changed.emit()

    def end_scale(self):
        """
        Finalize the scale operation: bake scale into stroke points
        and push to undo stack.
        """
        if not self._scale_objects:
            return

        scale_factors = {}
        for obj in self._scale_objects:
            orig = getattr(obj, '_scale_original', 1.0)
            factor = obj.scale / orig if orig != 0 else 1.0
            scale_factors[id(obj)] = obj.scale
            
            obj.apply_transforms()
            if hasattr(obj, '_scale_original'):
                del obj._scale_original

        if scale_factors:
            self._push_action(ScaleObjectAction(list(self._scale_objects), scale_factors))

        self._scale_objects = []
        self.objects_changed.emit()

    # ─── OCR Text Conversion ────────────────────────────────────────────

    def convert_selection_to_text(self, canvas_width: int, canvas_height: int) -> str | None:
        """
        Convert selected strokes to text using OCR.

        Args:
            canvas_width: Canvas width for rendering
            canvas_height: Canvas height for rendering

        Returns:
            Recognized text string, or None if failed
        """
        if not self.selected_objects:
            return None

        try:
            from canvas.ocr_engine import OCREngine
            from canvas.text_object import TextBlock

            if not OCREngine.is_available():
                return None

            # Render selected strokes to an isolated image
            strokes = [obj.stroke for obj in self.selected_objects]
            image = OCREngine.render_strokes_to_image(strokes, canvas_width, canvas_height)

            # Compute bounding region of selected strokes
            combined_rect = QRectF()
            for obj in self.selected_objects:
                if combined_rect.isNull():
                    combined_rect = obj.translated_bounding_rect()
                else:
                    combined_rect = combined_rect.united(obj.translated_bounding_rect())

            # Run OCR
            text = OCREngine.recognize(image, combined_rect)
            if not text or not text.strip():
                return None

            # Create text block at the position of the original strokes
            text_block = TextBlock(
                text=text.strip(),
                position=QPointF(combined_rect.x(), combined_rect.y()),
                font_size=max(14.0, combined_rect.height() * 0.4),
                color=QColor(self.selected_objects[0].stroke.color),
            )

            # Remove original strokes and add text block (undoable)
            removed = list(self.selected_objects)
            for obj in removed:
                if obj in self.objects:
                    self.objects.remove(obj)
            self.selected_objects.clear()

            self.text_blocks.append(text_block)
            self._push_action(ConvertToTextAction(removed, text_block))
            self.objects_changed.emit()
            return text.strip()

        except ImportError:
            return None

    # ─── Object Insertion & Deletion ─────────────────────────────────────────

    def delete_selection(self) -> None:
        """Delete all currently selected objects."""
        if not self.selected_objects:
            return

        erased = []
        for obj in self.selected_objects:
            from canvas.image_object import ImageObject
            if isinstance(obj, ImageObject):
                if obj in self.images:
                    erased.append((self.images.index(obj), obj))
                    self.images.remove(obj)
            elif hasattr(obj, 'text'):
                if obj in self.text_blocks:
                    erased.append((self.text_blocks.index(obj), obj))
                    self.text_blocks.remove(obj)
            else:
                if obj in self.objects:
                    erased.append((self.objects.index(obj), obj))
                    self.objects.remove(obj)

        if erased:
            self._add_undo_action(EraseStrokesAction(erased))
            self.selected_objects.clear()
            self.objects_changed.emit()

    def duplicate_selection(self) -> None:
        """Duplicate all currently selected objects."""
        if not self.selected_objects:
            return

        from canvas.image_object import ImageObject
        from canvas.text_object import TextBlock
        import copy

        new_objects = []
        OFFSET = QPointF(20.0, 20.0)

        for obj in self.selected_objects:
            if isinstance(obj, ImageObject):
                new_img = ImageObject(obj.image_path, obj.position + OFFSET)
                new_img.scale = obj.scale
                new_objects.append(new_img)
                self.images.append(new_img)
            elif hasattr(obj, 'text'):
                new_txt = TextBlock(obj.text, obj.position + OFFSET, obj.font_size, obj.color, obj.font_family)
                new_txt.scale = obj.scale
                new_objects.append(new_txt)
                self.text_blocks.append(new_txt)
            else:
                # CanvasObject (Stroke)
                new_stroke = Stroke(obj.stroke.color, obj.stroke.thickness)
                new_stroke.points = [QPointF(p.x() + OFFSET.x(), p.y() + OFFSET.y()) for p in obj.stroke.points]
                new_stroke.shape_type = obj.stroke.shape_type
                new_stroke.shape_params = copy.deepcopy(obj.stroke.shape_params) if obj.stroke.shape_params else None
                new_stroke.is_laser = obj.stroke.is_laser
                new_stroke.is_highlighter = obj.stroke.is_highlighter
                new_stroke.widths = list(obj.stroke.widths)
                new_obj = CanvasObject(new_stroke)
                new_objects.append(new_obj)
                self.objects.append(new_obj)

        if new_objects:
            # Select the newly duplicated objects
            self.clear_selection()
            self.selected_objects = new_objects
            for o in self.selected_objects:
                o.selected = True

            self._add_undo_action(AddObjectsAction(new_objects))
            self.objects_changed.emit()

    def insert_text(self, text: str, position: QPointF) -> None:
        """Insert a text block at the specified position."""
        if not text:
            return
        from canvas.text_object import TextBlock
        # Use default font sizing; color should contrast with background.
        # Assuming dark theme canvas, we use a light text color.
        text_block = TextBlock(text, position, font_size=24.0, color=QColor("#EDEDED"))
        self.text_blocks.append(text_block)
        self._add_undo_action(AddObjectsAction([text_block]))
        self.objects_changed.emit()

    def insert_image(self, file_path: str, position: QPointF) -> None:
        """Insert an image object at the specified position."""
        if not file_path:
            return
        from canvas.image_object import ImageObject
        img_obj = ImageObject(file_path, position)
        # Scale image down if it's too large
        if img_obj.image.width() > 800 or img_obj.image.height() > 800:
            scale_factor = min(800 / img_obj.image.width(), 800 / img_obj.image.height())
            img_obj.scale = scale_factor
        
        self.images.append(img_obj)
        self._add_undo_action(AddObjectsAction([img_obj]))
        self.objects_changed.emit()

    # ─── Undo/Redo ───────────────────────────────────────────────────────

    def _push_action(self, action: CanvasAction):
        """Push an action onto the undo stack and clear redo stack."""
        self.undo_stack.append(action)
        self.redo_stack.clear()

        # Enforce max undo steps
        while len(self.undo_stack) > MAX_UNDO_STEPS:
            self.undo_stack.pop(0)

    def undo(self):
        """Undo the last action."""
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        action.undo(self)
        self.redo_stack.append(action)
        self.clear_selection()
        self.objects_changed.emit()

    def redo(self):
        """Redo the last undone action."""
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        action.redo(self)
        self.clear_selection()
        self.objects_changed.emit()

    def can_undo(self) -> bool:
        """Whether there are actions to undo."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Whether there are actions to redo."""
        return len(self.redo_stack) > 0

    # ─── Canvas Operations ───────────────────────────────────────────────

    def clear_all(self):
        """Clear all objects from the canvas (undoable)."""
        if not self.objects and not self.text_blocks and not self.images:
            return

        self._push_action(ClearAllAction(list(self.objects), list(self.text_blocks), list(self.images)))
        self.objects.clear()
        self.text_blocks.clear()
        self.images.clear()
        self.selected_objects.clear()
        self.objects_changed.emit()

    def add_image(self, image: QImage, position: QPointF):
        """Add an image to the canvas."""
        from canvas.image_object import ImageObject
        img_obj = ImageObject(image, position)
        self.images.append(img_obj)
        
        # We can reuse AddStrokeAction since it just appends/removes from a list
        # Wait, AddStrokeAction appends to self.objects! Let's make a new action.
        class AddImageAction(CanvasAction):
            def __init__(self, img_obj):
                self.img_obj = img_obj
            def undo(self, engine):
                if self.img_obj in engine.images:
                    engine.images.remove(self.img_obj)
            def redo(self, engine):
                engine.images.append(self.img_obj)
                
        self._push_action(AddImageAction(img_obj))
        self.objects_changed.emit()

    def get_all_objects(self) -> list[CanvasObject]:
        """Get all canvas objects in draw order."""
        return list(self.objects)

    # ─── Export ───────────────────────────────────────────────────────────

    def render_to_image(self, width: int, height: int,
                        bg_color: QColor | None = None) -> QImage:
        """
        Render all canvas objects to a QImage.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            bg_color: Background color (None for transparent)

        Returns:
            QImage with all strokes rendered
        """
        if bg_color is None:
            bg_color = QColor(CANVAS_BACKGROUND_COLOR)

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(bg_color)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw highlighter strokes first (behind)
        for obj in self.objects:
            if obj.stroke.is_highlighter:
                color = QColor(obj.stroke.color)
                color.setAlpha(80)
                pen = QPen(color, obj.stroke.width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(obj.translated_path())

        # Then draw regular strokes
        for obj in self.objects:
            if obj.stroke.is_highlighter or obj.stroke.is_laser:
                continue
            pen = QPen(obj.stroke.color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # Use shape path if recognized
            if obj.stroke.shape_type != "none" and obj.stroke.shape_params:
                try:
                    from canvas.shape_recognizer import ShapeRecognizer
                    shape_path = ShapeRecognizer.shape_to_path(
                        obj.stroke.shape_type, obj.stroke.shape_params
                    )
                    if obj.offset.x() != 0 or obj.offset.y() != 0:
                        shape_path.translate(obj.offset)
                    painter.drawPath(shape_path)
                except ImportError:
                    painter.drawPath(obj.translated_path())
            else:
                painter.drawPath(obj.translated_path())

        # Render images
        for img in self.images:
            img.render(painter)

        # Render text blocks
        for text_block in self.text_blocks:
            text_block.render(painter)

        painter.end()
        return image
