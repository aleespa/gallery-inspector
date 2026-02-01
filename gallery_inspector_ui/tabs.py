import customtkinter as ctk
from .components import PathSelector

class BaseTab(ctk.CTkFrame):
    def __init__(self, parent, app, title, description, button_text, run_callback, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.run_callback = run_callback
        
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text=description, font=("Arial", 16, "bold")).grid(row=0, column=0, pady=10)
        
        self.input_selector = PathSelector(self, "Input Directory:", self.app.browse_directory)
        self.input_selector.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.output_selector = PathSelector(self, "Output Directory:", self.app.browse_directory)
        self.output_selector.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        self.run_button = ctk.CTkButton(self, text=button_text, command=self.on_run)
        self.run_button.grid(row=3, column=0, pady=20)

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
            **kwargs
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
            **kwargs
        )
        self.input_selector.label.configure(text="Input Directory (CR2):")
        self.output_selector.label.configure(text="Output Directory (JPG):")

class OrganizeTab(BaseTab):
    def __init__(self, parent, app, **kwargs):
        super().__init__(
            parent, 
            app,
            "Organize", 
            "Organize files by Year/Month", 
            "Run Organization", 
            lambda: app.run_process("create"),
            **kwargs
        )
