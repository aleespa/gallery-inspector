import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os


class MultiPathSelector(ctk.CTkFrame):
    def __init__(self, parent, label_text, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.paths = []

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=label_text, font=("Arial", 14, "bold"))
        self.label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Drag and Drop Area
        self.drop_frame = ctk.CTkFrame(
            self, height=100, border_width=2, border_color="gray"
        )
        self.drop_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.drop_frame.grid_propagate(False)
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_frame.grid_rowconfigure(0, weight=1)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame, text="Drag & Drop Folders Here\nor", text_color="gray"
        )
        self.drop_label.grid(row=0, column=0, pady=(10, 0))

        self.browse_btn = ctk.CTkButton(
            self.drop_frame,
            text="Browse Folders",
            width=120,
            command=self._browse_folders,
        )
        self.browse_btn.grid(row=1, column=0, pady=(0, 10))

        # List of added paths
        self.list_frame = ctk.CTkScrollableFrame(self, height=150)
        self.list_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Register for Drag and Drop
        # We need to use the actual tkinter widget for dnd2
        self.drop_frame.bind(
            "<Enter>", lambda e: self.drop_frame.configure(border_color="blue")
        )
        self.drop_frame.bind(
            "<Leave>", lambda e: self.drop_frame.configure(border_color="gray")
        )

        # This will be called from app.py to set up the actual dnd hooks
        # because the main window needs to be a TkinterDnD.Tk instance

    def setup_dnd(self, tk_widget):
        tk_widget.drop_target_register(DND_FILES)
        tk_widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        data = event.data
        # Handle different platforms and multiple files
        if data.startswith("{"):
            # Windows style multiple paths with spaces
            import re

            paths = re.findall(r"\{(.*?)\}", data)
            if not paths:
                paths = data.split()  # fallback
        else:
            paths = data.split()  # might not work with spaces

        # Refined path splitting for Windows if curly braces are not used
        if not data.startswith("{") and " " in data:
            # Try to split by spaces but respect quoted paths if dnd2 provides them
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
                self.list_frame, text="No directories added", text_color="gray"
            ).grid(row=0, column=0, pady=20)
            return

        for idx, path in enumerate(self.paths):
            item = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            item.grid(row=idx, column=0, sticky="ew", pady=2)
            item.grid_columnconfigure(0, weight=1)

            lbl = ctk.CTkLabel(item, text=path, anchor="w", wraplength=300)
            lbl.grid(row=0, column=0, sticky="w", padx=5)

            btn = ctk.CTkButton(
                item,
                text="X",
                width=30,
                height=30,
                fg_color="#ff4a4c",
                hover_color="#933032",
                command=lambda p=path: self.remove_path(p),
            )
            btn.grid(row=0, column=1, padx=5)

    def get_paths(self):
        return self.paths


class PathSelector(ctk.CTkFrame):
    def __init__(self, parent, label_text, browse_callback, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=label_text)
        self.label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.entry_frame.grid(row=1, column=0, sticky="ew")
        self.entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.entry_frame)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn = ctk.CTkButton(
            self.entry_frame,
            text="Browse",
            width=100,
            command=lambda: browse_callback(self.entry),
        )
        self.btn.grid(row=0, column=1)

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

        self.label = ctk.CTkLabel(
            self,
            text="Folder Structure (Order: Top to Bottom)",
            font=("Arial", 12, "bold"),
        )
        self.label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Available options frame (Checkboxes)
        self.checkbox_frame = ctk.CTkFrame(self)
        self.checkbox_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self.option_vars = {}
        for idx, option in enumerate(self.available_options):
            var = tk.BooleanVar(value=option in self.selected_options)
            self.option_vars[option] = var
            cb = ctk.CTkCheckBox(
                self.checkbox_frame,
                text=option,
                variable=var,
                command=lambda o=option: self._on_checkbox_toggle(o),
            )
            cb.grid(row=0, column=idx, sticky="w", padx=10, pady=5)

        # Selected items ordering frame
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
        # Clear order frame
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
                width=30,
                command=lambda i=idx: self._move_item(i, -1),
            )
            up_btn.pack(side="left", padx=2)
            if idx == 0:
                up_btn.configure(state="disabled")

            down_btn = ctk.CTkButton(
                btn_frame,
                text="▼",
                width=30,
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
