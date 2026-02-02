import sys
import tkinter as tk
# Mock tix for Python 3.13+ compatibility with tkinterdnd2
if not hasattr(tk, 'tix'):
    class DummyTix:
        Tk = tk.Tk
    sys.modules['tkinter.tix'] = DummyTix
    tk.tix = DummyTix

from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
from loguru import logger
import threading

from tkinterdnd2 import DND_FILES, TkinterDnD

from gallery_inspector.convertor import cr2_to_jpg
from gallery_inspector.export import export_images_table
from gallery_inspector.generate import generate_images_table, generated_directory, Options
from .tabs import AnalysisTab, ConvertTab, OrganizeTab
from .components import PathSelector, MultiPathSelector

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GalleryInspectorUI(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Gallery Inspector UI")
        self.geometry("1200x700")

        # Determine the application directory
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle (compiled with PyInstaller)
            self.app_dir = Path(sys.executable).parent
        else:
            # If the application is run as a script
            self.app_dir = Path(__file__).resolve().parents[1]

        self.log_dir = self.app_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "app_log.log"

        logger.add(str(self.log_file), rotation="10 MB", level="DEBUG")
        # Add a sink to redirect loguru logs to the UI log box
        logger.add(self._log_sink, level="INFO")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1) # Left column (Selectors)
        self.grid_columnconfigure(1, weight=2) # Right column (Tabs)
        self.grid_rowconfigure(0, weight=1)    # Main content
        self.grid_rowconfigure(2, weight=0)    # Log box (collapsible)

        # Left Column: Selectors
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_frame, text="Project Paths", font=("Arial", 18, "bold")).grid(row=0, column=0, pady=(0, 20), sticky="w")

        self.input_selector = MultiPathSelector(self.left_frame, "Input Directories:")
        self.input_selector.grid(row=1, column=0, sticky="ew", pady=10)
        self.input_selector.setup_dnd(self)

        self.output_selector = PathSelector(self.left_frame, "Output Directory:", self.browse_directory)
        self.output_selector.grid(row=2, column=0, sticky="ew", pady=10)

        # Right Column: Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="nsew")

        self.tab_organize = self.tabview.add("Organize")
        self.tab_analysis = self.tabview.add("Analysis")
        self.tab_convert = self.tabview.add("Convert CR2")

        self.analysis_view = AnalysisTab(self.tab_analysis, self)
        self.analysis_view.pack(fill="both", expand=True)

        self.convert_view = ConvertTab(self.tab_convert, self)
        self.convert_view.pack(fill="both", expand=True)

        self.organize_view = OrganizeTab(self.tab_organize, self)
        self.organize_view.pack(fill="both", expand=True)

        # Log Section
        self.log_container = ctk.CTkFrame(self)
        self.log_container.grid(row=1, column=0, columnspan=2, padx=20, sticky="ew")
        self.log_container.grid_columnconfigure(0, weight=1)

        self.log_header_frame = ctk.CTkFrame(self.log_container, fg_color="transparent")
        self.log_header_frame.grid(row=0, column=0, sticky="ew")
        self.log_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.log_header_frame, text="Logs:").grid(row=0, column=0, sticky="w")
        self.log_toggle_btn = ctk.CTkButton(self.log_header_frame, text="Show Logs", width=80, command=self.toggle_logs)
        self.log_toggle_btn.grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(self.log_container, height=150)
        self.log_textbox.configure(state="disabled")
        self.log_visible = False

        # Status Label (bottom)
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hide initially

        # Stop Button (hidden by default, shown when running)
        self.stop_button = ctk.CTkButton(
            self.left_frame, 
            text="Stop",
            fg_color="#ff4a4c",
            hover_color="#933032",
            command=self.stop_process
        )
        self.stop_event = threading.Event()

    def stop_process(self):
        if self.stop_event:
            self.stop_event.set()
            logger.warning("Stop requested by user...")
            self.status_label.configure(text="Stopping...", text_color="red")
            self.stop_button.configure(state="disabled")

    def _log_sink(self, message):
        # loguru messages can be serialized or objects, we want the formatted string
        record = message.record
        level = record["level"].name
        msg = record["message"]
        formatted_msg = f"[{level}] {msg}"
        self.after(0, lambda: self.log_message(formatted_msg))

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

    def browse_directory(self, entry):
        directory = filedialog.askdirectory()
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)
            logger.debug(f"Selected directory: {directory}")

    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))

    def run_process(self, func):
        if func == "analysis":
            btn = self.analysis_view.run_button
        elif func == "convert":
            btn = self.convert_view.run_button
        else: # create
            btn = self.organize_view.run_button

        input_paths = self.input_selector.get_paths()
        output_path = self.output_selector.get()

        if not input_paths or not output_path:
            messagebox.showerror("Error", "Please select at least one input directory and an output directory.")
            return

        btn.configure(state="disabled")
        self.stop_event.clear()
        self.stop_button.grid(row=3, column=0, pady=20, sticky="ew")
        self.stop_button.configure(state="normal")
        
        self.status_label.configure(text=f"Processing {func}...", text_color="orange")
        self.progress_bar.set(0)
        self.progress_bar.grid() # Show progress bar
        logger.info(f"START: {func.capitalize()} process initiated.")

        # Run in a separate thread to keep UI responsive
        threading.Thread(target=self.execute, args=(func, input_paths, output_path, btn), daemon=True).start()

    def execute(self, func, input_paths, output_path, btn):
        try:
            input_ps = [Path(p) for p in input_paths]
            output_p = Path(output_path)
            
            if func == "analysis":
                df = generate_images_table(input_ps, stop_event=self.stop_event, progress_callback=self.update_progress)
                if self.stop_event.is_set():
                    logger.warning("Analysis cancelled by user.")
                    self.after(0, lambda: self.finish_stopped(btn))
                    return
                export_images_table(df, output_p / "images_table.xlsx")
                msg = f"Analysis complete. Results saved to {output_p / 'images_table.xlsx'}"
            elif func == "convert":
                cr2_to_jpg(input_ps, output_p, stop_event=self.stop_event, progress_callback=self.update_progress)
                if self.stop_event.is_set():
                    logger.warning("Conversion cancelled by user.")
                    self.after(0, lambda: self.finish_stopped(btn))
                    return
                msg = f"Conversion complete. JPGs saved to {output_p}"
            elif func == "create":
                options_dict = self.organize_view.get_options()
                options = Options(**options_dict)
                generated_directory(input_ps, output_p, options, stop_event=self.stop_event, progress_callback=self.update_progress)
                if self.stop_event.is_set():
                    logger.warning("Organization cancelled by user.")
                    self.after(0, lambda: self.finish_stopped(btn))
                    return
                msg = f"Organization complete. Files organized in {output_p}"
            
            logger.info(msg)
            self.after(0, lambda: self.finish_success(msg, btn))
        except Exception as e:
            if self.stop_event.is_set():
                 self.after(0, lambda: self.finish_stopped(btn))
            else:
                logger.exception(f"Unexpected error: {e}")
                self.after(0, lambda: self.finish_error(str(e), btn))

    def finish_success(self, msg, btn):
        btn.configure(state="normal")
        self.stop_button.grid_forget()
        self.progress_bar.grid_remove()
        self.status_label.configure(text="Success!", text_color="green")
        messagebox.showinfo("Success", msg)

    def finish_error(self, err, btn):
        btn.configure(state="normal")
        self.stop_button.grid_forget()
        self.progress_bar.grid_remove()
        self.status_label.configure(text="Error occurred", text_color="red")
        messagebox.showerror("Error", f"An error occurred: {err}")

    def finish_stopped(self, btn):
        btn.configure(state="normal")
        self.stop_button.grid_forget()
        self.progress_bar.grid_remove()
        self.status_label.configure(text="Stopped", text_color="red")
        messagebox.showwarning("Stopped", "Process was stopped by user.")
