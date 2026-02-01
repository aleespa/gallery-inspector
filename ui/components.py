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


class StructureSelector(ctk.CTkFrame):
    def __init__(self, parent, available_options, initial_selection=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.available_options = available_options
        self.selected_options = initial_selection or []
        
        self.grid_columnconfigure(0, weight=1)
        
        self.label = ctk.CTkLabel(self, text="Folder Structure (Order: Top to Bottom)", font=("Arial", 12, "bold"))
        self.label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # Available options frame (Checkboxes)
        self.checkbox_frame = ctk.CTkFrame(self)
        self.checkbox_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.option_vars = {}
        for idx, option in enumerate(self.available_options):
            var = tk.BooleanVar(value=option in self.selected_options)
            self.option_vars[option] = var
            cb = ctk.CTkCheckBox(self.checkbox_frame, text=option, variable=var, command=lambda o=option: self._on_checkbox_toggle(o))
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
            
            ctk.CTkLabel(item_frame, text=f"{idx+1}. {option}", width=100, anchor="w").pack(side="left", padx=5)
            
            btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            btn_frame.pack(side="right")
            
            up_btn = ctk.CTkButton(btn_frame, text="▲", width=30, command=lambda i=idx: self._move_item(i, -1))
            up_btn.pack(side="left", padx=2)
            if idx == 0:
                up_btn.configure(state="disabled")
                
            down_btn = ctk.CTkButton(btn_frame, text="▼", width=30, command=lambda i=idx: self._move_item(i, 1))
            down_btn.pack(side="left", padx=2)
            if idx == len(self.selected_options) - 1:
                down_btn.configure(state="disabled")

    def _move_item(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.selected_options):
            self.selected_options[index], self.selected_options[new_index] = \
                self.selected_options[new_index], self.selected_options[index]
            self._refresh_order_view()

    def get(self):
        return self.selected_options
