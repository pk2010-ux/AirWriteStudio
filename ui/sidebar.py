"""
AirWrite Studio - Sidebar
===========================
Control panel with grouped sections for pen settings, eraser settings,
gesture status, camera preview, canvas actions, and export options.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QSlider, QLabel, QScrollArea, QFrame,
    QSizePolicy, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta

from config import (
    GestureMode, GESTURE_MODE_INFO,
    SIDEBAR_WIDTH, COLOR_PALETTE, HIGHLIGHTER_COLORS,
    DEFAULT_PEN_COLOR, DEFAULT_PEN_SIZE, MIN_PEN_SIZE, MAX_PEN_SIZE,
    DEFAULT_ERASER_SIZE, MIN_ERASER_SIZE, MAX_ERASER_SIZE,
)
from ui.styles import Styles
from ui.camera_widget import CameraWidget


# Icon color for qtawesome — muted grey, matching the theme
_IC = '#888888'
_IC_ACTIVE = '#EDEDED'


class Sidebar(QWidget):
    """
    Control panel sidebar with all tool settings and actions.
    """

    # ─── Signals ─────────────────────────────────────────────────────────
    pen_color_changed = pyqtSignal(QColor)
    pen_size_changed = pyqtSignal(float)
    eraser_size_changed = pyqtSignal(float)
    clear_canvas = pyqtSignal()
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    save_requested = pyqtSignal()
    export_pdf_requested = pyqtSignal()
    camera_toggled = pyqtSignal(bool)
    background_image_requested = pyqtSignal()
    clear_background_requested = pyqtSignal()
    theme_toggled = pyqtSignal(bool)

    laser_mode_toggled = pyqtSignal(bool)
    highlighter_toggled = pyqtSignal(bool)
    highlighter_color_changed = pyqtSignal(QColor)
    dynamic_width_toggled = pyqtSignal(bool)
    shape_recognition_toggled = pyqtSignal(bool)
    convert_to_text_requested = pyqtSignal()
    insert_text_requested = pyqtSignal()
    insert_image_requested = pyqtSignal()
    grid_type_changed = pyqtSignal(object)
    voice_toggled = pyqtSignal(bool)
    load_workspace_requested = pyqtSignal()
    export_svg_requested = pyqtSignal()
    galaxy_brush_toggled = pyqtSignal(bool)
    duplicate_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)

        self._selected_color = DEFAULT_PEN_COLOR
        self._color_swatches: list[QPushButton] = []
        self._camera_running = False
        self._laser_active = False
        self._highlighter_active = False

        self._build_ui()

    # ─── Icon Helper ─────────────────────────────────────────────────────

    @staticmethod
    def _icon(name: str, color: str = _IC) -> 'QIcon':
        """Create a qtawesome icon with consistent styling."""
        return qta.icon(name, color=color)

    # ─── Build UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        """Construct the sidebar layout with all sections."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("sidebar_content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        # ── App Title ────────────────────────────────────────────────
        title = QLabel("AirWrite Studio")
        title.setObjectName("app_title")
        layout.addWidget(title)

        subtitle = QLabel("Hands-free digital canvas")
        subtitle.setObjectName("app_subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(4)
        layout.addWidget(self._sep())

        # ── Status ───────────────────────────────────────────────────
        layout.addWidget(self._section("Status"))

        self._gesture_card = QWidget()
        self._gesture_card.setObjectName("gesture_status_card")
        card_layout = QVBoxLayout(self._gesture_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Top row: dot + gesture label + fps badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._gesture_dot = QLabel()
        self._gesture_dot.setStyleSheet(Styles.get_status_dot_style("#555555"))
        self._gesture_dot.setFixedSize(8, 8)
        top_row.addWidget(self._gesture_dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._gesture_label = QLabel("Neutral")
        self._gesture_label.setObjectName("status_label")
        top_row.addWidget(self._gesture_label)

        top_row.addStretch()

        self._fps_label = QLabel("—")
        self._fps_label.setObjectName("fps_badge")
        self._fps_label.setFixedHeight(20)
        top_row.addWidget(self._fps_label)

        card_layout.addLayout(top_row)

        # Description text
        self._gesture_desc = QLabel("Open palm — no action")
        self._gesture_desc.setObjectName("status_desc")
        self._gesture_desc.setWordWrap(True)
        card_layout.addWidget(self._gesture_desc)

        # Bottom row: hand status
        self._hand_indicator = QLabel("No hand detected")
        self._hand_indicator.setObjectName("hand_status")
        self._hand_indicator.setStyleSheet("color: #555555;")
        card_layout.addWidget(self._hand_indicator)

        # Hidden — kept for backward compat with update_gesture_status
        self._gesture_icon = QLabel("")
        self._gesture_icon.setVisible(False)

        layout.addWidget(self._gesture_card)

        # ── Camera ───────────────────────────────────────────────────
        layout.addWidget(self._section("Camera"))
        self._camera_widget = CameraWidget()
        layout.addWidget(self._camera_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._camera_toggle = QPushButton("Start Camera")
        self._camera_toggle.setIcon(self._icon('fa5s.video'))
        self._camera_toggle.setObjectName("primary_button")
        self._camera_toggle.clicked.connect(self._on_camera_toggle)
        layout.addWidget(self._camera_toggle)

        layout.addWidget(self._sep())

        # ── Pen ──────────────────────────────────────────────────────
        layout.addWidget(self._section("Pen"))

        color_grid = QGridLayout()
        color_grid.setSpacing(4)
        for i, hex_color in enumerate(COLOR_PALETTE):
            swatch = QPushButton()
            swatch.setObjectName("color_swatch")
            swatch.setStyleSheet(Styles.get_color_swatch_style(
                hex_color, hex_color == self._selected_color
            ))
            swatch.setFixedSize(26, 26)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.clicked.connect(lambda checked, c=hex_color: self._on_color_picked(c))
            self._color_swatches.append(swatch)
            color_grid.addWidget(swatch, i // 6, i % 6)
        layout.addLayout(color_grid)

        layout.addSpacing(4)

        pen_size_row = QHBoxLayout()
        pen_size_row.setSpacing(8)
        size_label = QLabel("Size")
        size_label.setObjectName("fps_label")
        pen_size_row.addWidget(size_label)
        self._pen_slider = QSlider(Qt.Orientation.Horizontal)
        self._pen_slider.setRange(int(MIN_PEN_SIZE * 10), int(MAX_PEN_SIZE * 10))
        self._pen_slider.setValue(int(DEFAULT_PEN_SIZE * 10))
        self._pen_slider.valueChanged.connect(self._on_pen_size_changed)
        pen_size_row.addWidget(self._pen_slider)
        self._pen_value = QLabel(f"{DEFAULT_PEN_SIZE:.1f}")
        self._pen_value.setObjectName("value_label")
        pen_size_row.addWidget(self._pen_value)
        layout.addLayout(pen_size_row)

        layout.addSpacing(4)

        # Pen mode toggles
        pen_toggles = QHBoxLayout()
        pen_toggles.setSpacing(4)

        self._laser_btn = self._toggle("Laser", 'mdi.laser-pointer')
        self._laser_btn.clicked.connect(self._on_laser_toggle)
        pen_toggles.addWidget(self._laser_btn)

        self._highlighter_btn = self._toggle("Highlight", 'fa5s.highlighter')
        self._highlighter_btn.clicked.connect(self._on_highlighter_toggle)
        pen_toggles.addWidget(self._highlighter_btn)

        self._dynamic_width_btn = self._toggle("Pressure", 'fa5s.wave-square')
        self._dynamic_width_btn.clicked.connect(
            lambda checked: self.dynamic_width_toggled.emit(self._dynamic_width_btn.isChecked())
        )
        pen_toggles.addWidget(self._dynamic_width_btn)

        self._galaxy_btn = self._toggle("Galaxy", 'fa5s.star')
        self._galaxy_btn.clicked.connect(self._on_galaxy_toggle)
        pen_toggles.addWidget(self._galaxy_btn)

        layout.addLayout(pen_toggles)

        # Highlighter color row (hidden by default)
        self._highlighter_color_row = QWidget()
        hl_layout = QHBoxLayout(self._highlighter_color_row)
        hl_layout.setContentsMargins(0, 4, 0, 0)
        hl_layout.setSpacing(4)
        self._hl_swatches: list[QPushButton] = []
        for hex_c in HIGHLIGHTER_COLORS:
            swatch = QPushButton()
            swatch.setStyleSheet(Styles.get_color_swatch_style(hex_c, hex_c == HIGHLIGHTER_COLORS[0]))
            swatch.setFixedSize(22, 22)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.clicked.connect(lambda checked, c=hex_c: self._on_highlighter_color_picked(c))
            self._hl_swatches.append(swatch)
            hl_layout.addWidget(swatch)
        hl_layout.addStretch()
        self._highlighter_color_row.setVisible(False)
        layout.addWidget(self._highlighter_color_row)

        layout.addWidget(self._sep())

        # ── Eraser ───────────────────────────────────────────────────
        layout.addWidget(self._section("Eraser"))
        eraser_row = QHBoxLayout()
        eraser_row.setSpacing(8)
        er_label = QLabel("Size")
        er_label.setObjectName("fps_label")
        eraser_row.addWidget(er_label)
        self._eraser_slider = QSlider(Qt.Orientation.Horizontal)
        self._eraser_slider.setRange(int(MIN_ERASER_SIZE), int(MAX_ERASER_SIZE))
        self._eraser_slider.setValue(int(DEFAULT_ERASER_SIZE))
        self._eraser_slider.valueChanged.connect(self._on_eraser_size_changed)
        eraser_row.addWidget(self._eraser_slider)
        self._eraser_value = QLabel(f"{int(DEFAULT_ERASER_SIZE)}")
        self._eraser_value.setObjectName("value_label")
        eraser_row.addWidget(self._eraser_value)
        layout.addLayout(eraser_row)

        layout.addWidget(self._sep())

        # ── Smart Tools ──────────────────────────────────────────────
        layout.addWidget(self._section("Smart Tools"))
        smart_row = QHBoxLayout()
        smart_row.setSpacing(4)

        self._shape_btn = self._toggle("Shapes", 'fa5s.shapes')
        self._shape_btn.clicked.connect(
            lambda: self.shape_recognition_toggled.emit(self._shape_btn.isChecked())
        )
        smart_row.addWidget(self._shape_btn)

        self._ocr_btn = QPushButton("To Text")
        self._ocr_btn.setIcon(self._icon('fa5s.font'))
        self._ocr_btn.setToolTip("Select strokes, then click to convert to text")
        self._ocr_btn.clicked.connect(self.convert_to_text_requested.emit)
        smart_row.addWidget(self._ocr_btn)

        layout.addLayout(smart_row)

        insert_row = QHBoxLayout()
        insert_row.setSpacing(4)
        
        insert_text_btn = QPushButton("Add Text")
        insert_text_btn.setIcon(self._icon('fa5s.i-cursor'))
        insert_text_btn.clicked.connect(self.insert_text_requested.emit)
        insert_row.addWidget(insert_text_btn)
        
        insert_img_btn = QPushButton("Add Image")
        insert_img_btn.setIcon(self._icon('fa5s.image'))
        insert_img_btn.clicked.connect(self.insert_image_requested.emit)
        insert_row.addWidget(insert_img_btn)
        
        layout.addLayout(insert_row)

        layout.addWidget(self._sep())

        # ── Actions ──────────────────────────────────────────────────
        layout.addWidget(self._section("Actions"))
        action_row = QHBoxLayout()
        action_row.setSpacing(4)

        undo_btn = QPushButton("Undo")
        undo_btn.setIcon(self._icon('fa5s.undo'))
        undo_btn.clicked.connect(self.undo_requested.emit)
        action_row.addWidget(undo_btn)

        redo_btn = QPushButton("Redo")
        redo_btn.setIcon(self._icon('fa5s.redo'))
        redo_btn.clicked.connect(self.redo_requested.emit)
        action_row.addWidget(redo_btn)

        layout.addLayout(action_row)

        edit_row = QHBoxLayout()
        edit_row.setSpacing(4)
        
        dup_btn = QPushButton("Duplicate")
        dup_btn.setIcon(self._icon('fa5s.copy'))
        dup_btn.clicked.connect(self.duplicate_requested.emit)
        edit_row.addWidget(dup_btn)

        del_btn = QPushButton("Delete")
        del_btn.setIcon(self._icon('fa5s.trash'))
        del_btn.clicked.connect(self.delete_requested.emit)
        edit_row.addWidget(del_btn)
        
        layout.addLayout(edit_row)

        clear_btn = QPushButton("Clear Canvas")
        clear_btn.setIcon(self._icon('fa5s.trash-alt', '#E5484D'))
        clear_btn.setObjectName("danger_button")
        clear_btn.clicked.connect(self.clear_canvas.emit)
        layout.addWidget(clear_btn)

        layout.addWidget(self._sep())

        # ── Background ───────────────────────────────────────────────
        layout.addWidget(self._section("Background"))

        grid_row = QHBoxLayout()
        grid_row.setSpacing(8)
        grid_lbl = QLabel("Grid")
        grid_lbl.setObjectName("fps_label")
        grid_row.addWidget(grid_lbl)
        self._grid_combo = QComboBox()
        self._grid_combo.addItems([
            "None", "Lines", "Graph", "Dots", "Music Staff", "Cornell"
        ])
        self._grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        grid_row.addWidget(self._grid_combo)
        layout.addLayout(grid_row)

        bg_row = QHBoxLayout()
        bg_row.setSpacing(4)
        load_bg_btn = QPushButton("Image")
        load_bg_btn.setIcon(self._icon('fa5s.image'))
        load_bg_btn.clicked.connect(self.background_image_requested.emit)
        bg_row.addWidget(load_bg_btn)
        clear_bg_btn = QPushButton("Clear")
        clear_bg_btn.setIcon(self._icon('fa5s.times'))
        clear_bg_btn.clicked.connect(self.clear_background_requested.emit)
        bg_row.addWidget(clear_bg_btn)
        layout.addLayout(bg_row)

        self._theme_btn = self._toggle("Light Mode", 'fa5s.sun')
        self._theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self._theme_btn)

        layout.addWidget(self._sep())

        # ── Voice ────────────────────────────────────────────────────
        layout.addWidget(self._section("Voice"))
        self._voice_btn = self._toggle("Voice Commands", 'fa5s.microphone')
        self._voice_btn.clicked.connect(
            lambda: self.voice_toggled.emit(self._voice_btn.isChecked())
        )
        layout.addWidget(self._voice_btn)

        self._voice_status = QLabel("Off")
        self._voice_status.setObjectName("fps_label")
        layout.addWidget(self._voice_status)

        self._voice_last_cmd = QLabel("")
        self._voice_last_cmd.setObjectName("fps_label")
        self._voice_last_cmd.setWordWrap(True)
        layout.addWidget(self._voice_last_cmd)

        layout.addWidget(self._sep())

        # ── Workspace ────────────────────────────────────────────────
        layout.addWidget(self._section("Workspace"))
        ws_row = QHBoxLayout()
        ws_row.setSpacing(4)

        save_ws_btn = QPushButton("Save")
        save_ws_btn.setIcon(self._icon('fa5s.save'))
        save_ws_btn.clicked.connect(self.save_requested.emit)
        ws_row.addWidget(save_ws_btn)

        load_ws_btn = QPushButton("Load")
        load_ws_btn.setIcon(self._icon('fa5s.folder-open'))
        load_ws_btn.clicked.connect(self.load_workspace_requested.emit)
        ws_row.addWidget(load_ws_btn)

        layout.addLayout(ws_row)
        layout.addWidget(self._sep())

        # ── Export ───────────────────────────────────────────────────
        layout.addWidget(self._section("Export"))
        export_row = QHBoxLayout()
        export_row.setSpacing(4)

        pdf_btn = QPushButton("PDF")
        pdf_btn.setIcon(self._icon('fa5s.file-pdf'))
        pdf_btn.clicked.connect(self.export_pdf_requested.emit)
        export_row.addWidget(pdf_btn)

        svg_btn = QPushButton("SVG")
        svg_btn.setIcon(self._icon('fa5s.file-code'))
        svg_btn.clicked.connect(self.export_svg_requested.emit)
        export_row.addWidget(svg_btn)

        layout.addLayout(export_row)

        # ── Bottom spacer ────────────────────────────────────────────
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ─── Widget Factories ────────────────────────────────────────────────

    def _toggle(self, text: str, icon_name: str) -> QPushButton:
        """Create a consistently styled toggle button."""
        btn = QPushButton(text)
        btn.setIcon(self._icon(icon_name))
        btn.setCheckable(True)
        btn.setObjectName("toggle_button")
        return btn

    @staticmethod
    def _section(text: str) -> QLabel:
        """Create a styled section title label."""
        label = QLabel(text)
        label.setObjectName("section_title")
        return label

    @staticmethod
    def _sep() -> QFrame:
        """Create a horizontal separator line."""
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep

    # ─── Public Methods ──────────────────────────────────────────────────

    def get_camera_widget(self) -> CameraWidget:
        """Get the camera preview widget for connecting to HandTracker."""
        return self._camera_widget

    def update_gesture_status(self, mode: GestureMode):
        """Update the gesture status display."""
        info = GESTURE_MODE_INFO.get(mode, GESTURE_MODE_INFO[GestureMode.NEUTRAL])
        color = info["color"]
        self._gesture_dot.setStyleSheet(Styles.get_status_dot_style(color))
        self._gesture_icon.setText(info["icon"])
        self._gesture_label.setText(info["label"])
        self._gesture_label.setStyleSheet(f"color: {color};")
        self._gesture_desc.setText(info["description"])
        # Update left accent border on the card
        self._gesture_card.setStyleSheet(
            f"QWidget#gesture_status_card {{ border-left: 3px solid {color}; }}"
        )

    def update_fps(self, fps: float):
        """Update the FPS display."""
        self._fps_label.setText(f"{fps:.0f} fps")

    def update_hand_status(self, detected: bool):
        """Update the hand detection indicator."""
        if detected:
            self._hand_indicator.setText("Hand detected")
            self._hand_indicator.setStyleSheet("color: #46A758;")
        else:
            self._hand_indicator.setText("No hand")
            self._hand_indicator.setStyleSheet("color: #555555;")

    def update_voice_status(self, status: str):
        """Update the voice command status text."""
        self._voice_status.setText(status)

    def update_voice_last_command(self, command: str):
        """Update the last recognized voice command display."""
        self._voice_last_cmd.setText(command)

    def is_laser_active(self) -> bool:
        return self._laser_active

    def is_highlighter_active(self) -> bool:
        return self._highlighter_active

    def is_dynamic_width_active(self) -> bool:
        return self._dynamic_width_btn.isChecked()

    def is_galaxy_brush_active(self) -> bool:
        return getattr(self, '_galaxy_active', False)

    # ─── Private Slots ───────────────────────────────────────────────────

    def _on_color_picked(self, hex_color: str):
        self._selected_color = hex_color
        for swatch in self._color_swatches:
            idx = self._color_swatches.index(swatch)
            is_selected = COLOR_PALETTE[idx] == hex_color
            swatch.setStyleSheet(Styles.get_color_swatch_style(
                COLOR_PALETTE[idx], is_selected
            ))
        self.pen_color_changed.emit(QColor(hex_color))

    def _on_pen_size_changed(self, value: int):
        size = value / 10.0
        self._pen_value.setText(f"{size:.1f}")
        self.pen_size_changed.emit(size)

    def _on_eraser_size_changed(self, value: int):
        self._eraser_value.setText(f"{value}")
        self.eraser_size_changed.emit(float(value))

    def _on_camera_toggle(self):
        self._camera_running = not self._camera_running
        if self._camera_running:
            self._camera_toggle.setText("Stop Camera")
            self._camera_toggle.setIcon(self._icon('fa5s.stop', '#E5484D'))
            self._camera_toggle.setObjectName("danger_button")
        else:
            self._camera_toggle.setText("Start Camera")
            self._camera_toggle.setIcon(self._icon('fa5s.video'))
            self._camera_toggle.setObjectName("primary_button")
        self._camera_toggle.style().unpolish(self._camera_toggle)
        self._camera_toggle.style().polish(self._camera_toggle)
        self.camera_toggled.emit(self._camera_running)

    def _on_laser_toggle(self):
        self._laser_active = self._laser_btn.isChecked()
        if self._laser_active:
            if self._highlighter_active:
                self._highlighter_btn.setChecked(False)
                self._highlighter_active = False
                self._highlighter_color_row.setVisible(False)
                self.highlighter_toggled.emit(False)
            if hasattr(self, '_galaxy_active') and self._galaxy_active:
                self._galaxy_btn.setChecked(False)
                self._galaxy_active = False
                self.galaxy_brush_toggled.emit(False)
        self.laser_mode_toggled.emit(self._laser_active)

    def _on_highlighter_toggle(self):
        self._highlighter_active = self._highlighter_btn.isChecked()
        if self._highlighter_active:
            if self._laser_active:
                self._laser_btn.setChecked(False)
                self._laser_active = False
                self.laser_mode_toggled.emit(False)
            if hasattr(self, '_galaxy_active') and self._galaxy_active:
                self._galaxy_btn.setChecked(False)
                self._galaxy_active = False
                self.galaxy_brush_toggled.emit(False)
        self._highlighter_color_row.setVisible(self._highlighter_active)
        self.highlighter_toggled.emit(self._highlighter_active)

    def _on_galaxy_toggle(self):
        self._galaxy_active = self._galaxy_btn.isChecked()
        if self._galaxy_active:
            if self._laser_active:
                self._laser_btn.setChecked(False)
                self._laser_active = False
                self.laser_mode_toggled.emit(False)
            if self._highlighter_active:
                self._highlighter_btn.setChecked(False)
                self._highlighter_active = False
                self._highlighter_color_row.setVisible(False)
                self.highlighter_toggled.emit(False)
        self.galaxy_brush_toggled.emit(self._galaxy_active)

    def _on_highlighter_color_picked(self, hex_color: str):
        for i, swatch in enumerate(self._hl_swatches):
            is_sel = HIGHLIGHTER_COLORS[i] == hex_color
            swatch.setStyleSheet(Styles.get_color_swatch_style(HIGHLIGHTER_COLORS[i], is_sel))
        self.highlighter_color_changed.emit(QColor(hex_color))

    def _on_grid_changed(self, index: int):
        try:
            from canvas.grid_renderer import GridType
            grid_map = {
                0: GridType.NONE, 1: GridType.LINES, 2: GridType.GRAPH,
                3: GridType.DOTS, 4: GridType.MUSIC_STAFF, 5: GridType.CORNELL,
            }
            self.grid_type_changed.emit(grid_map.get(index, GridType.NONE))
        except ImportError:
            pass

    def _on_theme_toggle(self):
        is_light = self._theme_btn.isChecked()
        self._theme_btn.setText("Dark Mode" if is_light else "Light Mode")
        self._theme_btn.setIcon(self._icon('fa5s.moon' if is_light else 'fa5s.sun'))
        self.theme_toggled.emit(is_light)

    # Keep old static method names for backward compat
    @staticmethod
    def _create_section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section_title")
        return label

    @staticmethod
    def _create_separator() -> QFrame:
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep
