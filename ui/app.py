import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
from loguru import logger
import threading

from gallery_inspector.convertor import cr2_to_jpg
from gallery_inspector.export import export_images_table
from gallery_inspector.generate import generate_images_table, generated_directory
from .tabs import AnalysisTab, ConvertTab, OrganizeTab

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GalleryInspectorUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gallery Inspector UI")
        self.geometry("700x700")

        logger.add("app_log.log", rotation="10 MB", level="INFO")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3) # Tabview
        self.grid_rowconfigure(2, weight=1) # Log box

        # Create Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")

        self.tab_analysis = self.tabview.add("Analysis")
        self.tab_convert = self.tabview.add("Convert CR2")
        self.tab_organize = self.tabview.add("Organize")

        self.analysis_view = AnalysisTab(self.tab_analysis, self)
        self.analysis_view.pack(fill="both", expand=True)

        self.convert_view = ConvertTab(self.tab_convert, self)
        self.convert_view.pack(fill="both", expand=True)

        self.organize_view = OrganizeTab(self.tab_organize, self)
        self.organize_view.pack(fill="both", expand=True)

        # Log Box
        ctk.CTkLabel(self, text="Logs:").grid(row=1, column=0, padx=20, sticky="w")
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Status Label (bottom)
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=3, column=0, pady=(0, 10))

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tk.END, f"{message}\n")
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

    def browse_directory(self, entry):
        directory = filedialog.askdirectory()
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)

    def run_process(self, func):
        if func == "analysis":
            input_path = self.analysis_view.input_selector.get()
            output_path = self.analysis_view.output_selector.get()
            btn = self.analysis_view.run_button
        elif func == "convert":
            input_path = self.convert_view.input_selector.get()
            output_path = self.convert_view.output_selector.get()
            btn = self.convert_view.run_button
        else: # create
            input_path = self.organize_view.input_selector.get()
            output_path = self.organize_view.output_selector.get()
            btn = self.organize_view.run_button

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        btn.configure(state="disabled")
        self.status_label.configure(text=f"Processing {func}...", text_color="orange")
        self.log_message(f"START: Processing {func}...")

        # Run in a separate thread to keep UI responsive
        threading.Thread(target=self.execute, args=(func, input_path, output_path, btn), daemon=True).start()

    def execute(self, func, input_path, output_path, btn):
        try:
            input_p = Path(input_path)
            output_p = Path(output_path)
            
            if func == "analysis":
                df = generate_images_table(input_p)
                export_images_table(df, output_p / "images_table.xlsx")
                msg = f"Analysis complete! Results saved to {output_p / 'images_table.xlsx'}"
            elif func == "convert":
                cr2_to_jpg(input_p, output_p)
                msg = f"Conversion complete! JPGs saved to {output_p}"
            elif func == "create":
                generated_directory(input_p, output_p, True, "Year", "Month")
                msg = f"Organization complete! Files organized in {output_p}"
            
            logger.info(msg)
            self.after(0, lambda: self.log_message(f"INFO: {msg}"))
            self.after(0, lambda: self.finish_success(msg, btn))
        except Exception as e:
            logger.error(f"Error: {e}")
            self.after(0, lambda: self.log_message(f"ERROR: {e}"))
            self.after(0, lambda: self.finish_error(str(e), btn))

    def finish_success(self, msg, btn):
        btn.configure(state="normal")
        self.status_label.configure(text="Success!", text_color="green")
        messagebox.showinfo("Success", msg)

    def finish_error(self, err, btn):
        btn.configure(state="normal")
        self.status_label.configure(text="Error occurred", text_color="red")
        messagebox.showerror("Error", f"An error occurred: {err}")
