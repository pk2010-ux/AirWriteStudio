"""
AirWrite Studio - One Euro Filter & Point Smoother
====================================================
Adaptive smoothing filter specifically designed for interactive hand tracking.
Smooth when the hand is still (eliminates jitter), responsive when moving fast (no lag).

Extended with speed tracking for dynamic width strokes.

Based on the 1€ Filter paper by Casiez et al.
"""

import time
import math
from config import SMOOTHING_MIN_CUTOFF, SMOOTHING_BETA, SMOOTHING_D_CUTOFF, JITTER_THRESHOLD


def _smoothing_factor(t_e: float, cutoff: float) -> float:
    """Compute the smoothing factor alpha for a given time interval and cutoff frequency."""
    r = 2.0 * math.pi * cutoff * t_e
    return r / (r + 1.0)


def _exp_smoothing(alpha: float, x: float, x_prev: float) -> float:
    """Exponential smoothing: weighted blend between current and previous value."""
    return alpha * x + (1.0 - alpha) * x_prev


class OneEuroFilter:
    """
    One Euro Filter - adaptive low-pass filter.

    The filter automatically adjusts its cutoff frequency based on the speed
    of the input signal:
    - When the signal changes slowly (hand is still) → low cutoff → heavy smoothing
    - When the signal changes quickly (hand moving fast) → high cutoff → light smoothing

    Parameters:
        min_cutoff: Minimum cutoff frequency. Lower = more smoothing when still.
                    Start at 1.0, decrease for more smoothing.
        beta: Speed coefficient. Higher = more responsive during fast movement.
              Start at 0.007, increase to reduce lag during drawing.
        d_cutoff: Cutoff frequency for the derivative filter. Usually leave at 1.0.
    """

    def __init__(self, min_cutoff: float = SMOOTHING_MIN_CUTOFF,
                 beta: float = SMOOTHING_BETA,
                 d_cutoff: float = SMOOTHING_D_CUTOFF):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        # Internal state
        self._x_prev: float | None = None
        self._dx_prev: float = 0.0
        self._t_prev: float | None = None

    def __call__(self, x: float, t: float | None = None) -> float:
        """
        Filter a single value.

        Args:
            x: Current raw input value
            t: Current timestamp (seconds). If None, uses time.time().

        Returns:
            Filtered (smoothed) value
        """
        if t is None:
            t = time.time()

        # First sample — initialize and return as-is
        if self._t_prev is None:
            self._x_prev = x
            self._t_prev = t
            return x

        # Time elapsed since last sample
        t_e = t - self._t_prev
        if t_e <= 0:
            return self._x_prev

        # --- Step 1: Filter the derivative (velocity) ---
        a_d = _smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self._x_prev) / t_e
        dx_hat = _exp_smoothing(a_d, dx, self._dx_prev)

        # --- Step 2: Adapt cutoff based on speed ---
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # --- Step 3: Filter the value with adaptive cutoff ---
        a = _smoothing_factor(t_e, cutoff)
        x_hat = _exp_smoothing(a, x, self._x_prev)

        # Update state
        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t

        return x_hat

    def reset(self):
        """Reset filter state. Call between strokes to avoid smoothing artifacts."""
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None


class PointSmoother:
    """
    Applies One Euro Filter independently to X and Y coordinates,
    followed by a short moving average for extra micro-jitter removal.
    Also includes a jitter threshold to ignore tiny movements.

    Extended with speed tracking for dynamic width strokes.

    Pipeline: Raw point → One Euro Filter → Moving Average → Jitter Gate → Output

    Usage:
        smoother = PointSmoother()
        smooth_x, smooth_y = smoother.smooth(raw_x, raw_y)
        speed = smoother.get_speed()  # pixels per second
        # ... on stroke end:
        smoother.reset()
    """

    # Number of points for the secondary moving average
    _MA_WINDOW = 3

    def __init__(self, min_cutoff: float = SMOOTHING_MIN_CUTOFF,
                 beta: float = SMOOTHING_BETA,
                 jitter_threshold: float = JITTER_THRESHOLD):
        self._filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self._filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self._jitter_threshold = jitter_threshold
        self._last_x: float | None = None
        self._last_y: float | None = None

        # Moving average buffers (secondary smoothing stage)
        self._ma_x: list[float] = []
        self._ma_y: list[float] = []

        # Speed tracking for dynamic width
        self._speed: float = 0.0
        self._speed_prev_x: float | None = None
        self._speed_prev_y: float | None = None
        self._speed_prev_t: float | None = None

    def smooth(self, x: float, y: float, t: float | None = None) -> tuple[float, float]:
        """
        Smooth a 2D point through the full pipeline.

        Args:
            x: Raw X coordinate (pixels)
            y: Raw Y coordinate (pixels)
            t: Optional timestamp (seconds)

        Returns:
            Tuple of (smoothed_x, smoothed_y)
        """
        now = t if t is not None else time.time()

        # Stage 1: One Euro Filter (adaptive)
        sx = self._filter_x(x, now)
        sy = self._filter_y(y, now)

        # Stage 2: Moving average (removes remaining micro-jitter)
        self._ma_x.append(sx)
        self._ma_y.append(sy)
        if len(self._ma_x) > self._MA_WINDOW:
            self._ma_x.pop(0)
            self._ma_y.pop(0)

        avg_x = sum(self._ma_x) / len(self._ma_x)
        avg_y = sum(self._ma_y) / len(self._ma_y)

        # Update speed tracking
        self._update_speed(avg_x, avg_y, now)

        # Stage 3: Jitter gate — if movement is below threshold, keep previous position
        if self._last_x is not None:
            dx = avg_x - self._last_x
            dy = avg_y - self._last_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < self._jitter_threshold:
                return self._last_x, self._last_y

        self._last_x = avg_x
        self._last_y = avg_y
        return avg_x, avg_y

    def _update_speed(self, x: float, y: float, t: float):
        """
        Track movement speed in pixels per second.
        Uses exponential smoothing to avoid spikes.
        """
        if self._speed_prev_x is not None and self._speed_prev_t is not None:
            dt = t - self._speed_prev_t
            if dt > 0.001:  # Avoid division by zero
                dx = x - self._speed_prev_x
                dy = y - self._speed_prev_y
                instant_speed = math.sqrt(dx * dx + dy * dy) / dt
                # Exponential smoothing on speed (alpha=0.3 for responsiveness)
                self._speed = 0.3 * instant_speed + 0.7 * self._speed

        self._speed_prev_x = x
        self._speed_prev_y = y
        self._speed_prev_t = t

    def get_speed(self) -> float:
        """
        Get the current smoothed movement speed in pixels per second.

        Returns:
            float: Speed in px/sec (0 when stationary)
        """
        return self._speed

    def reset(self):
        """Reset all filter stages, jitter state, and speed tracking. Call between strokes."""
        self._filter_x.reset()
        self._filter_y.reset()
        self._ma_x.clear()
        self._ma_y.clear()
        self._last_x = None
        self._last_y = None
        self._speed = 0.0
        self._speed_prev_x = None
        self._speed_prev_y = None
        self._speed_prev_t = None
