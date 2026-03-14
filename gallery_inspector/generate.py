import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, List, Literal, Optional

from loguru import logger

from gallery_inspector.analysis import analyze_files

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

    organize_files_by_options(
        all_files, output, options, stop_event, pause_event, progress_callback
    )


def generated_directory_from_list(
    files: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = [f for f in files if not f.is_dir()]
    organize_files_by_options(
        all_files, output, options, stop_event, pause_event, progress_callback
    )


def _normalize_path(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _extract_year_month(date_value) -> tuple[Optional[str], Optional[str]]:
    if isinstance(date_value, date):
        return str(date_value.year), f"{date_value.month:02d}"

    if not date_value:
        return None, None

    if isinstance(date_value, str):
        try:
            if ":" in date_value:
                parts = date_value.split(":")
            elif "-" in date_value:
                parts = date_value.split("-")
            else:
                parts = []
            if len(parts) >= 2:
                return parts[0], parts[1]
        except Exception:
            return None, None

    return None, None


def _metadata_for_organization(
    filetype: str, raw_metadata: Optional[dict]
) -> Optional[dict]:
    if not raw_metadata:
        return None

    year, month = _extract_year_month(raw_metadata.get("date_taken"))

    if filetype == "image":
        model = raw_metadata.get("camera")
        lens = raw_metadata.get("lens")
        if year or month or model or lens:
            return {
                "Year": year,
                "Month": month,
                "Model": sanitize_folder_name(model) if model else None,
                "Lens": sanitize_folder_name(lens) if lens else None,
            }
        return None

    if filetype == "video":
        if year or month:
            return {
                "Year": year,
                "Month": month,
            }
        return None

    return None


def organize_files_by_options(
    files_list: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    metadata_lookup: Optional[dict[str, tuple[str, dict]]] = None,
) -> None:
    total_files = len(files_list)
    if total_files == 0:
        logger.warning("No files found to organize.")
        return

    logger.info(f"Organizing {total_files} files into {output}...")
    successful_copies = 0
    excluded_files = []
    extraction_weight = 0.0 if metadata_lookup is not None else 0.35

    if metadata_lookup is None:
        extraction_progress = None
        if progress_callback:
            extraction_progress = (
                lambda value: progress_callback(
                    min(value * extraction_weight, extraction_weight)
                )
            )

        df_images, df_videos, df_others = analyze_files(
            files_list,
            stop_event=stop_event,
            pause_event=pause_event,
            progress_callback=extraction_progress,
        )

        metadata_lookup = {}
        for filetype, df in [
            ("image", df_images),
            ("video", df_videos),
            ("other", df_others),
        ]:
            if df.empty:
                continue
            for row in df.to_dict("records"):
                full_path = row.get("Full path")
                if full_path:
                    metadata_lookup[_normalize_path(full_path)] = (filetype, row)

    for i, file in enumerate(files_list):
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
            metadata_entry = metadata_lookup.get(_normalize_path(file))
            if metadata_entry:
                filetype, raw_metadata = metadata_entry
            else:
                filetype, raw_metadata = "other", None

            is_image = filetype == "image"
            is_video = filetype == "video"

            target_dir = output

            if options.by_media_type and (is_image or is_video):
                media_folder = "Photos" if is_image else "Videos"
                target_dir = target_dir / media_folder
            else:
                target_dir = target_dir / "Other"

            metadata = _metadata_for_organization(filetype, raw_metadata)

            if metadata is None:
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
                    logger.info(
                        f"Skipping {file} as it already exists at {destination}"
                    )
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
            progress_callback(
                extraction_weight + ((i + 1) / total_files) * (1.0 - extraction_weight)
            )

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
