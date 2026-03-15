import PyInstaller.__main__
import os
import customtkinter


# Path to the local ExifTool installation to bundle into the executable.
EXIFTOOL_INSTALL_DIR = r"C:\Program Files\Exiftool"


def build():
    # Path to customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)

    # Entry point
    entry_point = "main.py"

    # Exclude unnecessary dependencies
    excludes = [
        "streamlit",
        "streamlit_aggrid",
        "streamlit_extras",
        "plotly",
        "ipython",
        "nbformat",
        "tornado",
        "watchdog",
    ]

    # ExifTool paths
    exiftool_exe = os.path.join(EXIFTOOL_INSTALL_DIR, "exiftool.exe")
    exiftool_files_dir = os.path.join(EXIFTOOL_INSTALL_DIR, "exiftool_files")

    if not os.path.isfile(exiftool_exe):
        raise FileNotFoundError(
            f"exiftool.exe not found at '{exiftool_exe}'. "
            "Update EXIFTOOL_INSTALL_DIR in build_exe.py to point to your ExifTool installation."
        )

    # PyInstaller arguments
    args = [
        entry_point,
        "--name=GalleryInspector",
        "--onefile",
        "--windowed",  # No console
        "--clean",
        f"--add-data={ctk_path};customtkinter/",
        # Bundle exiftool.exe into the root of the package
        f"--add-binary={exiftool_exe};.",
        "--collect-all=pymediainfo",
        "--collect-all=imageio",
        "--collect-all=rawpy",
        "--collect-all=tkinterdnd2",
    ]

    # Bundle exiftool_files/ if present (required by the standalone exiftool.exe)
    if os.path.isdir(exiftool_files_dir):
        args.append(f"--add-data={exiftool_files_dir};exiftool_files/")

    for exc in excludes:
        args.append(f"--exclude-module={exc}")

    print(f"Starting build with args: {' '.join(args)}")
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    build()
