import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional

import pandas as pd
from loguru import logger
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from pymediainfo import MediaInfo

from gallery_inspector.common import clean_excel_unsafe, rational_to_float

OrderType = Literal["Year/Month", "Year", "Camera", "Lens", "Camera/Lens"]


@dataclass
class Options:
    by_media_type: bool = True
    structure: List[str] = field(default_factory=lambda: ["Year", "Month"])
    verbose: bool = True
    on_exist: Literal["rename", "skip"] = "rename"


import concurrent.futures


def _analyze_single_file(full_path: str, dirpath: str, f: str) -> Optional[Dict]:
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".gif"}
    try:
        size_bytes = os.path.getsize(full_path)
    except OSError:
        return None

    _, ext = os.path.splitext(f)
    ext_clean = ext.lower().lstrip(".") or "none"
    image_info = {}
    fields_list = [
        "Model",
        "LensModel",
        "ISOSpeedRatings",
        "FNumber",
        "ExposureTime",
        "FocalLength",
        "DateTime",
        "DateTimeOriginal",
        "Duration",
    ]

    media_type = "other"

    if ext.lower() in {".jpg", ".jpeg"}:
        media_type = "image"
        try:
            image = Image.open(full_path)
            exif_data = image._getexif()

            exif = {}
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value
                tag_ids = {v: k for k, v in TAGS.items()}

                for field in fields_list:
                    image_info[field] = exif_data.get(tag_ids.get(field))
        except (AttributeError, UnidentifiedImageError):
            pass

    elif ext.lower() in video_extensions:
        media_type = "video"
        try:
            media_info = MediaInfo.parse(full_path)
            creation_date = None
            for track in media_info.tracks:
                if track.track_type == "General":
                    creation_date = track.tagged_date or track.encoded_date
                    break

            if creation_date:
                # Try to find a date pattern
                match = re.search(
                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", creation_date
                )
                if match:
                    # Format to match EXIF format: YYYY:MM:DD HH:MM:SS
                    dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                    image_info["DateTimeOriginal"] = dt.strftime("%Y:%m:%d %H:%M:%S")
                    image_info["DateTime"] = dt.strftime("%Y:%m:%d %H:%M:%S")

            # Extract duration
            for track in media_info.tracks:
                if track.track_type == "General":
                    image_info["Duration"] = track.duration
                    break
        except Exception:
            pass

    return {
        "name": f,
        "size_bytes": size_bytes,
        "directory": dirpath,
        "filetype": ext_clean,
        "media_type": media_type,
    } | {field: image_info.get(field) for field in fields_list}


