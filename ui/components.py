# from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from theme import theme


class MultiPathSelector(ctk.CTkFrame):
    def __init__(self, parent, label_text, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.paths = []

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=label_text, font=theme.font_section).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        # Drag and Drop Area
        self.drop_frame = ctk.CTkFrame(
            self,
            height=theme.drop_frame_height,
            border_width=2,
            border_color=theme.drop_zone_border,
        )
        self.drop_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.drop_frame.grid_propagate(False)
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_frame.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            self.drop_frame,
            text="Drag & Drop Folders Here\nor",
            text_color=theme.muted_text,
        ).grid(row=0, column=0, pady=(10, 0))

        ctk.CTkButton(
            self.drop_frame,
            text="Browse Folders",
            width=theme.btn_browse_folder_width,
            command=self._browse_folders,
        ).grid(row=1, column=0, pady=(0, 10))

        # List of added paths
        self.list_frame = ctk.CTkScrollableFrame(self, height=theme.path_list_height)
        self.list_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Drag-and-drop hover feedback
        self.drop_frame.bind(
            "<Enter>",
            lambda e: self.drop_frame.configure(border_color=theme.drop_zone_hover),
        )
        self.drop_frame.bind(
            "<Leave>",
            lambda e: self.drop_frame.configure(border_color=theme.drop_zone_border),
        )

    def setup_dnd(self, tk_widget):
        pass
        # tk_widget.drop_target_register(DND_FILES)
        # tk_widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        data = event.data
        if data.startswith("{"):
            import re

            paths = re.findall(r"\{(.*?)\}", data)
            if not paths:
                paths = data.split()
        else:
            paths = data.split()

        if not data.startswith("{") and " " in data:
            import shlex

            try:
                paths = shlex.split(data)
            except ValueError:
                paths = [data]

        for p in paths:
            p = p.strip("{}")
            if os.path.isdir(p):
                self.add_path(p)

    def _browse_folders(self):
        directory = filedialog.askdirectory()
        if directory:
            self.add_path(directory)

    def add_path(self, path):
        if path not in self.paths:
            self.paths.append(path)
            self._refresh_list()

    def remove_path(self, path):
        if path in self.paths:
            self.paths.remove(path)
            self._refresh_list()

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.paths:
            ctk.CTkLabel(
                self.list_frame,
                text="No directories added",
                text_color=theme.muted_text,
            ).grid(row=0, column=0, pady=20)
            return

        for idx, path in enumerate(self.paths):
            item = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            item.grid(row=idx, column=0, sticky="ew", pady=2)
            item.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(item, text=path, anchor="w", wraplength=300).grid(
                row=0, column=0, sticky="w", padx=5
            )
            ctk.CTkButton(
                item,
                text="X",
                width=theme.btn_small_size,
                height=theme.btn_small_size,
                fg_color=theme.remove_path_fg,
                hover_color=theme.remove_path_hover,
                command=lambda p=path: self.remove_path(p),
            ).grid(row=0, column=1, padx=5)

    def get_paths(self):
        return self.paths


class PathSelector(ctk.CTkFrame):
    def __init__(self, parent, label_text, browse_callback, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=label_text).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.grid(row=1, column=0, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(entry_frame)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            entry_frame,
            text="Browse",
            width=theme.btn_browse_width,
            command=lambda: browse_callback(self.entry),
        ).grid(row=0, column=1)

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)


