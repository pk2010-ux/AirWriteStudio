"""
AirWrite Studio - Smart Shape Recognizer
==========================================
Analyses a list of freehand QPointF stroke points and determines whether
they approximate a geometric primitive (line, circle, rectangle, triangle).
When a shape is recognised the module returns clean geometric parameters
that can be used to replace the rough stroke with a perfect shape.

Recognition priority: Circle → Rectangle → Triangle → Line.
"""

import math
from enum import Enum

import numpy as np
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath


# ─── Shape Type Enum ──────────────────────────────────────────────────────────

class ShapeType(Enum):
    """Recognised geometric shape categories."""
    NONE = "none"
    LINE = "line"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"


# ─── Constants ────────────────────────────────────────────────────────────────

_MIN_POINTS = 10
_LINE_R2_THRESHOLD = 0.90
_CIRCLE_DEVIATION_THRESHOLD = 0.25
_CIRCLE_CLOSURE_THRESHOLD = 0.35
_RECT_ANGLE_TOLERANCE_DEG = 25.0
_RECT_SIDE_TOLERANCE = 0.35
_TRIANGLE_ANGLE_SUM_TOLERANCE_DEG = 30.0


# ─── Shape Recognizer ────────────────────────────────────────────────────────

class ShapeRecognizer:
    """
    Analyses a stroke (list of QPointF) and attempts to classify it
    as a known geometric shape.

    Usage::

        recognizer = ShapeRecognizer()
        shape_type, params = recognizer.recognize(stroke_points)
        if shape_type is not ShapeType.NONE:
            path = ShapeRecognizer.shape_to_path(shape_type, params)
    """

    # ── Public API ────────────────────────────────────────────────────────

    def recognize(
        self,
        points: list[QPointF],
    ) -> tuple[ShapeType, dict | None]:
        """
        Attempt to recognise a geometric shape from freehand points.

        Args:
            points: Ordered list of QPointF forming the stroke.

        Returns:
            A ``(ShapeType, params)`` tuple.  If no shape is recognised
            the result is ``(ShapeType.NONE, None)``.
        """
        if len(points) < _MIN_POINTS:
            return ShapeType.NONE, None

        pts = np.array([[p.x(), p.y()] for p in points], dtype=np.float64)

        # Priority order: Circle > Rectangle > Triangle > Line
        result = self._check_circle(pts)
        if result is not None:
            return ShapeType.CIRCLE, result

        result = self._check_rectangle(pts)
        if result is not None:
            return ShapeType.RECTANGLE, result

        result = self._check_triangle(pts)
        if result is not None:
            return ShapeType.TRIANGLE, result

        result = self._check_line(pts)
        if result is not None:
            return ShapeType.LINE, result

        return ShapeType.NONE, None

    # ── Static: Convert shape → QPainterPath ──────────────────────────────

    @staticmethod
    def shape_to_path(shape_type: ShapeType, params: dict) -> QPainterPath:
        """
        Build a clean QPainterPath from recognised shape parameters.

        Args:
            shape_type: The recognised shape kind.
            params:     Parameter dict as returned by :meth:`recognize`.

        Returns:
            A QPainterPath representing the idealised shape.
        """
        path = QPainterPath()

        if shape_type is ShapeType.LINE:
            start: QPointF = params["start"]
            end: QPointF = params["end"]
            path.moveTo(start)
            path.lineTo(end)

        elif shape_type is ShapeType.CIRCLE:
            center: QPointF = params["center"]
            radius: float = params["radius"]
            path.addEllipse(center, radius, radius)

        elif shape_type is ShapeType.RECTANGLE:
            rect: QRectF = params["rect"]
            angle: float = params["angle"]
            if abs(angle) < 1e-6:
                path.addRect(rect)
            else:
                # Build a rotated rectangle
                cx = rect.center().x()
                cy = rect.center().y()
                hw = rect.width() / 2.0
                hh = rect.height() / 2.0
                corners_local = [
                    (-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh),
                ]
                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                rotated = [
                    QPointF(cx + x * cos_a - y * sin_a,
                            cy + x * sin_a + y * cos_a)
                    for x, y in corners_local
                ]
                path.moveTo(rotated[0])
                for pt in rotated[1:]:
                    path.lineTo(pt)
                path.closeSubpath()

        elif shape_type is ShapeType.TRIANGLE:
            tri_pts: list[QPointF] = params["points"]
            path.moveTo(tri_pts[0])
            path.lineTo(tri_pts[1])
            path.lineTo(tri_pts[2])
            path.closeSubpath()

        return path

    # ── Private: Line Detection ───────────────────────────────────────────

    def _check_line(self, pts: np.ndarray) -> dict | None:
        """
        Detect a straight line using RDP simplification and R² fitting.

        A stroke is a line when:
        * The RDP-simplified path has ≤ 2 points (eps = 5 % of extent).
        * The R² of a least-squares linear fit exceeds 0.95.
        """
        extent = self._max_extent(pts)
        if extent < 1e-6:
            return None

        epsilon = extent * 0.05
        simplified = self._rdp(pts, epsilon)

        if len(simplified) > 2:
            return None

        # R² check — project onto the dominant axis
        r2 = self._linear_r_squared(pts)
        if r2 < _LINE_R2_THRESHOLD:
            return None

        return {
            "start": QPointF(float(pts[0, 0]), float(pts[0, 1])),
            "end": QPointF(float(pts[-1, 0]), float(pts[-1, 1])),
        }

    # ── Private: Circle Detection ─────────────────────────────────────────

    def _check_circle(self, pts: np.ndarray) -> dict | None:
        """
        Detect a circle by measuring radial deviation from the centroid.

        Criteria:
        * std(radii) / mean(radii) < 0.15
        * Stroke closes — first point near last within 15 % of diameter.
        """
        centroid = pts.mean(axis=0)
        radii = np.linalg.norm(pts - centroid, axis=1)
        mean_r = radii.mean()

        if mean_r < 1e-6:
            return None

        std_r = radii.std()
        if std_r / mean_r >= _CIRCLE_DEVIATION_THRESHOLD:
            return None

        # Closure check
        closure_dist = np.linalg.norm(pts[0] - pts[-1])
        if closure_dist > _CIRCLE_CLOSURE_THRESHOLD * (2.0 * mean_r):
            return None

        return {
            "center": QPointF(float(centroid[0]), float(centroid[1])),
            "radius": float(mean_r),
        }

    # ── Private: Rectangle Detection ──────────────────────────────────────

    def _check_rectangle(self, pts: np.ndarray) -> dict | None:
        """
        Detect a rectangle via convex-hull corner analysis.

        Steps:
        1. Compute convex hull (Graham scan).
        2. Find dominant corners (interior angle < 160°).
        3. Require exactly 4 corners.
        4. Verify angles ≈ 90° (within tolerance) and opposite sides
           similar in length (within 20 %).
        """
        hull = self._graham_scan(pts)
        if len(hull) < 4:
            return None

        corners, corner_angles = self._find_corners(hull, angle_threshold_deg=160.0)
        if len(corners) != 4:
            return None

        # Check right-angle property
        for angle in corner_angles:
            if abs(angle - 90.0) > _RECT_ANGLE_TOLERANCE_DEG:
                return None

        # Check opposite-side similarity
        sides = self._polygon_side_lengths(corners)
        if len(sides) != 4:
            return None

        for i in range(2):
            s1 = sides[i]
            s2 = sides[i + 2]
            avg = (s1 + s2) / 2.0
            if avg < 1e-6:
                return None
            if abs(s1 - s2) / avg > _RECT_SIDE_TOLERANCE:
                return None

        # Closure check — first point near last
        closure_dist = np.linalg.norm(pts[0] - pts[-1])
        extent = self._max_extent(pts)
        if extent > 1e-6 and closure_dist / extent > 0.25:
            return None

        # Build axis-aligned bounding rect + rotation angle
        rect, angle = self._oriented_bounding_rect(corners)
        return {"rect": rect, "angle": angle}

    # ── Private: Triangle Detection ───────────────────────────────────────

    def _check_triangle(self, pts: np.ndarray) -> dict | None:
        """
        Detect a triangle via convex-hull corner analysis.

        Steps:
        1. Compute convex hull.
        2. Find dominant corners (interior angle < 170°).
        3. Require exactly 3 corners.
        4. Verify angle sum ≈ 180°.
        """
        hull = self._graham_scan(pts)
        if len(hull) < 3:
            return None

        corners, corner_angles = self._find_corners(hull, angle_threshold_deg=170.0)
        if len(corners) != 3:
            return None

        angle_sum = sum(corner_angles)
        if abs(angle_sum - 180.0) > _TRIANGLE_ANGLE_SUM_TOLERANCE_DEG:
            return None

        # Closure check
        closure_dist = np.linalg.norm(pts[0] - pts[-1])
        extent = self._max_extent(pts)
        if extent > 1e-6 and closure_dist / extent > 0.25:
            return None

        return {
            "points": [
                QPointF(float(corners[0][0]), float(corners[0][1])),
                QPointF(float(corners[1][0]), float(corners[1][1])),
                QPointF(float(corners[2][0]), float(corners[2][1])),
            ],
        }

    # ── Geometry Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _max_extent(pts: np.ndarray) -> float:
        """Return the diagonal of the axis-aligned bounding box."""
        mins = pts.min(axis=0)
        maxs = pts.max(axis=0)
        diff = maxs - mins
        return float(np.linalg.norm(diff))

    @staticmethod
    def _linear_r_squared(pts: np.ndarray) -> float:
        """
        Compute R² of a least-squares line fit.

        To handle vertical lines properly the fit is performed along the
        axis with the larger range.
        """
        x = pts[:, 0]
        y = pts[:, 1]

        x_range = x.max() - x.min()
        y_range = y.max() - y.min()

        # Swap axes so the independent variable has the larger range
        if y_range > x_range:
            x, y = y, x

        n = len(x)
        if n < 2:
            return 0.0

        x_mean = x.mean()
        y_mean = y.mean()
        ss_tot = np.sum((y - y_mean) ** 2)
        if ss_tot < 1e-10:
            # All y values identical — perfect horizontal line
            return 1.0

        ss_xy = np.sum((x - x_mean) * (y - y_mean))
        ss_xx = np.sum((x - x_mean) ** 2)
        if ss_xx < 1e-10:
            return 0.0

        slope = ss_xy / ss_xx
        intercept = y_mean - slope * x_mean
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)

        return float(1.0 - ss_res / ss_tot)

    # ── Ramer-Douglas-Peucker Simplification ──────────────────────────────

    @staticmethod
    def _rdp(pts: np.ndarray, epsilon: float) -> np.ndarray:
        """
        Ramer-Douglas-Peucker polyline simplification.

        Recursively removes points whose perpendicular distance to the
        line segment between the first and last point is less than *epsilon*.

        Args:
            pts:     Nx2 array of polyline vertices.
            epsilon: Maximum allowed perpendicular deviation.

        Returns:
            Simplified Mx2 array (M ≤ N).
        """
        if len(pts) <= 2:
            return pts

        # Find the point with the maximum distance from the first-last line
        start = pts[0]
        end = pts[-1]
        line_vec = end - start
        line_len = np.linalg.norm(line_vec)

        if line_len < 1e-10:
            # Degenerate segment — find point farthest from start
            dists = np.linalg.norm(pts - start, axis=1)
        else:
            # Perpendicular distances
            unit = line_vec / line_len
            diff = pts - start
            proj = np.dot(diff, unit)
            closest = start + np.outer(proj, unit)
            dists = np.linalg.norm(pts - closest, axis=1)

        max_idx = int(np.argmax(dists))
        max_dist = dists[max_idx]

        if max_dist > epsilon:
            left = ShapeRecognizer._rdp(pts[: max_idx + 1], epsilon)
            right = ShapeRecognizer._rdp(pts[max_idx:], epsilon)
            return np.vstack([left[:-1], right])

        return np.array([pts[0], pts[-1]])

    # ── Graham Scan Convex Hull ───────────────────────────────────────────

    @staticmethod
    def _graham_scan(pts: np.ndarray) -> np.ndarray:
        """
        Compute the convex hull of a 2-D point set using Graham scan.

        Returns:
            Kx2 array of hull vertices in counter-clockwise order.
        """
        # Remove duplicate points
        unique = np.unique(pts, axis=0)
        if len(unique) < 3:
            return unique

        # Start from the lowest (then left-most) point
        lowest_idx = int(np.lexsort((unique[:, 0], unique[:, 1]))[0])
        pivot = unique[lowest_idx]

        # Sort remaining points by polar angle relative to the pivot
        diff = unique - pivot
        angles = np.arctan2(diff[:, 1], diff[:, 0])
        dists = np.linalg.norm(diff, axis=1)

        order = np.lexsort((dists, angles))
        sorted_pts = unique[order]

        # Build the hull
        hull: list[np.ndarray] = []
        for pt in sorted_pts:
            while len(hull) >= 2:
                cross = np.cross(hull[-1] - hull[-2], pt - hull[-2])
                if cross <= 0:
                    hull.pop()
                else:
                    break
            hull.append(pt)

        return np.array(hull)

    # ── Corner Detection on a Polygon ─────────────────────────────────────

    @staticmethod
    def _find_corners(
        hull: np.ndarray,
        angle_threshold_deg: float,
    ) -> tuple[np.ndarray, list[float]]:
        """
        Identify dominant corners on a convex polygon.

        A vertex is a "corner" when its interior angle is less than
        *angle_threshold_deg*.

        Returns:
            (corners, angles) — Nx2 array of corner vertices and a list
            of their interior angles in degrees.
        """
        n = len(hull)
        corners: list[np.ndarray] = []
        angles: list[float] = []

        for i in range(n):
            prev_pt = hull[(i - 1) % n]
            curr_pt = hull[i]
            next_pt = hull[(i + 1) % n]

            v1 = prev_pt - curr_pt
            v2 = next_pt - curr_pt

            len1 = np.linalg.norm(v1)
            len2 = np.linalg.norm(v2)
            if len1 < 1e-10 or len2 < 1e-10:
                continue

            cos_angle = np.clip(np.dot(v1, v2) / (len1 * len2), -1.0, 1.0)
            angle_deg = float(np.degrees(np.arccos(cos_angle)))

            if angle_deg < angle_threshold_deg:
                corners.append(curr_pt)
                angles.append(angle_deg)

        return np.array(corners) if corners else np.empty((0, 2)), angles

    # ── Polygon Side Lengths ──────────────────────────────────────────────

    @staticmethod
    def _polygon_side_lengths(corners: np.ndarray) -> list[float]:
        """Return a list of side lengths for an ordered polygon."""
        n = len(corners)
        return [
            float(np.linalg.norm(corners[(i + 1) % n] - corners[i]))
            for i in range(n)
        ]

    # ── Oriented Bounding Rectangle ──────────────────────────────────────

    @staticmethod
    def _oriented_bounding_rect(
        corners: np.ndarray,
    ) -> tuple[QRectF, float]:
        """
        Compute an oriented bounding rectangle for a 4-corner polygon.

        The primary edge (longest side starting from corner 0) defines
        the rotation angle.  The rectangle is expressed as an axis-aligned
        QRectF plus a rotation *angle* in degrees.

        Returns:
            (QRectF centred at polygon centroid, rotation angle in degrees)
        """
        # Primary edge direction
        edge = corners[1] - corners[0]
        angle_rad = math.atan2(float(edge[1]), float(edge[0]))
        angle_deg = math.degrees(angle_rad)

        # Rotate corners to align primary edge with the X axis
        cos_a = math.cos(-angle_rad)
        sin_a = math.sin(-angle_rad)
        rotated = np.empty_like(corners)
        for i, (cx, cy) in enumerate(corners):
            rotated[i, 0] = cx * cos_a - cy * sin_a
            rotated[i, 1] = cx * sin_a + cy * cos_a

        x_min = float(rotated[:, 0].min())
        x_max = float(rotated[:, 0].max())
        y_min = float(rotated[:, 1].min())
        y_max = float(rotated[:, 1].max())

        w = x_max - x_min
        h = y_max - y_min

        # Centre in rotated space, then rotate back
        cx_rot = (x_min + x_max) / 2.0
        cy_rot = (y_min + y_max) / 2.0
        cx_orig = cx_rot * cos_a + cy_rot * sin_a  # inverse rotation
        cy_orig = -cx_rot * sin_a + cy_rot * cos_a

        rect = QRectF(cx_orig - w / 2.0, cy_orig - h / 2.0, w, h)
        return rect, angle_deg