def generate_images_table(
    paths: List[Path],
    stop_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> pd.DataFrame:
    logger.info(f"Starting directory analysis for: {[str(p) for p in paths]}")
    all_files = []
    files_to_process = []

    for path in paths:
        for dirpath, dir_names, filenames in os.walk(path, topdown=False):
            if stop_event and stop_event.is_set():
                logger.warning("Directory analysis stopped by user during walk.")
                return pd.DataFrame()
            logger.debug(f"Analyzing directory: {dirpath}")
            for f in filenames:
                full_path = os.path.join(dirpath, f)
                files_to_process.append((full_path, dirpath, f))

    total_files = len(files_to_process)
    if total_files == 0:
        logger.warning("No files found to analyze.")
        return pd.DataFrame()

    logger.info(f"Extracting metadata from {total_files} files...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(_analyze_single_file, fp, dp, fn)
            for fp, dp, fn in files_to_process
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                return pd.DataFrame()
            result = future.result()
            if result:
                all_files.append(result)
            if progress_callback:
                progress_callback((i + 1) / total_files)

    df_all = pd.DataFrame(all_files)
    fields_list = [
        "Model",
        "LensModel",
        "ISOSpeedRatings",
        "FNumber",
        "ExposureTime",
        "FocalLength",
        "DateTime",
        "DateTimeOriginal",
        "Duration",
    ]

    if df_all.empty:
        return pd.DataFrame(
            columns=[
                "name",
                "size_bytes",
                "directory",
                "filetype",
                "media_type",
                "size (MB)",
            ]
            + fields_list
        )

    df_all_clean = df_all.map(clean_excel_unsafe)
    df_all_clean["size (MB)"] = (df_all["size_bytes"] / 1048576).round(2)

    # Ensure columns exist before mapping
    for col in ["ExposureTime", "FNumber", "FocalLength", "Duration"]:
        if col in df_all_clean.columns:
            df_all_clean[col] = (
                pd.to_numeric(df_all_clean[col], errors="coerce")
                if col == "Duration"
                else df_all_clean[col].map(rational_to_float)
            )

    if "DateTime" in df_all_clean.columns:
        df_all_clean["DateTime"] = pd.to_datetime(
            df_all_clean["DateTime"], errors="coerce", format="%Y:%m:%d %H:%M:%S"
        )
    if "DateTimeOriginal" in df_all_clean.columns:
        df_all_clean["DateTimeOriginal"] = pd.to_datetime(
            df_all_clean["DateTimeOriginal"],
            errors="coerce",
            format="%Y:%m:%d %H:%M:%S",
        )

    return df_all_clean


def sanitize_folder_name(name: str) -> str | None:
    if name is None:
        return None
    else:
        return re.sub(r"[^\w\-_. ]", "_", name)


def _get_image_metadata(file: Path) -> Optional[Dict[str, Optional[str]]]:
    try:
        img = Image.open(file)
        exif_data = img._getexif()
        img.close()

        tag_ids = {v: k for k, v in TAGS.items()}

        date = None
        if exif_data:
            date_str = exif_data.get(tag_ids.get("DateTimeOriginal"))
            if date_str:
                try:
                    date_only = date_str.split(" ")[0]
                    date = datetime.strptime(date_only, "%Y:%m:%d")
                except (ValueError, IndexError):
                    pass

        model = None
        lens = None
        if exif_data:
            model = exif_data.get(tag_ids.get("Model"))
            lens = exif_data.get(tag_ids.get("LensModel"))

        return {
            "Year": f"{date.year:04d}" if date else None,
            "Month": f"{date.month:02d}" if date else None,
            "Model": sanitize_folder_name(model) if model else None,
            "Lens": sanitize_folder_name(lens) if lens else None,
        }
    except Exception:
        return None


def _get_video_metadata(file: Path) -> Optional[Dict[str, Optional[str]]]:
    try:
        media_info = MediaInfo.parse(file)
        creation_date = None
        for track in media_info.tracks:
            if track.track_type == "General":
                creation_date = track.tagged_date or track.encoded_date
                break

        date = None
        if creation_date:
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", creation_date)
            if match:
                date = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")

        return {
            "Year": f"{date.year:04d}" if date else None,
            "Month": f"{date.month:02d}" if date else None,
        }
    except Exception:
        return None


def _process_single_file(file: Path, output: Path, options: Options) -> None:
    image_extensions = {".jpg", ".jpeg", ".png", ".cr2", ".nef", ".tiff", ".arw"}
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".gif"}

    suffix = file.suffix.lower()
    is_image = suffix in image_extensions
    is_video = suffix in video_extensions

    target_dir = output

    if options.by_media_type and (is_image or is_video):
        media_folder = "Photos" if is_image else "Videos"
        target_dir = target_dir / media_folder

    try:
        if is_image:
            metadata = _get_image_metadata(file)
            if metadata is None:
                target_dir = target_dir / "No Info"
            else:
                for arg in options.structure:
                    val = metadata.get(arg)
                    target_dir = target_dir / (val if val is not None else "No Info")
        elif is_video:
            metadata = _get_video_metadata(file)
            if metadata is None:
                target_dir = target_dir / "No Info"
            else:
                if not options.structure:
                    target_dir = target_dir / "No Info"
                else:
                    for arg in options.structure:
                        val = metadata.get(arg)
                        target_dir = target_dir / (
                            val if val is not None else "No Info"
                        )
        else:
            target_dir = target_dir / "No Info"
    except Exception as e:
        target_dir = target_dir / "No Info"
        if options.verbose:
            logger.warning(f"Error processing {file}: {e}")

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / file.name

    if options.on_exist == "skip" and destination.exists():
        if options.verbose:
            logger.info(f"Skipping {file} as it already exists at {destination}")
        return
    elif options.on_exist == "rename":
        if destination.exists():
            stem, suffix = file.stem, file.suffix
            counter = 1
            while destination.exists():
                destination = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

    logger.info(f"Copying {file} -> {destination}")
    shutil.copy2(file, destination)


def generated_directory(
    input_paths: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = []
    for input_path in input_paths:
        for file in input_path.rglob("*"):
            if not file.is_dir():
                all_files.append(file)

    total_files = len(all_files)
    if total_files == 0:
        logger.warning("No files found to organize.")
        return

    logger.info(f"Organizing {total_files} files into {output}...")
    for i, file in enumerate(all_files):
        if stop_event and stop_event.is_set():
            logger.warning("Organization stopped by user.")
            return
        _process_single_file(file, output, options)
        if progress_callback:
            progress_callback((i + 1) / total_files)


def generated_directory_from_list(
    files: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = [f for f in files if not f.is_dir()]
    total_files = len(all_files)
    if total_files == 0:
        return

    for i, file in enumerate(all_files):
        if stop_event and stop_event.is_set():
            logger.warning("Organization from list stopped by user.")
            return
        _process_single_file(file, output, options)
        if progress_callback:
            progress_callback((i + 1) / total_files)