class StructureSelector(ctk.CTkFrame):
    def __init__(self, parent, available_options, initial_selection=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.available_options = available_options
        self.selected_options = initial_selection or []

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Folder Structure (Order: Top to Bottom)",
            font=theme.font_label_bold,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Checkboxes
        self.checkbox_frame = ctk.CTkFrame(self)
        self.checkbox_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self.option_vars = {}
        num_columns = 2
        for idx, option in enumerate(self.available_options):
            var = tk.BooleanVar(value=option in self.selected_options)
            self.option_vars[option] = var
            ctk.CTkCheckBox(
                self.checkbox_frame,
                text=option,
                variable=var,
                command=lambda o=option: self._on_checkbox_toggle(o),
            ).grid(
                row=idx // num_columns,
                column=idx % num_columns,
                sticky="w",
                padx=10,
                pady=5,
            )

        # Order view
        self.order_frame = ctk.CTkFrame(self)
        self.order_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.order_frame.grid_columnconfigure(0, weight=1)

        self._refresh_order_view()

    def _on_checkbox_toggle(self, option):
        if self.option_vars[option].get():
            if option not in self.selected_options:
                self.selected_options.append(option)
        else:
            if option in self.selected_options:
                self.selected_options.remove(option)
        self._refresh_order_view()

    def _refresh_order_view(self):
        for widget in self.order_frame.winfo_children():
            widget.destroy()

        if not self.selected_options:
            ctk.CTkLabel(self.order_frame, text="No fields selected").pack(pady=5)
            return

        for idx, option in enumerate(self.selected_options):
            item_frame = ctk.CTkFrame(self.order_frame, fg_color="transparent")
            item_frame.pack(fill="x", padx=5, pady=2)

            ctk.CTkLabel(
                item_frame, text=f"{idx + 1}. {option}", width=100, anchor="w"
            ).pack(side="left", padx=5)

            btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            btn_frame.pack(side="right")

            up_btn = ctk.CTkButton(
                btn_frame,
                text="▲",
                width=theme.btn_small_size,
                command=lambda i=idx: self._move_item(i, -1),
            )
            up_btn.pack(side="left", padx=2)
            if idx == 0:
                up_btn.configure(state="disabled")

            down_btn = ctk.CTkButton(
                btn_frame,
                text="▼",
                width=theme.btn_small_size,
                command=lambda i=idx: self._move_item(i, 1),
            )
            down_btn.pack(side="left", padx=2)
            if idx == len(self.selected_options) - 1:
                down_btn.configure(state="disabled")

    def _move_item(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.selected_options):
            self.selected_options[index], self.selected_options[new_index] = (
                self.selected_options[new_index],
                self.selected_options[index],
            )
            self._refresh_order_view()

    def get(self):
        return self.selected_options


class FilterOptionsFrame(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        # Filetype
        filetype_frame = ctk.CTkFrame(self, fg_color="transparent")
        filetype_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(
            filetype_frame,
            text="File Types:",
            width=theme.filter_label_width,
            anchor="w",
        ).pack(side="left")

        self.video_var = ctk.BooleanVar()
        self.photo_var = ctk.BooleanVar()
        self.other_var = ctk.BooleanVar()

        ctk.CTkCheckBox(filetype_frame, text="Videos", variable=self.video_var).pack(
            side="left", padx=10
        )
        ctk.CTkCheckBox(filetype_frame, text="Photos", variable=self.photo_var).pack(
            side="left", padx=10
        )
        ctk.CTkCheckBox(filetype_frame, text="Other", variable=self.other_var).pack(
            side="left", padx=10
        )

        # Extensions
        self.extensions_entry = self._row(1, "Extensions:", "e.g. .jpg, .mp4")

        # Date Range
        self.start_date_entry, self.end_date_entry = self._range_row(
            2, "Date Range:", "YYYY-MM-DD", "YYYY-MM-DD"
        )

        # Camera and Lens
        self.camera_entry = self._row(3, "Camera(s):", "comma-separated")
        self.lens_entry = self._row(4, "Lens(es):", "comma-separated")

        # Aperture Range
        self.min_aperture_entry, self.max_aperture_entry = self._range_row(
            5, "Aperture:", "Min", "Max"
        )

        # ISO Range
        self.min_iso_entry, self.max_iso_entry = self._range_row(
            6, "ISO:", "Min", "Max"
        )

        # Shutter Speed Range
        self.min_shutter_entry, self.max_shutter_entry = self._range_row(
            7, "Shutter Speed:", "Min (e.g. 1/100)", "Max"
        )

    def _row(self, row, label_text, placeholder):
        ctk.CTkLabel(
            self, text=label_text, width=theme.filter_label_width, anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entry = ctk.CTkEntry(self, placeholder_text=placeholder)
        entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        return entry

    def _range_row(self, row, label_text, p1, p2):
        ctk.CTkLabel(
            self, text=label_text, width=theme.filter_label_width, anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=10, pady=5)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=1, sticky="ew", padx=0, pady=5)
        frame.grid_columnconfigure((0, 2), weight=1)

        e1 = ctk.CTkEntry(frame, placeholder_text=p1)
        e1.grid(row=0, column=0, sticky="ew", padx=(10, 5))

        ctk.CTkLabel(frame, text="to").grid(row=0, column=1, padx=5)

        e2 = ctk.CTkEntry(frame, placeholder_text=p2)
        e2.grid(row=0, column=2, sticky="ew", padx=(5, 10))

        return e1, e2

    def get_query(self):
        from gallery_inspector.filtering import FilterOptions
        from datetime import date

        filetypes = []
        if self.video_var.get():
            filetypes.append("video")
        if self.photo_var.get():
            filetypes.append("image")
        if self.other_var.get():
            filetypes.append("other")

        extensions = [
            e.strip() for e in self.extensions_entry.get().split(",") if e.strip()
        ]

        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()
        date_range = None
        try:
            start_date = date.fromisoformat(start_date_str) if start_date_str else None
            end_date = date.fromisoformat(end_date_str) if end_date_str else None
            if start_date or end_date:
                date_range = (start_date, end_date)
        except ValueError:
            pass

        cameras = [c.strip() for c in self.camera_entry.get().split(",") if c.strip()]
        lenses = [l.strip() for l in self.lens_entry.get().split(",") if l.strip()]

        min_ap = (
            float(self.min_aperture_entry.get())
            if self.min_aperture_entry.get()
            else None
        )
        max_ap = (
            float(self.max_aperture_entry.get())
            if self.max_aperture_entry.get()
            else None
        )
        aperture_range = (
            (min_ap, max_ap) if min_ap is not None or max_ap is not None else None
        )

        min_iso = int(self.min_iso_entry.get()) if self.min_iso_entry.get() else None
        max_iso = int(self.max_iso_entry.get()) if self.max_iso_entry.get() else None
        iso_range = (
            (min_iso, max_iso) if min_iso is not None or max_iso is not None else None
        )

        min_ss = self.min_shutter_entry.get() if self.min_shutter_entry.get() else None
        max_ss = self.max_shutter_entry.get() if self.max_shutter_entry.get() else None
        shutter_speed_range = (min_ss, max_ss) if min_ss or max_ss else None

        return FilterOptions(
            filetypes=filetypes or None,
            extensions=extensions or None,
            date_range=date_range,
            cameras=cameras or None,
            lenses=lenses or None,
            aperture_range=aperture_range,
            iso_range=iso_range,
            shutter_speed_range=shutter_speed_range,
        )
