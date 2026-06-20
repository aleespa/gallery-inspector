from pathlib import Path

from gallery_inspector.filtering import filter_files, FilterOptions
from gallery_inspector.generate import Options


def _drive_db(target: Path) -> Path:
    """Return the per-drive database path, e.g. E:\\Photos\\Other cameras -> E:\\Metadata.xlsx."""
    return Path(target.anchor) / "Metadata.xlsx"


def main():
    # Source directory to search files in (customizable)
    source = Path(r"C:\Users\Alejandro\Pictures\Pixel10-07.06.2026")

    # Destination directories for Photos and Videos (customizable)
    photo_targets = [
        Path(r"E:\Photos\Other cameras"),
        Path(r"D:\Photos\Other cameras"),
    ]
    video_targets = [
        Path(r"E:\Videos"),
        Path(r"D:\Videos"),
    ]

    # Collect all source files recursively
    files = [f for f in source.rglob("*") if f.is_file()]

    # Customizable filter extensions
    photo_extensions = [".cr3", ".jpg"]
    video_extensions = [".mp4"]

    # Options for organizing files (default: structured by Year/Month, rename on exist)
    options = Options(
        by_media_type=False,
        structure=["Year", "Month"],
        verbose=True,
        on_exist="skip",  # Customizable parameter (options: 'rename' or 'skip')
    )

    # Filter query for photos
    photo_query = FilterOptions(filetypes=["image"], extensions=photo_extensions)

    # Filter query for videos
    video_query = FilterOptions(filetypes=["video"], extensions=video_extensions)

    # Process and organize photos to all photo target directories.
    # Each drive's root Metadata.xlsx is updated incrementally with what was placed.
    for target in photo_targets:
        filter_files(
            files=files,
            output_dir=target,
            options=options,
            query=photo_query,
            database_path=_drive_db(target),
        )

    # Process and organize videos to all video target directories
    for target in video_targets:
        filter_files(
            files=files,
            output_dir=target,
            options=options,
            query=video_query,
            database_path=_drive_db(target),
        )


if __name__ == "__main__":
    main()
