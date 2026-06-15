"""
AirWrite Studio - Canvas Objects
==================================
Data classes for strokes and canvas objects with smooth Bezier path rendering,
hit testing, and transform support for selection/movement.

Supports:
- Regular pen strokes
- Laser pointer strokes (with fade/opacity)
- Highlighter strokes (semi-transparent, render behind)
- Variable-width strokes (speed-based)
- Recognized shapes (snap to clean geometry)
"""

import time
import math
from dataclasses import dataclass, field
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath


@dataclass
class Stroke:
    """
    A freehand drawing stroke consisting of an ordered list of points.

    Attributes:
        points: Ordered list of QPointF coordinates
        color: Stroke color
        width: Stroke width in pixels
        timestamp: Creation time (time.time())
        is_laser: Whether this is a laser pointer stroke (auto-fades)
        is_highlighter: Whether this is a highlighter stroke (semi-transparent, behind)
        point_widths: Per-point widths for dynamic width strokes (None = uniform)
        shape_type: Recognized shape type string ('none', 'line', 'circle', etc.)
        shape_params: Parameters for recognized shape rendering
    """
    points: list[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    width: float = 3.0
    timestamp: float = field(default_factory=time.time)
    is_laser: bool = False
    is_highlighter: bool = False
    point_widths: list[float] | None = None
    shape_type: str = "none"
    shape_params: dict | None = None
    is_galaxy: bool = False

    def age(self) -> float:
        """Return the age of this stroke in seconds."""
        return time.time() - self.timestamp

    def laser_opacity(self, fade_duration: float = 2.5) -> float:
        """
        Compute the current opacity for laser strokes (1.0 → 0.0 over fade_duration).

        Args:
            fade_duration: Total fade duration in seconds

        Returns:
            float: Opacity value between 0.0 and 1.0
        """
        if not self.is_laser:
            return 1.0
        age = self.age()
        if age >= fade_duration:
            return 0.0
        return max(0.0, 1.0 - (age / fade_duration))

    def is_expired(self, fade_duration: float = 2.5) -> bool:
        """Check if a laser stroke has fully faded."""
        return self.is_laser and self.age() >= fade_duration

    def bounding_rect(self) -> QRectF:
        """
        Compute the bounding rectangle that contains all stroke points.
        Includes padding for the stroke width.

        Returns:
            QRectF bounding rectangle, or empty rect if no points
        """
        if not self.points:
            return QRectF()

        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        max_w = self.width
        if self.point_widths:
            max_w = max(max_w, max(self.point_widths))
        pad = max_w / 2.0 + 2.0  # Extra 2px for antialiasing

        return QRectF(
            min(xs) - pad, min(ys) - pad,
            (max(xs) - min(xs)) + 2 * pad,
            (max(ys) - min(ys)) + 2 * pad,
        )

    def contains_point(self, point: QPointF, threshold: float) -> bool:
        """
        Hit test: check if a point is within threshold distance of any
        line segment in the stroke.

        Args:
            point: The query point
            threshold: Maximum distance (pixels) to consider a hit

        Returns:
            True if the point is close enough to any segment
        """
        if len(self.points) < 2:
            if self.points:
                dx = point.x() - self.points[0].x()
                dy = point.y() - self.points[0].y()
                return math.sqrt(dx * dx + dy * dy) <= threshold
            return False

        for i in range(len(self.points) - 1):
            dist = self._point_to_segment_distance(
                point, self.points[i], self.points[i + 1]
            )
            if dist <= threshold:
                return True
        return False

    def to_painter_path(self) -> QPainterPath:
        """
        Convert stroke points to a smooth QPainterPath using quadratic Bezier curves.

        Uses midpoint interpolation: for each pair of consecutive points,
        the actual points become control points and midpoints become on-curve
        points. This produces much smoother curves than straight lineTo.

        Returns:
            QPainterPath ready for rendering with QPainter
        """
        path = QPainterPath()
        if not self.points:
            return path

        if len(self.points) == 1:
            # Single point — draw a tiny circle
            path.addEllipse(self.points[0], self.width / 2, self.width / 2)
            return path

        # Start at the first point
        path.moveTo(self.points[0])

        if len(self.points) == 2:
            path.lineTo(self.points[1])
            return path

        # Use Catmull-Rom to Cubic Bezier conversion for "Pro" smooth ink
        # Need at least 3 points for a good spline. We have len(self.points) > 2
        pts = self.points
        
        # Pad the points array by duplicating the first and last points
        # to handle the tangents at the endpoints
        p = [pts[0]] + pts + [pts[-1]]
        
        path.moveTo(pts[0])
        
        for i in range(1, len(p) - 2):
            p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
            
            # Tension parameter (0.5 is standard Catmull-Rom)
            tension = 0.5
            # Divisor is 3 to convert from Catmull-Rom to Cubic Bezier control points
            # c1 = p1 + (p2 - p0) * tension / 3
            # c2 = p2 - (p3 - p1) * tension / 3
            
            c1 = QPointF(
                p1.x() + (p2.x() - p0.x()) * tension / 3.0,
                p1.y() + (p2.y() - p0.y()) * tension / 3.0
            )
            c2 = QPointF(
                p2.x() - (p3.x() - p1.x()) * tension / 3.0,
                p2.y() - (p3.y() - p1.y()) * tension / 3.0
            )
            
            path.cubicTo(c1, c2, p2)

        return path

    def to_variable_width_polygons(self) -> list[tuple[QPainterPath, float]]:
        """
        Generate per-segment paths with individual widths for variable-width strokes.

        Returns:
            List of (QPainterPath, width) tuples for each segment.
            Returns empty list if point_widths is None.
        """
        if not self.point_widths or len(self.points) < 2:
            return []

        segments = []
        for i in range(len(self.points) - 1):
            seg_path = QPainterPath()
            seg_path.moveTo(self.points[i])
            seg_path.lineTo(self.points[i + 1])
            # Average width of the two endpoints
            w_idx = min(i, len(self.point_widths) - 1)
            w_idx_next = min(i + 1, len(self.point_widths) - 1)
            avg_w = (self.point_widths[w_idx] + self.point_widths[w_idx_next]) / 2.0
            segments.append((seg_path, avg_w))

        return segments

    @staticmethod
    def _point_to_segment_distance(p: QPointF, a: QPointF, b: QPointF) -> float:
        """
        Minimum distance from point p to line segment a-b.

        Uses projection to find the closest point on the segment,
        then returns the distance to that closest point.
        """
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 1e-10:
            # Degenerate segment (a ≈ b)
            return math.sqrt((p.x() - a.x()) ** 2 + (p.y() - a.y()) ** 2)

        # Project p onto the line defined by a-b, clamped to [0, 1]
        t = max(0.0, min(1.0, (
            (p.x() - a.x()) * dx + (p.y() - a.y()) * dy
        ) / seg_len_sq))

        # Closest point on segment
        closest_x = a.x() + t * dx
        closest_y = a.y() + t * dy

        return math.sqrt((p.x() - closest_x) ** 2 + (p.y() - closest_y) ** 2)


class CanvasObject:
    """
    Wrapper around a Stroke that adds selection and transform support.

    The offset is used for drag/move operations — the original stroke
    points remain unchanged, and the offset is applied during rendering.

    Attributes:
        stroke: The underlying Stroke data
        offset: Translation offset for drag/move (applied on top of stroke points)
        selected: Whether this object is currently selected
    """

    def __init__(self, stroke: Stroke):
        self.stroke = stroke
        self.offset = QPointF(0.0, 0.0)
        self.scale = 1.0
        self.selected = False

    def _transform(self):
        from PyQt6.QtGui import QTransform
        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        if self.scale != 1.0:
            c = self.stroke.bounding_rect().center()
            transform.translate(c.x(), c.y())
            transform.scale(self.scale, self.scale)
            transform.translate(-c.x(), -c.y())
        return transform

    def translated_path(self) -> QPainterPath:
        """
        Get the stroke's painter path with the current offset and scale applied.
        """
        path = self.stroke.to_painter_path()
        return self._transform().map(path)

    def translated_bounding_rect(self) -> QRectF:
        """
        Get the stroke's bounding rect with the current offset and scale applied.
        """
        rect = self.stroke.bounding_rect()
        return self._transform().mapRect(rect)

    def contains_point(self, point: QPointF, threshold: float) -> bool:
        """
        Hit test accounting for the current offset.

        Translates the query point in the opposite direction of the offset
        to test against the original stroke points.

        Args:
            point: Query point in canvas coordinates
            threshold: Hit test threshold in pixels

        Returns:
            True if the point is within threshold of the translated stroke
        """
        # Inverse transform the point
        inv_transform, invertible = self._transform().inverted()
        if not invertible:
            return False
        adjusted_point = inv_transform.map(point)
        # Scale the threshold so it works correctly after transformation
        return self.stroke.contains_point(adjusted_point, threshold / self.scale)

    def apply_transforms(self):
        """
        Bake the current offset and scale into the stroke points permanently.
        Called after a move/scale operation is finalized.
        """
        if self.offset.x() == 0.0 and self.offset.y() == 0.0 and self.scale == 1.0:
            return
        
        transform = self._transform()
        self.stroke.points = [transform.map(p) for p in self.stroke.points]
        
        if self.scale != 1.0:
            self.stroke.width *= self.scale
            if self.stroke.point_widths:
                self.stroke.point_widths = [w * self.scale for w in self.stroke.point_widths]
                
        self.offset = QPointF(0.0, 0.0)
        self.scale = 1.0
