import PyInstaller.__main__
import os
import customtkinter

def build():
    # Path to customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    # Entry point
    entry_point = "run_app.py"
    
    # Exclude unnecessary dependencies
    excludes = [
        "streamlit",
        "streamlit_aggrid",
        "streamlit_extras",
        "plotly",
        "matplotlib",
        "ipython",
        "nbformat",
        "tornado",
        "watchdog"
    ]
    
    # PyInstaller arguments
    args = [
        entry_point,
        "--name=GalleryInspector",
        "--onefile",
        "--windowed",  # No console
        "--clean",
        f"--add-data={ctk_path};customtkinter/",
        "--collect-all=pymediainfo",
        "--collect-all=imageio",
        "--collect-all=rawpy",
    ]
    
    for exc in excludes:
        args.append(f"--exclude-module={exc}")
        
    print(f"Starting build with args: {' '.join(args)}")
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build()
