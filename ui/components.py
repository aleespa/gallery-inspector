import tkinter as tk
import customtkinter as ctk

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
        
        self.btn = ctk.CTkButton(self.entry_frame, text="Browse", width=100, command=lambda: browse_callback(self.entry))
        self.btn.grid(row=0, column=1)

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
