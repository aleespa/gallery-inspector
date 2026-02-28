import os
import re
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd
import piexif
import exifread
from loguru import logger
from PIL import Image
from pymediainfo import MediaInfo

from gallery_inspector.common import clean_excel_unsafe, rational_to_float

def _rational_to_float(value):
    if isinstance(value, tuple) and len(value) == 2 and value[1] != 0:
        return value[0] / value[1]
    return value


def _decode_if_bytes(value):
    if value is None:
        return None
    # exifread returns IFDTag objects
    if hasattr(value, "values"):
        val = value.values
        if isinstance(val, list):
            # For ASCII tags, it's usually a list of characters
            return "".join(val) if all(isinstance(c, str) for c in val) else str(val[0])
        return str(val)
    # fallback for bytes
    if isinstance(value, bytes):
        return value.decode(errors="ignore").strip("\x00")
    return str(value)


def _format_shutter(value):
    if isinstance(value, tuple) and value[1] != 0:
        num, den = value
        if num > den:
            return f"{num / den:.2f}s"
        return f"{num}/{den}s"
    return value

def analyze_image(path: Path) -> Optional[Dict]:
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        return analyze_standard_image(path)
    elif path.suffix.lower() in {".cr2", ".cr3"}:
        return analyze_raw(path)
    return None


def analyze_video(path: Path) -> Optional[Dict]:
    try:
        file_name = path.name
        name = file_name.rsplit(".", 1)[0]
        filetype = path.suffix.lower()
        directory = str(path.parent)
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        media_info = MediaInfo.parse(str(path))
        duration = None
        width = None
        height = None
        date_taken = None
        time_taken = None
        codec = None
        frame_rate = None

        for track in media_info.tracks:
            if track.track_type == "General":
                duration = track.duration  # in ms
                creation_date = track.tagged_date or track.encoded_date
                if creation_date:
                    creation_date = creation_date.replace(" UTC", "")
                    match = re.search(
                        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
                        creation_date,
                    )
                    if match:
                        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                        date_taken = dt.strftime("%Y:%m:%d")
                        time_taken = dt.strftime("%H:%M:%S")
            elif track.track_type == "Video":
                width = track.width
                height = track.height
                codec = track.format
                frame_rate = track.frame_rate

        return {
            "name": name,
            "filetype": filetype,
            "directory": directory,
            "date_taken": date_taken,
            "time_taken": time_taken,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "width": width,
            "height": height,
            "duration_ms": duration,
            "codec": codec,
            "frame_rate": frame_rate,
        }
    except Exception:
        return None


def analyze_other(path: Path) -> Optional[Dict]:
    try:
        file_name = path.name
        name = file_name.rsplit(".", 1)[0]
        filetype = path.suffix.lower()
        directory = str(path.parent)
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        return {
            "name": name,
            "filetype": filetype,
            "directory": directory,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
        }
    except Exception:
        return None

def analyze_standard_image(path: Path) -> Optional[Dict]:
    try:
        file_name = path.name
        name = file_name.rsplit(".", 1)[0]
        filetype = path.suffix.lower()
        if filetype not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError(f"Not a supported image file: {filetype}")
        directory = str(path.parent)
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        with Image.open(path) as img:
            width, height = img.size
            exif_bytes = img.info.get("exif")

        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
        else:
            try:
                exif_dict = piexif.load(str(path))
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        zeroth = exif_dict.get("0th", {})
        exif = exif_dict.get("Exif", {})

        date_taken_full = _decode_if_bytes(exif.get(piexif.ExifIFD.DateTimeOriginal))
        date_taken = None
        time_taken = None
        if date_taken_full and " " in date_taken_full:
            date_taken, time_taken = date_taken_full.split(" ", 1)
        elif date_taken_full:
            date_taken = date_taken_full

        camera = _decode_if_bytes(zeroth.get(piexif.ImageIFD.Model))
        lens = _decode_if_bytes(exif.get(piexif.ExifIFD.LensModel))
        focal_length = _rational_to_float(exif.get(piexif.ExifIFD.FocalLength))
        aperture = _rational_to_float(exif.get(piexif.ExifIFD.FNumber))
        iso = exif.get(piexif.ExifIFD.ISOSpeedRatings)
        shutter_speed = _format_shutter(exif.get(piexif.ExifIFD.ExposureTime))

        return {
            "name": name,
            "filetype": filetype,
            "directory": directory,
            "date_taken": date_taken,
            "time_taken": time_taken,
            "camera": camera,
            "lens": lens,
            "focal_length": focal_length,
            "aperture": aperture,
            "iso": iso,
            "shutter_speed": shutter_speed,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "width": width,
            "height": height,
        }

    except Exception:
        return None

