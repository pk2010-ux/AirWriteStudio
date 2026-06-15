"""
AirWrite Studio - Main Window
================================
Main application window that wires together the hand tracker, gesture detector,
point smoother, canvas engine, canvas widget, and sidebar into a cohesive app.

Extended with:
- Laser pointer mode
- Highlighter mode
- Dynamic width strokes
- Shape recognition
- OCR text conversion
- Zoom & pan via gesture
- Voice command integration
- Gesture calibration wizard
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QFileDialog, QApplication,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QImage, QShortcut, QKeySequence, QGuiApplication

from config import (
    GestureMode, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    DEFAULT_PEN_COLOR, DEFAULT_PEN_SIZE, DEFAULT_ERASER_SIZE,
    LASER_COLOR, LASER_WIDTH, HIGHLIGHTER_WIDTH, HIGHLIGHTER_COLORS,
    DYNAMIC_WIDTH_MAX_SPEED, DYNAMIC_WIDTH_MIN_FACTOR, DYNAMIC_WIDTH_MAX_FACTOR,
    OBJECT_SCALE_SPEED,
)
from canvas.canvas_engine import CanvasEngine
from canvas.canvas_widget import CanvasWidget
from tracking.hand_tracker import HandTracker
from tracking.gesture_detector import GestureDetector
from tracking.smoother import PointSmoother
from ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """
    Main application window for AirWrite Studio.

    Layout:
        [Sidebar (fixed 280px)] | [Canvas (stretch)]

    Wiring:
        HandTracker → GestureDetector → PointSmoother → CanvasEngine → CanvasWidget
        Sidebar signals ↔ Canvas/Engine/Tracker
        VoiceCommander → MainWindow → Canvas/Engine actions
    """

    def __init__(self):
        super().__init__()

        # Window setup
        self.setWindowTitle("AirWrite Studio")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # ─── Core Components ─────────────────────────────────────
        self.engine = CanvasEngine()
        self.canvas_widget = CanvasWidget(self.engine)
        self.hand_tracker = HandTracker()
        self.gesture_detector = GestureDetector()
        self.smoother = PointSmoother()
        self.sidebar = Sidebar()

        # ─── State ───────────────────────────────────────────────
        self._prev_gesture = GestureMode.NEUTRAL
        self._camera_active = False
        self._erasing = False

        # Feature state
        self._laser_mode = False
        self._highlighter_mode = False
        self._highlighter_color = QColor(HIGHLIGHTER_COLORS[0])
        self._dynamic_width = False
        self._galaxy_mode = False

        # Voice commander (lazy init)
        self._voice_commander = None

        # Toast widget (lazy init)
        self._toast = None

        # ─── Layout ──────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (fixed width)
        main_layout.addWidget(self.sidebar)

        # Canvas (fills remaining space)
        main_layout.addWidget(self.canvas_widget, stretch=1)

        # ─── Connect Signals ─────────────────────────────────────
        self._connect_tracker_signals()
        self._connect_sidebar_signals()
        self._connect_engine_signals()
        self._setup_shortcuts()

    def _connect_tracker_signals(self):
        """Connect HandTracker signals to processing pipeline."""
        camera_widget = self.sidebar.get_camera_widget()

        # Camera frame → preview widget
        self.hand_tracker.frame_ready.connect(camera_widget.update_frame)

        # Landmarks → gesture processing
        self.hand_tracker.landmarks_ready.connect(self._on_landmarks)

        # Status signals
        self.hand_tracker.hand_detected.connect(self.sidebar.update_hand_status)
        self.hand_tracker.fps_updated.connect(self.sidebar.update_fps)

    def _connect_sidebar_signals(self):
        """Connect Sidebar control signals to canvas/engine."""
        # Pen settings
        self.sidebar.pen_color_changed.connect(self.canvas_widget.set_pen_color)
        self.sidebar.pen_size_changed.connect(self.canvas_widget.set_pen_size)
        self.sidebar.eraser_size_changed.connect(self.canvas_widget.set_eraser_size)

        # Canvas actions
        self.sidebar.clear_canvas.connect(self._on_clear)
        self.sidebar.undo_requested.connect(self._on_undo)
        self.sidebar.redo_requested.connect(self._on_redo)

        # Export & Workspace
        self.sidebar.save_requested.connect(self._save_workspace)
        self.sidebar.load_workspace_requested.connect(self._load_workspace)
        self.sidebar.export_pdf_requested.connect(self._export_pdf)
        self.sidebar.export_svg_requested.connect(self._export_svg)

        # Camera
        self.sidebar.camera_toggled.connect(self._toggle_camera)

        # Background
        self.sidebar.background_image_requested.connect(self._load_background)
        self.sidebar.clear_background_requested.connect(self.canvas_widget.clear_background)

        # New feature signals
        self.sidebar.laser_mode_toggled.connect(self._on_laser_toggled)
        self.sidebar.highlighter_toggled.connect(self._on_highlighter_toggled)
        self.sidebar.highlighter_color_changed.connect(self._on_highlighter_color_changed)
        self.sidebar.dynamic_width_toggled.connect(self._on_dynamic_width_toggled)
        self.sidebar.shape_recognition_toggled.connect(self._on_shape_recognition_toggled)
        # Advanced actions
        self.sidebar.convert_to_text_requested.connect(self._on_convert_to_text)
        self.sidebar.insert_text_requested.connect(self._on_insert_text)
        self.sidebar.insert_image_requested.connect(self._on_insert_image)
        self.sidebar.duplicate_requested.connect(self.engine.duplicate_selection)
        self.sidebar.delete_requested.connect(self.engine.delete_selection)
        self.sidebar.grid_type_changed.connect(self.canvas_widget.set_grid_type)
        self.sidebar.voice_toggled.connect(self._toggle_voice)
        self.sidebar.galaxy_brush_toggled.connect(self._on_galaxy_toggled)
        self.sidebar.theme_toggled.connect(self.canvas_widget.set_light_mode)

    def _connect_engine_signals(self):
        """Connect CanvasEngine signals to UI feedback."""
        self.engine.shape_recognized.connect(self._on_shape_recognized)

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+Z"), self, self._on_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._on_redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self._on_redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_canvas)
        QShortcut(QKeySequence("Ctrl+E"), self, self._export_pdf)
        QShortcut(QKeySequence("Ctrl+N"), self, self._on_clear)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)

    # ─── Core Processing Pipeline ────────────────────────────────────────

    def _on_landmarks(self, landmarks):
        """
        Core gesture processing pipeline.

        Called for every frame from the HandTracker thread.
        Flow: landmarks → gesture detection → smoothing → canvas action

        Args:
            landmarks: MediaPipe hand landmarks object, or None if no hand
        """
        if landmarks is None:
            # No hand detected — end any active operations
            self._end_active_operations()
            self.canvas_widget.set_cursor(None, GestureMode.NEUTRAL)
            return

        # 1. Detect gesture mode and get action point (normalized 0–1)
        gesture, action_point = self.gesture_detector.detect(landmarks)

        # Update gesture detector's knowledge of selection state
        self.gesture_detector.has_selection = len(self.engine.selected_objects) > 0

        # 2. Convert normalized coordinates to canvas pixel coordinates
        canvas_w = self.canvas_widget.width()
        canvas_h = self.canvas_widget.height()
        raw_x = action_point[0] * canvas_w
        raw_y = action_point[1] * canvas_h

        # 3. Smooth the position (reduces jitter, smooths drawing)
        smooth_x, smooth_y = self.smoother.smooth(raw_x, raw_y)
        screen_point = QPointF(smooth_x, smooth_y)

        # 4. Transform screen point to canvas coordinates (accounting for zoom/pan)
        canvas_point = self.canvas_widget.screen_to_canvas(screen_point)

        # 5. Update visual cursor (in screen space)
        self.canvas_widget.set_cursor(screen_point, gesture)
        self.sidebar.update_gesture_status(gesture)

        # 6. End previous operations if gesture changed
        if gesture != self._prev_gesture:
            self._handle_gesture_transition(self._prev_gesture, gesture)

        # 7. Execute current gesture action
        self._execute_gesture(gesture, canvas_point, screen_point)

        self._prev_gesture = gesture

    def _handle_gesture_transition(self, old: GestureMode, new: GestureMode):
        """Handle cleanup when transitioning between gesture modes."""
        # End pen stroke
        if old == GestureMode.PEN and new != GestureMode.PEN:
            self.engine.end_stroke()
            self.smoother.reset()
            # Start laser fade timer if we just finished a laser stroke
            if self._laser_mode:
                self.canvas_widget.start_laser_timer()

        # End erase session
        if old == GestureMode.ERASER and new != GestureMode.ERASER:
            self.engine.end_erase()
            self._erasing = False
            
        # End select lasso
        if old == GestureMode.SELECT and new != GestureMode.SELECT:
            self.engine.end_lasso()

        # End drag
        if old == GestureMode.DRAG and new != GestureMode.DRAG:
            self.engine.end_move()

        # End scale
        if old in [GestureMode.ZOOM_IN, GestureMode.ZOOM_OUT] and new not in [GestureMode.ZOOM_IN, GestureMode.ZOOM_OUT]:
            self.engine.end_scale()

    def _execute_gesture(self, gesture: GestureMode, canvas_point: QPointF,
                         screen_point: QPointF):
        """Execute the action for the current gesture mode."""
        if gesture == GestureMode.PEN:
            if self._prev_gesture != GestureMode.PEN:
                # Starting a new stroke — determine stroke type
                if self._laser_mode:
                    self.engine.begin_stroke(
                        canvas_point,
                        QColor(LASER_COLOR),
                        LASER_WIDTH,
                        is_laser=True,
                    )
                elif self._highlighter_mode:
                    self.engine.begin_stroke(
                        canvas_point,
                        self._highlighter_color,
                        HIGHLIGHTER_WIDTH,
                        is_highlighter=True,
                    )
                elif self._galaxy_mode:
                    self.engine.begin_stroke(
                        canvas_point,
                        QColor("#FFFFFF"), # Base color, gradient applied in renderer
                        self.canvas_widget.pen_size,
                    )
                    # We need a way to mark it as galaxy
                    if self.engine.objects:
                        self.engine.objects[-1].stroke.is_galaxy = True
                else:
                    self.engine.begin_stroke(
                        canvas_point,
                        self.canvas_widget.pen_color,
                        self.canvas_widget.pen_size,
                    )
            else:
                # Continuing the stroke
                width_override = None
                if self._dynamic_width and not self._laser_mode and not self._highlighter_mode:
                    width_override = self._compute_dynamic_width()
                self.engine.add_point(canvas_point, width_override)

        elif gesture == GestureMode.ERASER:
            if not self._erasing:
                self.engine.begin_erase()
                self._erasing = True
            self.engine.erase_at(canvas_point, self.canvas_widget.eraser_size)

        elif gesture == GestureMode.SELECT:
            if self._prev_gesture != GestureMode.SELECT:
                self.engine.begin_lasso(canvas_point)
            else:
                self.engine.update_lasso(canvas_point)

        elif gesture == GestureMode.DRAG:
            if self._prev_gesture != GestureMode.DRAG:
                # Starting drag — auto-select nearest object if nothing selected
                if not self.engine.selected_objects:
                    self.engine.select_at(canvas_point, 30.0)
                self.engine.begin_move(canvas_point)
            else:
                self.engine.update_move(canvas_point)

        elif gesture == GestureMode.ZOOM_IN:
            if self._prev_gesture != GestureMode.ZOOM_IN:
                # Need something selected to scale
                if not self.engine.selected_objects:
                    self.engine.select_at(canvas_point, 30.0)
                self.engine.begin_scale()
            else:
                scale_delta = 1.0 + OBJECT_SCALE_SPEED
                self.engine.update_scale(scale_delta)
                
        elif gesture == GestureMode.ZOOM_OUT:
            if self._prev_gesture != GestureMode.ZOOM_OUT:
                # Need something selected to scale
                if not self.engine.selected_objects:
                    self.engine.select_at(canvas_point, 30.0)
                self.engine.begin_scale()
            else:
                scale_delta = 1.0 - OBJECT_SCALE_SPEED
                self.engine.update_scale(scale_delta)

        elif gesture == GestureMode.NEUTRAL:
            pass  # No action in neutral mode

    def _compute_dynamic_width(self) -> float:
        """Compute pen width based on current drawing speed."""
        speed = self.smoother.get_speed()
        base = self.canvas_widget.pen_size
        # Inverse relationship: fast = thin, slow = thick
        ratio = min(speed / DYNAMIC_WIDTH_MAX_SPEED, 1.0)
        factor = DYNAMIC_WIDTH_MAX_FACTOR - ratio * (DYNAMIC_WIDTH_MAX_FACTOR - DYNAMIC_WIDTH_MIN_FACTOR)
        return max(base * DYNAMIC_WIDTH_MIN_FACTOR, base * factor)

    def _end_active_operations(self):
        """End all active operations (called when hand is lost)."""
        if self._prev_gesture == GestureMode.PEN:
            self.engine.end_stroke()
            self.smoother.reset()
            if self._laser_mode:
                self.canvas_widget.start_laser_timer()
        if self._prev_gesture == GestureMode.DRAG:
            self.engine.end_move()
        if self._erasing:
            self.engine.end_erase()
            self._erasing = False
        if self._prev_gesture == GestureMode.SELECT:
            self.engine.end_lasso()
        self._prev_gesture = GestureMode.NEUTRAL

    # ─── Feature Toggle Handlers ─────────────────────────────────────────

    def _on_laser_toggled(self, active: bool):
        """Handle laser pointer mode toggle."""
        self._laser_mode = active
        if active:
            self._highlighter_mode = False

    def _on_highlighter_toggled(self, active: bool):
        """Handle highlighter mode toggle."""
        self._highlighter_mode = active
        if active:
            self._laser_mode = False
            self._galaxy_mode = False

    def _on_galaxy_toggled(self, active: bool):
        """Handle galaxy brush toggle."""
        self._galaxy_mode = active
        if active:
            self._laser_mode = False
            self._highlighter_mode = False

    def _on_highlighter_color_changed(self, color: QColor):
        """Handle highlighter color change."""
        self._highlighter_color = QColor(color)

    def _on_dynamic_width_toggled(self, active: bool):
        """Handle dynamic width toggle."""
        self._dynamic_width = active
        self.engine.dynamic_width_enabled = active

    def _on_shape_recognition_toggled(self, active: bool):
        """Handle shape recognition toggle."""
        self.engine.shape_recognition_enabled = active

    def _on_shape_recognized(self, shape_type: str):
        """Show toast when a shape is auto-detected."""
        label = shape_type.capitalize()
        self._show_toast(f"{label} detected")

    def _on_convert_to_text(self):
        """Handle request to convert selected strokes to text."""
        if not self.engine.selected_objects:
            self._show_toast("Select strokes first to convert")
            return
            
        try:
            from canvas.ocr_engine import OCREngine
            if not OCREngine.is_available():
                QMessageBox.information(
                    self, "Tesseract Required",
                    OCREngine.get_install_instructions()
                )
                return
            
            result = self.engine.convert_selection_to_text(
                self.canvas_widget.width(),
                self.canvas_widget.height()
            )
            if result:
                self._show_toast(f'Recognized: "{result}"')
            else:
                self._show_toast("Could not recognize text")
        except ImportError:
            self._show_toast("OCR module not available")
            return

    def _on_insert_text(self):
        """Prompt user for text and insert it into the canvas."""
        from PyQt6.QtWidgets import QInputDialog
        from PyQt6.QtCore import QPointF
        text, ok = QInputDialog.getMultiLineText(self, "Insert Text", "Enter text to add to canvas:")
        if ok and text:
            center_x = self.canvas_widget.width() / 2.0
            center_y = self.canvas_widget.height() / 2.0
            self.engine.insert_text(text, QPointF(center_x, center_y))

    def _on_insert_image(self):
        """Prompt user for an image and insert it into the canvas."""
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtCore import QPointF
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Insert Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if file_path:
            center_x = self.canvas_widget.width() / 2.0
            center_y = self.canvas_widget.height() / 2.0
            self.engine.insert_image(file_path, QPointF(center_x, center_y))


    # ─── Voice Commands ──────────────────────────────────────────────────

    def _toggle_voice(self, start: bool):
        """Start or stop voice command listening."""
        if start:
            try:
                from tracking.voice_commander import VoiceCommander
                if not VoiceCommander.is_available():
                    self.sidebar.update_voice_status("Vosk not installed")
                    self._show_toast("Install vosk: pip install vosk")
                    return

                if self._voice_commander is None:
                    self._voice_commander = VoiceCommander()
                    self._voice_commander.command_recognized.connect(self._on_voice_command)
                    self._voice_commander.status_changed.connect(self.sidebar.update_voice_status)

                self._voice_commander.start()
                self.sidebar.update_voice_status("Listening...")
            except ImportError:
                self.sidebar.update_voice_status("Module not found")
        else:
            if self._voice_commander is not None:
                self._voice_commander.stop()
            self.sidebar.update_voice_status("Off")

    def _on_voice_command(self, command: str, params: dict):
        """Handle a recognized voice command."""
        self.sidebar.update_voice_last_command(f"{command}: {params}")

        if command == "clear":
            self._on_clear()
            self._show_toast("Canvas cleared")
        elif command == "undo":
            self._on_undo()
            self._show_toast("Undo")
        elif command == "redo":
            self._on_redo()
            self._show_toast("Redo")
        elif command == "color":
            hex_color = params.get("color", "#FFFFFF")
            self.canvas_widget.set_pen_color(QColor(hex_color))
            self._show_toast(f"Color: {params.get('name', hex_color)}")
        elif command == "pen_size":
            size = params.get("size", 3.0)
            self.canvas_widget.set_pen_size(size)
            self._show_toast(f"Pen size: {size}")
        elif command == "tool":
            tool = params.get("tool", "pen")
            if tool == "laser":
                self._laser_mode = True
                self._highlighter_mode = False
                self._show_toast("Laser pointer on")
            elif tool == "highlighter":
                self._highlighter_mode = True
                self._laser_mode = False
                self._show_toast("Highlighter on")
            elif tool == "pen":
                self._laser_mode = False
                self._highlighter_mode = False
                self._show_toast("Pen mode")
        elif command == "save":
            self._save_canvas()
            self._show_toast("Saving...")
        elif command == "zoom":
            direction = params.get("direction", "in")
            if not self.engine.selected_objects:
                self._show_toast("Select an object to scale")
                return
                
            self.engine.begin_scale()
            if direction == "in":
                self.engine.update_scale(1.25)
            else:
                self.engine.update_scale(0.8)
            self.engine.end_scale()
            self._show_toast(f"Scale {direction}")
        elif command == "reset_view":
            self._show_toast("View reset")

    # ─── Toast Notifications ─────────────────────────────────────────────

    def _show_toast(self, message: str, icon: str = ""):
        """Show a floating toast notification on the canvas."""
        try:
            from ui.toast_widget import ToastWidget
            if self._toast is None:
                self._toast = ToastWidget(self.canvas_widget)
            self._toast.show_toast(message, icon)
        except ImportError:
            pass  # Toast widget not available, silently skip

    # ─── Sidebar Actions ─────────────────────────────────────────────────

    def _on_clear(self):
        """Clear the entire canvas."""
        self.engine.clear_all()

    def _on_undo(self):
        """Undo the last action."""
        self.engine.undo()

    def _on_redo(self):
        """Redo the last undone action."""
        self.engine.redo()

    def _toggle_camera(self, start: bool):
        """Start or stop the camera/hand tracker."""
        if start:
            self.hand_tracker.start()
            self._camera_active = True
        else:
            self.hand_tracker.stop()
            self._camera_active = False
            self._end_active_operations()
            self.canvas_widget.set_cursor(None, GestureMode.NEUTRAL)
            self.sidebar.update_gesture_status(GestureMode.NEUTRAL)

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ─── Export & Workspace ───────────────────────────────────────────────

    def _save_workspace(self):
        """Save the workspace to an .air file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Workspace",
            "canvas.air",
            "AirWrite Workspace (*.air);;All Files (*)",
        )
        if file_path:
            from canvas.serializer import save_workspace
            if save_workspace(self.engine, file_path):
                self._show_toast("Workspace saved")
            else:
                self._show_toast("Failed to save workspace")

    def _load_workspace(self):
        """Load a workspace from an .air file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Workspace",
            "",
            "AirWrite Workspace (*.air);;All Files (*)",
        )
        if file_path:
            from canvas.serializer import load_workspace
            if load_workspace(self.engine, file_path):
                self._show_toast("Workspace loaded")
            else:
                self._show_toast("Failed to load workspace")

    def _save_canvas(self):
        """Save the canvas as a PNG image."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Canvas",
            "airwrite_canvas.png",
            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)",
        )
        if file_path:
            image = self.engine.render_to_image(
                self.canvas_widget.width(),
                self.canvas_widget.height(),
            )
            image.save(file_path)

    def _export_pdf(self):
        """Export the canvas as a PDF."""
        try:
            from PyQt6.QtGui import QPdfWriter, QPainter
            from PyQt6.QtCore import QMarginsF
            from PyQt6.QtGui import QPageLayout, QPageSize

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export PDF",
                "airwrite_canvas.pdf",
                "PDF Files (*.pdf);;All Files (*)",
            )
            if file_path:
                writer = QPdfWriter(file_path)
                page_layout = QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Landscape,
                    QMarginsF(20, 20, 20, 20),
                )
                writer.setPageLayout(page_layout)

                painter = QPainter(writer)
                # Render the canvas content
                image = self.engine.render_to_image(
                    writer.width(), writer.height(),
                )
                painter.drawImage(0, 0, image)
                painter.end()
                self._show_toast("PDF exported")
        except ImportError:
            # QPdfWriter may not be available in all PyQt6 builds
            # Fall back to saving as PNG
            self._save_canvas()

    def _export_svg(self):
        """Export the canvas as an SVG vector graphic."""
        try:
            from canvas.svg_exporter import export_svg
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export SVG",
                "airwrite_vector.svg",
                "SVG Graphics (*.svg);;All Files (*)",
            )
            if file_path:
                if export_svg(self.engine, self.canvas_widget.width(), self.canvas_widget.height(), file_path):
                    self._show_toast("SVG exported")
                else:
                    self._show_toast("Failed to export SVG")
        except ImportError:
            self._show_toast("SVG export module missing")

    def _load_background(self):
        """Load a background image for the canvas."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Background Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                self.canvas_widget.set_background_image(image)

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean up resources on window close."""
        if self._camera_active:
            self.hand_tracker.stop()
        if self._voice_commander is not None:
            self._voice_commander.stop()
        event.accept()
