import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from loguru import logger
import threading

from gallery_inspector.convertor import cr2_to_jpg
from gallery_inspector.export import export_images_table
from gallery_inspector.generate import generate_images_table, generated_directory

class GalleryInspectorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gallery Inspector UI")
        self.root.geometry("600x400")

        logger.add("app_log.log", rotation="10 MB", level="INFO")

        # Input Directory
        tk.Label(root, text="Input Directory:").pack(pady=(10, 0))
        self.input_entry = tk.Entry(root, width=70)
        self.input_entry.pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse_input).pack()

        # Output Directory
        tk.Label(root, text="Output Directory:").pack(pady=(10, 0))
        self.output_entry = tk.Entry(root, width=70)
        self.output_entry.pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse_output).pack()

        # Function Selection
        tk.Label(root, text="Function:").pack(pady=(10, 0))
        self.function_var = tk.StringVar(value="analysis")
        functions = [("Analysis", "analysis"), ("Convert CR2 to JPG", "convert"), ("Create Organized Directory", "create")]
        for text, val in functions:
            tk.Radiobutton(root, text=text, variable=self.function_var, value=val).pack()

        # Action Button
        self.run_button = tk.Button(root, text="Run", command=self.run_process, bg="green", fg="white", font=("Arial", 12, "bold"))
        self.run_button.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(root, text="Ready", fg="blue")
        self.status_label.pack()

    def browse_input(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, directory)

    def browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)

    def run_process(self):
        input_path = self.input_entry.get()
        output_path = self.output_entry.get()
        func = self.function_var.get()

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        self.run_button.config(state="disabled")
        self.status_label.config(text="Processing...", fg="orange")

        # Run in a separate thread to keep UI responsive
        threading.Thread(target=self.execute, args=(func, input_path, output_path), daemon=True).start()

    def execute(self, func, input_path, output_path):
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
            self.root.after(0, lambda: self.finish_success(msg))
        except Exception as e:
            logger.error(f"Error: {e}")
            self.root.after(0, lambda: self.finish_error(str(e)))

    def finish_success(self, msg):
        self.run_button.config(state="normal")
        self.status_label.config(text="Success!", fg="green")
        messagebox.showinfo("Success", msg)

    def finish_error(self, err):
        self.run_button.config(state="normal")
        self.status_label.config(text="Error occurred", fg="red")
        messagebox.showerror("Error", f"An error occurred: {err}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GalleryInspectorUI(root)
    root.mainloop()