def analyze_raw(path: Path) -> Optional[Dict]:
    file_name = path.name
    name = file_name.rsplit(".", 1)[0]
    filetype = path.suffix.lower()
    if filetype not in {".cr2", ".cr3"}:
        raise ValueError("Not a CR2 or CR3 file")

    directory = str(path.parent)
    size_bytes = path.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)

    camera = lens = date_taken = time_taken = iso = shutter_speed = aperture = focal_length = None
    width = height = None
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    if filetype in {".cr2"}:
        date_taken_full = _decode_if_bytes(tags.get("EXIF DateTimeOriginal"))
        if date_taken_full and " " in date_taken_full:
            date_taken, time_taken = date_taken_full.split(" ", 1)
        elif date_taken_full:
            date_taken = date_taken_full
        camera = _decode_if_bytes(tags.get("Image Model"))
        lens = _decode_if_bytes(tags.get("EXIF LensModel"))

        focal_length = _rational_to_float(tags.get("EXIF FocalLength"))
        aperture = _rational_to_float(tags.get("EXIF FNumber"))
        iso = tags.get("EXIF ISOSpeedRatings")
        shutter_speed = _decode_if_bytes(tags.get("EXIF ExposureTime"))

        # Dimensions
        width = tags.get("EXIF ExifImageWidth")
        height = tags.get("EXIF ExifImageLength")
        if width:
            width = int(str(width))
        if height:
            height = int(str(height))

    elif filetype in {".cr3"}:
        mi = MediaInfo.parse(str(path))
        for track in mi.tracks:
            if track.track_type == "General":
                camera = (getattr(track, "model", None)
                          or getattr(track, "writing_library", None)
                          or getattr(track, "encoded_library_name", None))
                lens = getattr(track, "lens_model", None)
                date_taken_full = getattr(track, "tagged_date", None) or getattr(track, "encoded_date", None)
                if date_taken_full:
                    # MediaInfo dates often look like "2026-02-14 14:00:21" or "UTC 2026-02-14 14:00:21"
                    date_taken_full = date_taken_full.replace(" UTC", "")
                    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", date_taken_full)
                    if match:
                        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                        date_taken = dt.strftime("%Y:%m:%d")
                        time_taken = dt.strftime("%H:%M:%S")
            elif track.track_type == "Video":
                width = track.width
                height = track.height
                # Exposure parameters in CR3 (ISO, etc.) are sometimes in the 'General' or 'Video' track metadata
                # but often complex to find. MediaInfo provides some.
                # Let's try to get what we can.
                # For CR3, sometimes tags like 'f_number', 'exposure_time' are available
                focal_length = getattr(track, "focal_length", None)
                aperture = getattr(track, "f_number", None)
                iso = getattr(track, "iso", None)
                shutter_speed = getattr(track, "exposure_time", None)

    def _to_float(v):
        if v is None:
            return None
        try:
            return float(str(v))
        except (ValueError, TypeError):
            return None

    return {
        "name": name,
        "filetype": filetype,
        "directory": directory,
        "date_taken": date_taken,
        "time_taken": time_taken,
        "camera": camera,
        "lens": lens,
        "focal_length": _to_float(focal_length) if focal_length is not None else None,
        "aperture": _to_float(aperture) if aperture is not None else None,
        "iso": int(str(iso)) if iso else None,
        "shutter_speed": str(shutter_speed) + "s" if shutter_speed is not None else None,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "width": int(str(width)) if width is not None else None,
        "height": int(str(height)) if height is not None else None,
    }

