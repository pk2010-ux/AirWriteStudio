"""
AirWrite Studio - Styles
==========================
Minimal, professional dark theme inspired by Linear, Apple, and Notion.
Clean typography, intentional spacing, and restrained color palette.
"""


class Styles:
    """
    Centralized stylesheet and color constants for the application.
    Provides a refined, minimal dark theme with strong contrast.
    """

    # ─── Color Palette (restrained — 2 primary + 1 accent) ──────────────
    BG_BASE = '#161616'       # App background
    BG_SURFACE = '#1E1E1E'    # Sidebar / panels
    BG_ELEVATED = '#262626'   # Cards, inputs, dropdowns
    BG_HOVER = '#2E2E2E'      # Hover state
    BG_ACTIVE = '#363636'     # Pressed / active state

    ACCENT = '#0091FF'        # Primary accent — clear blue (Linear-style)
    ACCENT_HOVER = '#0081E6'  # Slightly darker for hover
    ACCENT_MUTED = 'rgba(0, 145, 255, 0.12)'  # Subtle tint

    TEXT_PRIMARY = '#EDEDED'   # High contrast primary text
    TEXT_SECONDARY = '#888888' # Muted secondary text
    TEXT_TERTIARY = '#555555'  # Very muted (placeholders, disabled)

    BORDER = '#2A2A2A'        # Subtle border
    BORDER_HOVER = '#3A3A3A'  # Border on hover

    DANGER = '#E5484D'        # Destructive actions
    DANGER_BG = 'rgba(229, 72, 77, 0.08)'
    SUCCESS = '#46A758'       # Positive feedback

    @staticmethod
    def get_main_stylesheet() -> str:
        """
        Returns the complete QSS stylesheet for the application.
        """
        return """
        /* ─── Global ─────────────────────────────────────────────── */

        QMainWindow {
            background-color: #161616;
        }

        QWidget {
            color: #EDEDED;
            font-family: 'Inter', 'Segoe UI Variable', -apple-system, 'Segoe UI', sans-serif;
            font-size: 13px;
        }

        /* ─── Sidebar ────────────────────────────────────────────── */

        QWidget#sidebar {
            background-color: #1E1E1E;
            border-right: 1px solid #2A2A2A;
        }

        QWidget#sidebar_content {
            background-color: transparent;
        }

        /* ─── Section Titles ─────────────────────────────────────── */

        QLabel#section_title {
            color: #555555;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.5px;
            padding: 8px 0px 4px 0px;
        }

        /* ─── App Title ──────────────────────────────────────────── */

        QLabel#app_title {
            font-size: 18px;
            font-weight: 700;
            color: #0091FF;
            letter-spacing: 1.5px;
            padding: 4px 0px 0px 0px;
            text-transform: uppercase;
        }

        QLabel#app_subtitle {
            font-size: 12px;
            color: #555555;
            font-weight: 400;
            padding-bottom: 4px;
        }

        /* ─── Buttons ────────────────────────────────────────────── */

        QPushButton {
            background-color: #262626;
            color: #EDEDED;
            border: 1px solid #2A2A2A;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 500;
            font-size: 12px;
            min-height: 18px;
        }

        QPushButton:hover {
            background-color: #2E2E2E;
            border-color: #3A3A3A;
        }

        QPushButton:pressed {
            background-color: #363636;
        }

        QPushButton:disabled {
            background-color: #1E1E1E;
            color: #444444;
            border-color: #252525;
        }

        QPushButton#primary_button {
            background-color: #0091FF;
            border: 1px solid #0091FF;
            color: #FFFFFF;
            font-weight: 600;
        }

        QPushButton#primary_button:hover {
            background-color: #0081E6;
            border-color: #0081E6;
        }

        QPushButton#primary_button:pressed {
            background-color: #0070CC;
            border-color: #0070CC;
        }

        QPushButton#danger_button {
            background-color: rgba(229, 72, 77, 0.08);
            border: 1px solid rgba(229, 72, 77, 0.25);
            color: #E5484D;
        }

        QPushButton#danger_button:hover {
            background-color: rgba(229, 72, 77, 0.15);
            border-color: rgba(229, 72, 77, 0.4);
        }

        QPushButton#toggle_button {
            background-color: #262626;
            border: 1px solid #2A2A2A;
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 11px;
        }

        QPushButton#toggle_button:hover {
            background-color: #2E2E2E;
            border-color: #3A3A3A;
        }

        QPushButton#toggle_button:checked {
            background-color: rgba(0, 145, 255, 0.12);
            border-color: rgba(0, 145, 255, 0.3);
            color: #0091FF;
        }

        /* ─── Sliders ────────────────────────────────────────────── */

        QSlider::groove:horizontal {
            height: 3px;
            background-color: #2A2A2A;
            border-radius: 1px;
        }

        QSlider::handle:horizontal {
            width: 12px;
            height: 12px;
            margin: -5px 0;
            background: #EDEDED;
            border-radius: 6px;
            border: none;
        }

        QSlider::handle:horizontal:hover {
            background: #FFFFFF;
        }

        QSlider::sub-page:horizontal {
            background: #0091FF;
            border-radius: 1px;
        }

        /* ─── Labels ─────────────────────────────────────────────── */

        QLabel {
            color: #EDEDED;
            background: transparent;
        }

        QLabel#value_label {
            color: #888888;
            font-weight: 500;
            font-size: 12px;
            min-width: 30px;
        }

        QLabel#status_label {
            font-size: 13px;
            font-weight: 600;
            padding: 0px;
        }

        QLabel#fps_label {
            color: #555555;
            font-size: 11px;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        }

        QLabel#fps_badge {
            color: #888888;
            font-size: 10px;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
            font-weight: 500;
            background-color: #2A2A2A;
            border-radius: 4px;
            padding: 2px 6px;
        }

        QLabel#status_desc {
            color: #666666;
            font-size: 11px;
            padding: 0px;
        }

        QLabel#hand_status {
            font-size: 11px;
            font-weight: 500;
            color: #555555;
        }

        /* ─── Gesture Status Card ───────────────────────────────── */

        QWidget#gesture_status_card {
            background-color: #222222;
            border: 1px solid #2A2A2A;
            border-left: 3px solid #333333;
            border-radius: 8px;
        }

        /* ─── Scroll Area ────────────────────────────────────────── */

        QScrollArea {
            background: transparent;
            border: none;
        }

        QScrollBar:vertical {
            background-color: transparent;
            width: 4px;
            margin: 0px;
        }

        QScrollBar::handle:vertical {
            background-color: #3A3A3A;
            min-height: 30px;
            border-radius: 2px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #555555;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }

        /* ─── ComboBox ───────────────────────────────────────────── */

        QComboBox {
            background-color: #262626;
            border: 1px solid #2A2A2A;
            border-radius: 6px;
            padding: 5px 10px;
            color: #EDEDED;
            min-height: 20px;
            font-size: 12px;
        }

        QComboBox:hover {
            border-color: #3A3A3A;
        }

        QComboBox::drop-down {
            border: none;
            padding-right: 6px;
        }

        QComboBox QAbstractItemView {
            background-color: #262626;
            border: 1px solid #3A3A3A;
            border-radius: 6px;
            color: #EDEDED;
            padding: 4px;
            selection-background-color: rgba(0, 145, 255, 0.12);
            selection-color: #0091FF;
        }

        /* ─── Separator ──────────────────────────────────────────── */

        QFrame#separator {
            background-color: #2A2A2A;
            max-height: 1px;
            margin: 4px 0px;
        }

        /* ─── Group Boxes ────────────────────────────────────────── */

        QGroupBox {
            background-color: #1E1E1E;
            border: 1px solid #2A2A2A;
            border-radius: 8px;
            margin-top: 12px;
            padding: 16px 10px 10px 10px;
            font-weight: 500;
            font-size: 12px;
            color: #888888;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0px 8px;
            color: #888888;
            font-size: 11px;
            font-weight: 500;
            background-color: #1E1E1E;
        }
        """

    @staticmethod
    def get_status_dot_style(color: str) -> str:
        """
        Generate inline QSS for a colored status indicator dot.
        """
        return f"""
            background-color: {color};
            border-radius: 4px;
            min-width: 8px;
            max-width: 8px;
            min-height: 8px;
            max-height: 8px;
            border: none;
        """

    @staticmethod
    def get_color_swatch_style(color: str, selected: bool = False) -> str:
        """
        Generate inline QSS for a color swatch button.
        """
        if selected:
            border = f"2px solid #EDEDED"
        else:
            border = f"1px solid #2A2A2A"
        return f"""
            background-color: {color};
            border: {border};
            border-radius: 6px;
            min-width: 26px;
            min-height: 26px;
            max-width: 26px;
            max-height: 26px;
        """
