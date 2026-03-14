import sys
import tkinter as tk
from datetime import datetime

# Mock tix for Python 3.13+ compatibility with tkinterdnd2
if not hasattr(tk, "tix"):

    class DummyTix:
        Tk = tk.Tk

    sys.modules["tkinter.tix"] = DummyTix
    tk.tix = DummyTix

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from loguru import logger

# from tkinterdnd2 import DND_FILES, TkinterDnD

from .theme import theme as _default_theme
from .components import (
    MultiPathSelector,
    PathSelector,
    StructureSelector,
    FilterOptionsFrame,
)


class GalleryInspectorUI(ctk.CTk):  # , TkinterDnD.DnDWrapper):
    """Main application window.

    Swap ``GalleryInspectorUI.theme`` for a custom :class:`~ui.theme.Theme`
    instance *before* calling ``__init__`` to restyle the entire UI.
    """

    # ── Active theme ──────────────────────────────────────────────────────────
    theme = _default_theme

    def __init__(self):
        # Apply appearance settings from the theme before creating the window
        ctk.set_appearance_mode(self.theme.appearance_mode)
        ctk.set_default_color_theme(self.theme.color_theme)

        super().__init__()
        # self.TkdndVersion = TkinterDnD._require(self)

        self.title("Gallery Inspector UI")
        self.geometry(self.theme.window_geometry)

        # Determine the application directory
        if getattr(sys, "frozen", False):
            self.app_dir = Path(sys.executable).parent
        else:
            self.app_dir = Path(__file__).resolve().parents[1]

        self.log_dir = self.app_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "app_log.log"

        logger.add(str(self.log_file), rotation="10 MB", level="DEBUG")
        logger.add(self._log_sink, level="INFO")

        t = self.theme  # shorthand used throughout __init__

        # ── Root grid ─────────────────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)  # Left column  (paths)
        self.grid_columnconfigure(1, weight=2)  # Right column (options)
        self.grid_rowconfigure(0, weight=1)  # Main content
        self.grid_rowconfigure(1, weight=0)  # Log bar

        # ── Left Column: path selectors ───────────────────────────────────────
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_frame, text="Project Paths", font=t.font_title).grid(
            row=0, column=0, pady=(0, 20), sticky="w"
        )

        self.input_selector = MultiPathSelector(self.left_frame, "Input Directories:")
        self.input_selector.grid(row=1, column=0, sticky="ew", pady=10)

        self.output_selector = PathSelector(
            self.left_frame, "Output Directory:", self.browse_directory
        )
        self.output_selector.grid(row=2, column=0, sticky="ew", pady=10)

        # ── Right Column: scrollable options + action buttons ─────────────────
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)  # scrollable expands
        self.right_frame.grid_rowconfigure(1, weight=0)  # button bar fixed

        # Scrollable options area
        self.scroll_container = ctk.CTkScrollableFrame(
            self.right_frame, fg_color="transparent"
        )
        self.scroll_container.grid(row=0, column=0, sticky="nsew")
        self.scroll_container.grid_columnconfigure(0, weight=1)

        # ── Section 1: Output Options (Options dataclass) ─────────────────────
        ctk.CTkLabel(
            self.scroll_container,
            text="Output Options",
            font=t.font_section,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 4))

        self.output_options_frame = ctk.CTkFrame(
            self.scroll_container, fg_color="transparent"
        )
        self.output_options_frame.grid(
            row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
        )
        self.output_options_frame.grid_columnconfigure((0, 1), weight=1)

        self.by_media_type_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.output_options_frame,
            text="Separate by Media Type (Photos/Videos)",
            variable=self.by_media_type_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        self.structure_selector = StructureSelector(
            self.output_options_frame,
            available_options=["Year", "Month", "Model", "Lens"],
            initial_selection=["Year", "Month"],
        )
        self.structure_selector.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=10
        )

        ctk.CTkLabel(self.output_options_frame, text="On Conflict:").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.on_exist_var = ctk.StringVar(value="rename")
        ctk.CTkComboBox(
            self.output_options_frame,
            values=["Rename", "Skip"],
            variable=self.on_exist_var,
        ).grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.verbose_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.output_options_frame,
            text="Verbose Logging",
            variable=self.verbose_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # ── Section 2: Filter Options (FilterOptions dataclass) ───────────────
        ctk.CTkLabel(
            self.scroll_container,
            text="Select:",
            font=t.font_section,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(16, 4))

        self.filter_options_frame = FilterOptionsFrame(self.scroll_container)
        self.filter_options_frame.grid(
            row=3, column=0, sticky="ew", padx=20, pady=(0, 16)
        )

        # ── Action button bar ─────────────────────────────────────────────────
        self.button_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.button_bar.grid(row=1, column=0, pady=(10, 20))

        self.analysis_button = ctk.CTkButton(
            self.button_bar,
            text="Run Analysis",
            command=lambda: self.run_process("analysis"),
            fg_color=t.btn_analysis_fg,
            hover_color=t.btn_analysis_hover,
            height=t.btn_action_height,
            width=t.btn_action_width,
        )
        self.analysis_button.grid(row=0, column=0, padx=5)

        self.filter_button = ctk.CTkButton(
            self.button_bar,
            text="Start Filtering",
            command=lambda: self.run_process("filter"),
            fg_color=t.btn_filter_fg,
            hover_color=t.btn_filter_hover,
            height=t.btn_action_height,
            width=t.btn_action_width,
        )
        self.filter_button.grid(row=0, column=1, padx=5)

        self.pause_button = ctk.CTkButton(
            self.button_bar,
            text="⏸",
            width=t.btn_icon_size,
            height=t.btn_icon_size,
            command=self.toggle_pause,
            fg_color=t.btn_pause_fg,
            hover_color=t.btn_pause_hover,
        )
        self.stop_button = ctk.CTkButton(
            self.button_bar,
            text="⏹",
            width=t.btn_icon_size,
            height=t.btn_icon_size,
            command=self.stop_process,
            fg_color=t.btn_stop_fg,
            hover_color=t.btn_stop_hover,
        )
        # pause/stop are shown only while a process is running

        # ── Log Section (collapsible) ─────────────────────────────────────────
        self.log_container = ctk.CTkFrame(self)
        self.log_container.grid(row=1, column=0, columnspan=2, padx=20, sticky="ew")
        self.log_container.grid_columnconfigure(0, weight=1)

        self.log_header_frame = ctk.CTkFrame(self.log_container, fg_color="transparent")
        self.log_header_frame.grid(row=0, column=0, sticky="ew")
        self.log_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.log_header_frame, text="Logs:").grid(
            row=0, column=0, sticky="w"
        )
        self.log_toggle_btn = ctk.CTkButton(
            self.log_header_frame,
            text="Show Logs",
            width=t.btn_logs_width,
            command=self.toggle_logs,
            fg_color=t.btn_logs_fg,
            hover_color=t.btn_logs_hover,
        )
        self.log_toggle_btn.grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(
            self.log_container, height=t.log_textbox_height
        )
        self.log_textbox.configure(state="disabled")
        self.log_visible = False

        # ── Status / Progress ─────────────────────────────────────────────────
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color=t.status_ready)
        self.status_label.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self, width=t.progress_bar_width)
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self._active_btn = None

    # ── Process control ───────────────────────────────────────────────────────

    def stop_process(self):
        if self.stop_event:
            self.stop_event.set()
            logger.warning("Stop requested by user...")
            self.status_label.configure(
                text="Stopping...", text_color=self.theme.status_stopped
            )
            self.stop_button.configure(state="disabled")
            self.pause_button.configure(state="disabled")

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="⏸")
            self.status_label.configure(
                text="Resuming...", text_color=self.theme.status_running
            )
            logger.info("Process resumed.")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="▶")
            self.status_label.configure(
                text="Paused", text_color=self.theme.status_paused
            )
            logger.info("Process paused.")

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log_sink(self, message):
        record = message.record
        level = record["level"].name
        msg = record["message"]
        self.after(0, lambda: self.log_message(f"[{level}] {msg}"))

    def toggle_logs(self):
        if self.log_visible:
            self.log_textbox.grid_forget()
            self.log_toggle_btn.configure(text="Show Logs")
            self.log_visible = False
            self.grid_rowconfigure(2, weight=0)
        else:
            self.log_textbox.grid(row=1, column=0, pady=(5, 10), sticky="nsew")
            self.log_toggle_btn.configure(text="Hide Logs")
            self.log_visible = True
            self.grid_rowconfigure(2, weight=1)

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tk.END, f"{message}\n")
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def browse_directory(self, entry):
        directory = filedialog.askdirectory()
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)
            logger.debug(f"Selected directory: {directory}")

    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))

    def get_output_options(self):
        from gallery_inspector.generate import Options

        return Options(
            by_media_type=self.by_media_type_var.get(),
            structure=self.structure_selector.get(),
            on_exist=self.on_exist_var.get().lower(),
            verbose=self.verbose_var.get(),
        )

    def get_filter_query(self):
        return self.filter_options_frame.get_query()

    def _is_query_empty(self, query):
        """Check if the filter query has any active filters."""
        if not query:
            return True
        return not (
            query.filetypes
            or query.extensions
            or query.date_range
            or query.cameras
            or query.lenses
            or query.aperture_range
            or query.iso_range
            or query.shutter_speed_range
        )

    def _analyze_with_filters(self, all_files, query):
        """Analyze files and filter results based on query."""
        import os
        from gallery_inspector.analysis import analyze_files
        from gallery_inspector.filtering import _normalize_path, _parse_date_value, _parse_shutter_speed

        # First, analyze all files to get metadata
        df_images, df_videos, df_others = analyze_files(
            all_files,
            stop_event=self.stop_event,
            pause_event=self.pause_event,
            progress_callback=self.update_progress,
        )

        if self.stop_event.is_set():
            return df_images, df_videos, df_others

        # Build metadata lookup for filtering
        metadata_lookup = {}
        for filetype, df in [("image", df_images), ("video", df_videos), ("other", df_others)]:
            if df.empty:
                continue
            for row in df.to_dict("records"):
                full_path = row.get("Full path")
                if full_path:
                    metadata_lookup[_normalize_path(full_path)] = (filetype, row)

        # Apply filters to each dataframe
        normalized_extensions = (
            [e.lower() for e in query.extensions] if query.extensions else None
        )

        def _should_keep_file(file_path, filetype, metadata):
            """Check if a file matches the filter criteria."""
            if not metadata:
                return False

            # Filter by filetype
            if query.filetypes and filetype not in query.filetypes:
                return False

            # Photo-specific filters
            has_photo_options = (
                query.cameras or query.lenses or query.aperture_range
                or query.iso_range or query.shutter_speed_range
            )
            if has_photo_options and filetype != "image":
                return False

            # Filter by extensions
            if normalized_extensions:
                ext = Path(file_path).suffix.lower()
                if ext not in normalized_extensions:
                    return False

            # Filter by date
            if query.date_range:
                start_date, end_date = query.date_range
                dt = _parse_date_value(metadata.get("date_taken"))
                if dt:
                    if start_date and dt < start_date:
                        return False
                    if end_date and dt > end_date:
                        return False
                else:
                    return False

            # Filter by camera
            if query.cameras:
                camera = metadata.get("camera")
                if not camera or camera not in query.cameras:
                    return False

            # Filter by lens
            if query.lenses:
                lens = metadata.get("lens")
                if not lens or lens not in query.lenses:
                    return False

            # Filter by aperture
            if query.aperture_range:
                min_ap, max_ap = query.aperture_range
                aperture = metadata.get("aperture")
                if aperture is None:
                    return False
                if min_ap is not None and aperture < min_ap:
                    return False
                if max_ap is not None and aperture > max_ap:
                    return False

            # Filter by ISO
            if query.iso_range:
                min_iso, max_iso = query.iso_range
                iso = metadata.get("iso")
                if iso is None:
                    return False
                if min_iso is not None and iso < min_iso:
                    return False
                if max_iso is not None and iso > max_iso:
                    return False

            # Filter by shutter speed
            if query.shutter_speed_range:
                min_ss_str, max_ss_str = query.shutter_speed_range
                ss_str = metadata.get("shutter_speed")
                if not ss_str:
                    return False
                ss_val = _parse_shutter_speed(ss_str)
                if min_ss_str:
                    min_ss = _parse_shutter_speed(min_ss_str)
                    if ss_val < min_ss:
                        return False
                if max_ss_str:
                    max_ss = _parse_shutter_speed(max_ss_str)
                    if ss_val > max_ss:
                        return False

            return True

        # Filter each dataframe
        filtered_images = []
        filtered_videos = []
        filtered_others = []

        for file in all_files:
            metadata_entry = metadata_lookup.get(_normalize_path(file))
            if metadata_entry:
                filetype, metadata = metadata_entry
                if _should_keep_file(file, filetype, metadata):
                    if filetype == "image":
                        filtered_images.append(metadata)
                    elif filetype == "video":
                        filtered_videos.append(metadata)
                    else:
                        filtered_others.append(metadata)

        return (
            pd.DataFrame(filtered_images) if filtered_images else pd.DataFrame(),
            pd.DataFrame(filtered_videos) if filtered_videos else pd.DataFrame(),
            pd.DataFrame(filtered_others) if filtered_others else pd.DataFrame(),
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def run_process(self, func):
        btn = self.analysis_button if func == "analysis" else self.filter_button

        input_paths = self.input_selector.get_paths()
        output_path = self.output_selector.get()

        if not input_paths or not output_path:
            messagebox.showerror(
                "Error",
                "Please select at least one input directory and an output directory.",
            )
            return

        btn.configure(state="disabled")
        self._active_btn = btn
        self.stop_event.clear()
        self.pause_event.clear()

        # Show pause / stop buttons
        self.pause_button.configure(text="⏸", state="normal")
        self.pause_button.grid(row=0, column=2, padx=5)
        self.stop_button.configure(state="normal")
        self.stop_button.grid(row=0, column=3, padx=5)

        self.status_label.configure(
            text=f"Processing {func}...", text_color=self.theme.status_running
        )
        self.progress_bar.set(0)
        self.progress_bar.grid()
        logger.info(f"START: {func.capitalize()} process initiated.")

        threading.Thread(
            target=self.execute, args=(func, input_paths, output_path, btn), daemon=True
        ).start()

    def execute(self, func, input_paths, output_path, btn):  # noqa: C901
        from gallery_inspector.filtering import filter_files, FilterOptions
        from gallery_inspector.export import export_files_table
        from gallery_inspector.analysis import analyze_files

        try:
            input_ps = [Path(p) for p in input_paths]
            output_p = Path(output_path)

            if func == "analysis":
                query = self.get_filter_query()

                # Collect all files from input directories
                all_files = [
                    file for p in input_ps for file in p.rglob("*") if not file.is_dir()
                ]

                if not all_files:
                    logger.warning("No files found to analyze.")
                    df_images, df_videos, df_others = (
                        pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
                    )
                elif self._is_query_empty(query):
                    # No filters applied, analyze all files
                    df_images, df_videos, df_others = analyze_files(
                        all_files,
                        stop_event=self.stop_event,
                        pause_event=self.pause_event,
                        progress_callback=self.update_progress,
                    )
                else:
                    # Apply filters: first analyze, then filter
                    df_images, df_videos, df_others = self._analyze_with_filters(
                        all_files, query
                    )
                if self.stop_event.is_set():
                    logger.warning("Analysis cancelled by user.")
                    self.after(0, lambda: self.finish_stopped(btn))
                    return
                name_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                analysis_dir = output_p / f"Analysis {name_date}"
                analysis_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = analysis_dir / "Metadata.xlsx"
                export_files_table(df_images, df_videos, df_others, output_file)
                
                figures_dir = analysis_dir / "Figures"
                figures_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    from gallery_inspector.figures import generate_plots
                    generate_plots(output_file, figures_dir)
                except Exception as e:
                    logger.error(f"Failed to generate plots: {e}")
                
                msg = f"Analysis complete. Results saved to {analysis_dir}"

            elif func == "filter":
                query = self.get_filter_query()
                options = self.get_output_options()

                all_files = [
                    file for p in input_ps for file in p.rglob("*") if not file.is_dir()
                ]
                filter_files(
                    all_files,
                    output_p,
                    options,
                    query,
                    stop_event=self.stop_event,
                    pause_event=self.pause_event,
                    progress_callback=self.update_progress,
                )
                if self.stop_event.is_set():
                    logger.warning("Filtering cancelled by user.")
                    self.after(0, lambda: self.finish_stopped(btn))
                    return
                msg = f"Filtering complete. Filtered files organized in {output_p}"

            logger.info(msg)
            self.after(0, lambda: self.finish_success(msg, btn))
        except Exception as e:
            if self.stop_event.is_set():
                self.after(0, lambda: self.finish_stopped(btn))
            else:
                err_msg = str(e)
                logger.exception(f"Unexpected error: {err_msg}")
                self.after(0, lambda: self.finish_error(err_msg, btn))

    def _hide_run_controls(self, btn):
        btn.configure(state="normal")
        self.pause_button.grid_forget()
        self.stop_button.grid_forget()
        self.progress_bar.grid_remove()

    def finish_success(self, msg, btn):
        self._hide_run_controls(btn)
        self.status_label.configure(
            text="Success!", text_color=self.theme.status_success
        )
        messagebox.showinfo("Success", msg)

    def finish_error(self, err, btn):
        self._hide_run_controls(btn)
        self.status_label.configure(
            text="Error occurred", text_color=self.theme.status_error
        )
        messagebox.showerror("Error", f"An error occurred: {err}")

    def finish_stopped(self, btn):
        self._hide_run_controls(btn)
        self.status_label.configure(
            text="Stopped", text_color=self.theme.status_stopped
        )
        messagebox.showwarning("Stopped", "Process was stopped by user.")
