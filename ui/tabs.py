import customtkinter as ctk

from .components import PathSelector, StructureSelector


class BaseTab(ctk.CTkFrame):
    def __init__(
        self, parent, app, title, description, button_text, run_callback, **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.run_callback = run_callback

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=description, font=("Arial", 16, "bold")).grid(
            row=0, column=0, pady=10
        )

        # Button container
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=3, column=0, pady=20)

        self.run_button = ctk.CTkButton(
            self.button_frame,
            text=button_text,
            command=self.on_run,
            fg_color="green",
            hover_color="darkgreen",
            height=40,
            width=150,
        )
        self.run_button.grid(row=0, column=0, padx=5)

        self.pause_button = ctk.CTkButton(
            self.button_frame,
            text="⏸",
            width=40,
            height=40,
            command=app.toggle_pause,
            fg_color="#3b8ed0",
            hover_color="#36719f",
        )
        self.stop_button = ctk.CTkButton(
            self.button_frame,
            text="⏹",
            width=40,
            height=40,
            command=app.stop_process,
            fg_color="#ff4a4c",
            hover_color="#933032",
        )

    def on_run(self):
        self.run_callback()


class AnalysisTab(BaseTab):
    def __init__(self, parent, app, **kwargs):
        super().__init__(
            parent,
            app,
            "Analysis",
            "Analyze directory and export to Excel",
            "Run Analysis",
            lambda: app.run_process("analysis"),
            **kwargs,
        )


class ConvertTab(BaseTab):
    def __init__(self, parent, app, **kwargs):
        super().__init__(
            parent,
            app,
            "Convert CR2",
            "Convert CR2 files to JPG",
            "Run Conversion",
            lambda: app.run_process("convert"),
            **kwargs,
        )


class OrganizeTab(BaseTab):
    def __init__(self, parent, app, **kwargs):
        super().__init__(
            parent,
            app,
            "Organize",
            "Organize files by metadata",
            "Run Organization",
            lambda: app.run_process("create"),
            **kwargs,
        )

        # Add additional options
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        self.options_frame.grid_columnconfigure((0, 1), weight=1)

        self.by_media_type_var = ctk.BooleanVar(value=True)
        self.by_media_type_check = ctk.CTkCheckBox(
            self.options_frame,
            text="Separate by Media Type (Photos/Videos)",
            variable=self.by_media_type_var,
        )
        self.by_media_type_check.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        self.structure_selector = StructureSelector(
            self.options_frame,
            available_options=["Year", "Month", "Model", "Lens"],
            initial_selection=["Year", "Month"],
        )
        self.structure_selector.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=10
        )

        ctk.CTkLabel(self.options_frame, text="On Conflict:").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.on_exist_var = ctk.StringVar(value="rename")
        self.on_exist_combo = ctk.CTkComboBox(
            self.options_frame, values=["rename", "skip"], variable=self.on_exist_var
        )
        self.on_exist_combo.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.verbose_var = ctk.BooleanVar(value=True)
        self.verbose_check = ctk.CTkCheckBox(
            self.options_frame, text="Verbose Logging", variable=self.verbose_var
        )
        self.verbose_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

    def get_options(self):
        return {
            "by_media_type": self.by_media_type_var.get(),
            "structure": self.structure_selector.get(),
            "on_exist": self.on_exist_var.get(),
            "verbose": self.verbose_var.get(),
        }
