import concurrent.futures
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd
from loguru import logger

from gallery_inspector.common import clean_excel_unsafe, rational_to_float

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".cr2", ".cr3"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".gif"}


def _get_exiftool_path() -> str:
    """Return the path to the exiftool executable.

    When the app is frozen by PyInstaller, bundled files are extracted to
    sys._MEIPASS at runtime.  Fall back to the system PATH otherwise so that
    the development workflow continues to work as before.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "exiftool.exe")
        if os.path.isfile(bundled):
            return bundled
    return "exiftool"


EXIFTOOL_BASE_ARGS = [
    _get_exiftool_path(),
    "-j",
    "-n",
    "-fast2",
    "-m",
    "-q",
    "-q",
    "-c",
    "%.6f",
    "-FileName",
    "-Directory",
    "-FileSize",
    "-DateTimeOriginal",
    "-CreateDate",
]
EXIFTOOL_IMAGE_TAG_ARGS = [
    "-Model",
    "-LensModel",
    "-LensID",
    "-FocalLength",
    "-FNumber",
    "-ISO",
    "-ExposureTime",
    "-GPSLatitude",
    "-GPSLongitude",
    "-GPSAltitude",
    "-ImageWidth",
    "-ImageHeight",
]
EXIFTOOL_VIDEO_TAG_ARGS = [
    "-ImageWidth",
    "-ImageHeight",
    "-Duration",
    "-VideoCodecID",
    "-CompressorID",
    "-VideoFrameRate",
]


def _choose_exiftool_plan(file_count: int) -> tuple[int, int]:
    max_cpu = os.cpu_count() or 4
    if file_count < 10000:
        # Preserve high parallelism for smaller scans.
        min_batch_size = 250
        workers_by_files = max(1, file_count // min_batch_size)
        workers = min(8, max_cpu, workers_by_files)
        batch_size = max(1, math.ceil(file_count / workers))
        return workers, batch_size

    if file_count < 30000:
        batch_size = 2500
        max_workers = 6
    else:
        # Reduce ExifTool process fan-out on very large scans to avoid disk thrashing.
        batch_size = 3000
        max_workers = 3

    num_batches = max(1, math.ceil(file_count / batch_size))
    workers = min(max_workers, max_cpu, num_batches)

    env_workers = os.getenv("GI_EXIFTOOL_MAX_WORKERS")
    if env_workers:
        try:
            workers = max(1, min(workers, int(env_workers)))
        except ValueError:
            pass

    env_batch_size = os.getenv("GI_EXIFTOOL_BATCH_SIZE")
    if env_batch_size:
        try:
            batch_size = max(100, int(env_batch_size))
            num_batches = max(1, math.ceil(file_count / batch_size))
            workers = min(workers, num_batches)
        except ValueError:
            pass

    return workers, batch_size


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
            "Full path": str(path),
            "size_bytes": size_bytes,
            "size_mb": size_mb,
        }
    except Exception:
        return None


def run_exiftool_batch(file_paths: List[Path], tag_profile: str = "all") -> List[Dict]:
    if not file_paths:
        return []

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8", suffix=".txt"
    ) as tmp:
        for path in file_paths:
            tmp.write(str(path) + "\n")
        tmp_path = tmp.name

    profile_tags = EXIFTOOL_IMAGE_TAG_ARGS + EXIFTOOL_VIDEO_TAG_ARGS
    if tag_profile == "image":
        profile_tags = EXIFTOOL_IMAGE_TAG_ARGS
    elif tag_profile == "video":
        profile_tags = EXIFTOOL_VIDEO_TAG_ARGS

    cmd = EXIFTOOL_BASE_ARGS + profile_tags + ["-@", tmp_path]

    try:
        process = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8"
        )
        if process.stderr:
            logger.debug(f"ExifTool stderr: {process.stderr}")

        if not process.stdout:
            return []

        return json.loads(process.stdout)
    except Exception as exc:
        logger.error(f"Error running ExifTool: {exc}")
        return []
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _map_exiftool_result(exif_item: Dict) -> tuple[Optional[str], Optional[Dict]]:
    source_file_raw = exif_item.get("SourceFile", "")
    if not source_file_raw:
        return None, None

    full_path = source_file_raw
    name = os.path.splitext(os.path.basename(source_file_raw))[0]
    filetype = os.path.splitext(source_file_raw)[1].lower()
    directory = exif_item.get("Directory") or os.path.dirname(source_file_raw)
    size_bytes = exif_item.get("FileSize")
    size_mb = round(size_bytes / 1048576, 2) if size_bytes else 0.0

    date_taken_full = exif_item.get("DateTimeOriginal") or exif_item.get("CreateDate")
    date_taken = None
    time_taken = None
    if date_taken_full:
        if " " in str(date_taken_full):
            date_taken, time_taken = str(date_taken_full).split(" ", 1)
        else:
            date_taken = str(date_taken_full)

    if filetype in IMAGE_EXTENSIONS:
        data = {
            "name": name,
            "filetype": filetype,
            "directory": directory,
            "Full path": full_path,
            "date_taken": date_taken,
            "time_taken": time_taken,
            "camera": exif_item.get("Model"),
            "lens": exif_item.get("LensModel") or exif_item.get("LensID"),
            "focal_length": exif_item.get("FocalLength"),
            "aperture": exif_item.get("FNumber") or exif_item.get("Aperture"),
            "iso": exif_item.get("ISO"),
            "shutter_speed": exif_item.get("ExposureTime"),
            "latitude": exif_item.get("GPSLatitude"),
            "longitude": exif_item.get("GPSLongitude"),
            "altitude": exif_item.get("GPSAltitude"),
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "width": exif_item.get("ImageWidth") or exif_item.get("ExifImageWidth"),
            "height": exif_item.get("ImageHeight") or exif_item.get("ExifImageHeight"),
        }

        if data["shutter_speed"] and isinstance(data["shutter_speed"], (int, float)):
            if data["shutter_speed"] < 1:
                denominator = round(1 / data["shutter_speed"])
                data["shutter_speed"] = f"1/{denominator}s"
            else:
                data["shutter_speed"] = f"{data['shutter_speed']}s"

        return "image", data

    if filetype in VIDEO_EXTENSIONS:
        duration = exif_item.get("Duration")
        if duration and isinstance(duration, (int, float)):
            duration = duration * 1000

        data = {
            "name": name,
            "filetype": filetype,
            "directory": directory,
            "Full path": full_path,
            "date_taken": date_taken,
            "time_taken": time_taken,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "width": exif_item.get("ImageWidth"),
            "height": exif_item.get("ImageHeight"),
            "duration_ms": duration,
            "codec": exif_item.get("VideoCodecID") or exif_item.get("CompressorID"),
            "frame_rate": exif_item.get("VideoFrameRate"),
        }
        return "video", data

    return "other", {
        "name": name,
        "filetype": filetype,
        "directory": directory,
        "Full path": full_path,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
    }


def _empty_df(type_name: str) -> pd.DataFrame:
    if type_name == "image":
        return pd.DataFrame(
            columns=[
                "name",
                "filetype",
                "directory",
                "Full path",
                "date_taken",
                "time_taken",
                "camera",
                "lens",
                "focal_length",
                "aperture",
                "iso",
                "shutter_speed",
                "latitude",
                "longitude",
                "altitude",
                "size_bytes",
                "size (MB)",
                "width",
                "height",
            ]
        )
    if type_name == "video":
        return pd.DataFrame(
            columns=[
                "name",
                "filetype",
                "directory",
                "Full path",
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
    return pd.DataFrame(
        columns=[
            "name",
            "filetype",
            "directory",
            "Full path",
            "size_bytes",
            "size (MB)",
        ]
    )


def _format_df(df: pd.DataFrame, type_name: str) -> pd.DataFrame:
    if df.empty:
        return _empty_df(type_name)

    # Cleaning object/string columns only is significantly faster on large datasets.
    object_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in object_columns:
        df[col] = df[col].map(clean_excel_unsafe)

    if "size_bytes" in df.columns:
        df["size (MB)"] = (df["size_bytes"] / 1048576).round(2)
    if "size_mb" in df.columns:
        df = df.drop(columns=["size_mb"], errors="ignore")

    if type_name == "image":
        for col in ["aperture", "focal_length", "altitude"]:
            if col in df.columns:
                df[col] = df[col].map(rational_to_float)

        if "date_taken" in df.columns:
            df["date_taken"] = pd.to_datetime(
                df["date_taken"], errors="coerce", format="%Y:%m:%d"
            ).dt.date

    return df


def analyze_files(
    file_paths: List[Path],
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_images = []
    all_videos = []
    all_others = []

    image_files: List[Path] = []
    video_files: List[Path] = []

    for file_path in file_paths:
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            image_files.append(file_path)
        elif suffix in VIDEO_EXTENSIONS:
            video_files.append(file_path)
        else:
            result = analyze_other(file_path)
            if result:
                all_others.append(result)

    total_files = len(image_files) + len(video_files) + len(all_others)
    if total_files == 0:
        return _empty_df("image"), _empty_df("video"), _empty_df("other")

    processed_count = len(all_others)
    if progress_callback:
        progress_callback(processed_count / total_files)

    def _run_profile_batches(file_list: List[Path], tag_profile: str) -> None:
        nonlocal processed_count

        if not file_list:
            return

        num_workers, batch_size = _choose_exiftool_plan(len(file_list))
        batches = [
            file_list[i : i + batch_size]
            for i in range(0, len(file_list), batch_size)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_batch_size = {
                executor.submit(run_exiftool_batch, batch, tag_profile): len(batch)
                for batch in batches
            }

            for future in concurrent.futures.as_completed(future_to_batch_size):
                if stop_event and stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                if pause_event:
                    while pause_event.is_set():
                        if stop_event and stop_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            break
                        threading.Event().wait(0.1)
                    if stop_event and stop_event.is_set():
                        break

                exif_results = future.result()
                batch_size_done = future_to_batch_size[future]
                for exif_item in exif_results:
                    category, result = _map_exiftool_result(exif_item)
                    if not result:
                        continue
                    if category == "image":
                        all_images.append(result)
                    elif category == "video":
                        all_videos.append(result)
                    else:
                        all_others.append(result)

                processed_count += batch_size_done
                if progress_callback:
                    progress_callback(min(processed_count / total_files, 1.0))

    _run_profile_batches(image_files, "image")
    _run_profile_batches(video_files, "video")

    return (
        _format_df(pd.DataFrame(all_images), "image"),
        _format_df(pd.DataFrame(all_videos), "video"),
        _format_df(pd.DataFrame(all_others), "other"),
    )


def analyze_directories(
    paths: List[Path],
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info(f"Starting directory analysis for: {[str(p) for p in paths]}")

    files_to_process: List[Path] = []
    for path in paths:
        for dirpath, _, filenames in os.walk(path, topdown=False):
            if stop_event and stop_event.is_set():
                logger.warning("Directory analysis stopped by user during walk.")
                return _empty_df("image"), _empty_df("video"), _empty_df("other")

            if pause_event:
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        return _empty_df("image"), _empty_df("video"), _empty_df("other")
                    threading.Event().wait(0.1)

            for filename in filenames:
                files_to_process.append(Path(dirpath) / filename)

    if not files_to_process:
        logger.warning("No files found to analyze.")
        return _empty_df("image"), _empty_df("video"), _empty_df("other")

    logger.info(
        f"Extracting metadata from {len(files_to_process):,} files with ExifTool batch mode..."
    )
    return analyze_files(
        files_to_process,
        stop_event=stop_event,
        pause_event=pause_event,
        progress_callback=progress_callback,
    )