def analyze_directories(
    paths: List[Path],
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info(f"Starting directory analysis for: {[str(p) for p in paths]}")
    all_images = []
    all_videos = []
    all_others = []
    files_to_process = []

    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".cr2", ".cr3"}
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".gif"}

    def format_df(df, type_name):
        if df.empty:
            if type_name == "image":
                return pd.DataFrame(
                    columns=[
                        "name",
                        "filetype",
                        "directory",
                        "date_taken",
                        "time_taken",
                        "camera",
                        "lens",
                        "focal_length",
                        "aperture",
                        "iso",
                        "shutter_speed",
                        "size_bytes",
                        "size (MB)",
                        "width",
                        "height",
                    ]
                )
            elif type_name == "video":
                return pd.DataFrame(
                    columns=[
                        "name",
                        "filetype",
                        "directory",
                        "date_taken",
                        "time_taken",
                        "size_bytes",
                        "size (MB)",
                        "width",
                        "height",
                        "duration_ms",
                        "codec",
                        "frame_rate",
                    ]
                )
            else:
                return pd.DataFrame(
                    columns=["name", "filetype", "directory", "size_bytes", "size (MB)"]
                )

        df = df.map(clean_excel_unsafe)
        if "size_bytes" in df.columns:
            df["size (MB)"] = (df["size_bytes"] / 1048576).round(2)
        if "size_mb" in df.columns:
            df = df.drop(columns=["size_mb"], errors="ignore")

        if type_name == "image":
            for col in ["aperture", "focal_length"]:
                if col in df.columns:
                    df[col] = df[col].map(rational_to_float)

            if "date_taken" in df.columns:
                df["date_taken"] = pd.to_datetime(
                    df["date_taken"], errors="coerce", format="%Y:%m:%d"
                ).dt.date
        return df

    for path in paths:
        for dirpath, dir_names, filenames in os.walk(path, topdown=False):
            if stop_event and stop_event.is_set():
                logger.warning("Directory analysis stopped by user during walk.")
                return format_df(pd.DataFrame(), "image"), format_df(pd.DataFrame(), "video"), format_df(pd.DataFrame(), "other")

            if pause_event:
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        return format_df(pd.DataFrame(), "image"), format_df(pd.DataFrame(), "video"), format_df(pd.DataFrame(), "other")
                    threading.Event().wait(0.1)

            logger.debug(f"Analyzing directory: {dirpath}")
            for f in filenames:
                fp = Path(dirpath) / f
                files_to_process.append(fp)

    total_files = len(files_to_process)
    if total_files == 0:
        logger.warning("No files found to analyze.")
        return format_df(pd.DataFrame(), "image"), format_df(pd.DataFrame(), "video"), format_df(pd.DataFrame(), "other")

    def _analyze_any(fp: Path):
        ext = fp.suffix.lower()
        if ext in image_extensions:
            return "image", analyze_image(fp)
        elif ext in video_extensions:
            return "video", analyze_video(fp)
        else:
            return "other", analyze_other(fp)

    logger.info(f"Extracting metadata from {total_files} files...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_analyze_any, fp) for fp in files_to_process]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                return format_df(pd.DataFrame(), "image"), format_df(pd.DataFrame(), "video"), format_df(pd.DataFrame(), "other")

            if pause_event:
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        return format_df(pd.DataFrame(), "image"), format_df(pd.DataFrame(), "video"), format_df(pd.DataFrame(), "other")
                    threading.Event().wait(0.1)

            category, result = future.result()
            if result:
                if category == "image":
                    all_images.append(result)
                elif category == "video":
                    all_videos.append(result)
                else:
                    all_others.append(result)
            if progress_callback:
                progress_callback((i + 1) / total_files)

    df_images = pd.DataFrame(all_images)
    df_videos = pd.DataFrame(all_videos)
    df_others = pd.DataFrame(all_others)

    return format_df(df_images, "image"), format_df(df_videos, "video"), format_df(df_others, "other")
