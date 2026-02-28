import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Literal, Optional

from loguru import logger

from gallery_inspector.analysis import analyze_image, analyze_video

OrderType = Literal["Year/Month", "Year", "Camera", "Lens", "Camera/Lens"]


@dataclass
class Options:
    by_media_type: bool = True
    structure: List[str] = field(default_factory=lambda: ["Year", "Month"])
    verbose: bool = True
    on_exist: Literal["rename", "skip"] = "rename"


def sanitize_folder_name(name: str) -> str | None:
    if name is None:
        return None
    else:
        return re.sub(r"[^\w\-_. ]", "_", name)


def generated_directory(
    input_paths: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = []
    for input_path in input_paths:
        for file in input_path.rglob("*"):
            if not file.is_dir():
                all_files.append(file)

    _process_files(all_files, output, options, stop_event, pause_event, progress_callback)


def generated_directory_from_list(
    files: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = [f for f in files if not f.is_dir()]
    _process_files(all_files, output, options, stop_event, pause_event, progress_callback)


def _extract_metadata(file: Path, is_image: bool, is_video: bool) -> Optional[dict]:
    if is_image:
        raw_metadata = analyze_image(file)
    elif is_video:
        raw_metadata = analyze_video(file)
    else:
        return None

    if not raw_metadata:
        return None

    year, month = None, None
    date_str = raw_metadata.get("date_taken")
    if date_str:
        try:
            parts = date_str.split(":")
            if len(parts) >= 2:
                year = parts[0]
                month = parts[1]
        except Exception:
            pass

    if is_image:
        model = raw_metadata.get("camera")
        lens = raw_metadata.get("lens")
        if year or month or model or lens:
            return {
                "Year": year,
                "Month": month,
                "Model": sanitize_folder_name(model) if model else None,
                "Lens": sanitize_folder_name(lens) if lens else None,
            }
    elif is_video:
        if year or month:
            return {
                "Year": year,
                "Month": month,
            }
            
    return None


def _process_files(
    all_files: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    total_files = len(all_files)
    if total_files == 0:
        logger.warning("No files found to organize.")
        return

    logger.info(f"Organizing {total_files} files into {output}...")
    successful_copies = 0
    excluded_files = []

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".cr2",
        ".nef",
        ".tiff",
        ".arw",
        ".cr3",
    }
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".gif"}

    for i, file in enumerate(all_files):
        if stop_event and stop_event.is_set():
            logger.warning("Organization stopped by user.")
            break

        if pause_event:
            while pause_event.is_set():
                if stop_event and stop_event.is_set():
                    break
                threading.Event().wait(0.1)

            if stop_event and stop_event.is_set():
                logger.warning("Organization stopped by user during pause.")
                break

        # Process single file logic inline
        status = "error"
        try:
            suffix = file.suffix.lower()
            is_image = suffix in image_extensions
            is_video = suffix in video_extensions

            target_dir = output

            if options.by_media_type and (is_image or is_video):
                media_folder = "Photos" if is_image else "Videos"
                target_dir = target_dir / media_folder
            else:
                target_dir = target_dir / "Other"

            metadata = _extract_metadata(file, is_image, is_video)

            if options.by_media_type and not (is_image or is_video):
                ...
            elif metadata is None:
                target_dir = target_dir / "No Info"
            else:
                if is_video and not options.structure:
                    target_dir = target_dir / "No Info"
                else:
                    for arg in options.structure:
                        val = metadata.get(arg)
                        if val is not None:
                            target_dir = target_dir / val
                        else:
                            target_dir = target_dir / "No Info"
                            break

            target_dir.mkdir(parents=True, exist_ok=True)
            destination = target_dir / file.name

            if options.on_exist == "skip" and destination.exists():
                if options.verbose:
                    logger.info(f"Skipping {file} as it already exists at {destination}")
                status = "skipped"
            else:
                if options.on_exist == "rename" and destination.exists():
                    stem, suffix = file.stem, file.suffix
                    counter = 1
                    while destination.exists():
                        destination = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                logger.info(f"Copying {file} -> {destination}")
                shutil.copy2(file, destination)
                status = "copied"

        except Exception as e:
            logger.error(f"Failed to process {file}: {e}")
            status = "error"

        if status == "copied":
            successful_copies += 1
        else:
            excluded_files.append(file)
            if status == "error":
                logger.warning(
                    f"File not copied to target directory due to error: {file}"
                )
            elif status == "skipped":
                logger.info(f"File skipped (already exists): {file}")

        if progress_callback:
            progress_callback((i + 1) / total_files)

    _final_report(total_files, successful_copies, excluded_files)


def _final_report(total: int, copied: int, excluded: List[Path]) -> None:
    num_excluded = len(excluded)
    logger.info("--- Organization Report ---")
    logger.info(f"Files in original paths: {total}")
    logger.info(f"Files copied successfully: {copied}")
    logger.info(f"Files excluded: {num_excluded}")
    logger.info("---------------------------")

    if excluded:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        error_log_path = logs_dir / f"error_{timestamp}.log"

        with open(error_log_path, "w", encoding="utf-8") as f:
            f.write(f"Report Date: {datetime.now().isoformat()}\n")
            f.write(f"Total files: {total}\n")
            f.write(f"Copied successfully: {copied}\n")
            f.write(f"Excluded files: {num_excluded}\n")
            f.write("-" * 30 + "\n")
            f.write("Excluded Files List:\n")
            for file in excluded:
                f.write(f"{file}\n")

        logger.info(f"Error log generated at: {error_log_path}")
