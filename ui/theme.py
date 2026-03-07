"""
ui/theme.py
-----------
Single source of truth for every visual token in the Gallery Inspector UI.

Usage
-----
    from .theme import theme          # use the shared default instance
    theme.btn_analysis_fg = "#..."   # mutate before the window is created
    # — or —
    from .theme import Theme
    GalleryInspectorUI.theme = Theme(btn_analysis_fg="#...")
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Theme:
    # ── Window ────────────────────────────────────────────────────────────────
    window_geometry: str = "1000x900"
    appearance_mode: str = "System"  # "Light" | "Dark" | "System"
    color_theme: str = "dark-blue"  # built-in CTk palette name

    # ── Fonts  (family, size, weight) ────────────────────────────────────────
    font_title: Tuple = ("Arial", 18, "bold")  # "Project Paths"
    font_section: Tuple = ("Arial", 16, "bold")  # section headers
    font_label_bold: Tuple = ("Arial", 14, "bold")  # component headers
    font_label: Tuple = ("Arial", 14)  # ordinary labels

    # ── Action-button dimensions ──────────────────────────────────────────────
    btn_action_height: int = 40
    btn_action_width: int = 150
    btn_icon_size: int = 40  # height & width for ⏸ ⏹
    btn_small_size: int = 30  # height & width for ▲ ▼ and "X"
    btn_browse_width: int = 100  # "Browse" in PathSelector
    btn_browse_folder_width: int = 120  # "Browse Folders" in MultiPathSelector
    btn_logs_width: int = 80  # "Show/Hide Logs"

    # ── Component dimensions ──────────────────────────────────────────────────
    drop_frame_height: int = 150  # drag-and-drop zone height
    path_list_height: int = 150  # scrollable path list height
    log_textbox_height: int = 150  # collapsible log textbox height
    progress_bar_width: int = 400
    filter_label_width: int = 120  # fixed-width label column in FilterOptionsFrame

    # ── Colors: action buttons ────────────────────────────────────────────────
    btn_analysis_fg: str = "#303030"  # Run Analysis   (dark green)
    btn_analysis_hover: str = "#1D1D1D"
    btn_filter_fg: str = "#133D52"  # Start Filtering (dark blue)
    btn_filter_hover: str = "#13263b"
    btn_pause_fg: str = "#3b8ed0"  # Pause           (mid blue)
    btn_pause_hover: str = "#36719f"
    btn_stop_fg: str = "#ff4a4c"  # Stop            (red)
    btn_stop_hover: str = "#933032"
    btn_logs_fg: str = "#303030"  # Show/Hide Logs  (mid blue)
    btn_logs_hover: str = "#1D1D1D"

    # ── Colors: status text ───────────────────────────────────────────────────
    status_ready: str = "gray"
    status_running: str = "orange"
    status_paused: str = "yellow"
    status_success: str = "green"
    status_error: str = "red"
    status_stopped: str = "red"

    # ── Colors: components ────────────────────────────────────────────────────
    drop_zone_border: str = "gray"  # drag-zone border (idle)
    drop_zone_hover: str = "#ffffff"  # drag-zone border (mouse-over)
    remove_path_fg: str = "#ff4a4c"  # "X" button on path entries
    remove_path_hover: str = "#933032"
    muted_text: str = "gray"  # placeholder / hint text


# Shared default instance.  Import this throughout the package so every widget
# reads from the same object.  Mutate fields before the window is created to
# apply a custom theme without subclassing.
theme = Theme()
