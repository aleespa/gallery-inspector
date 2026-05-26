from pathlib import Path

from gallery_inspector.filtering import filter_files, FilterOptions
from gallery_inspector.generate import Options


def main():
    # Source directory to search files in (customizable)
    source = Path(r"F:\\")
    
    # Destination directories for Photos and Videos (customizable)
    photo_targets = [
        Path(r"E:\Photos\Canon"),
        Path(r"D:\Photos\Canon"),
    ]
    video_targets = [
        Path(r"E:\Videos"),
        Path(r"D:\Videos"),
    ]
    
    # Collect all source files recursively
    files = [f for f in source.rglob("*") if f.is_file()]
    
    # Customizable filter extensions
    photo_extensions = [".cr3", ".jpeg"]
    video_extensions = [".mp4"]
    
    # Options for organizing files (default: structured by Year/Month, rename on exist)
    options = Options(
        by_media_type=False,
        structure=["Year", "Month"],
        verbose=True,
        on_exist="skip"  # Customizable parameter (options: 'rename' or 'skip')
    )
    
    # Filter query for photos
    photo_query = FilterOptions(
        filetypes=["image"],
        extensions=photo_extensions
    )
    
    # Filter query for videos
    video_query = FilterOptions(
        filetypes=["video"],
        extensions=video_extensions
    )
    
    # Process and organize photos to all photo target directories
    for target in photo_targets:
        filter_files(
            files=files,
            output_dir=target,
            options=options,
            query=photo_query
        )
        
    # Process and organize videos to all video target directories
    for target in video_targets:
        filter_files(
            files=files,
            output_dir=target,
            options=options,
            query=video_query
        )


if __name__ == "__main__":
    main()
