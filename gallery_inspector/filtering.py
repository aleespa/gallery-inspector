import os
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, List, Callable, Tuple

from loguru import logger

from gallery_inspector.analysis import analyze_files
from gallery_inspector.generate import Options, organize_files_by_options


@dataclass
class FilterOptions:
    filetypes: Optional[List[str]] = None  # "image", "video", "other"
    extensions: Optional[List[str]] = None
    date_range: Optional[Tuple[Optional[date], Optional[date]]] = None
    cameras: Optional[List[str]] = None
    lenses: Optional[List[str]] = None
    aperture_range: Optional[Tuple[Optional[float], Optional[float]]] = None
    iso_range: Optional[Tuple[Optional[int], Optional[int]]] = None
    shutter_speed_range: Optional[Tuple[Optional[str], Optional[str]]] = None


def _parse_shutter_speed(s: str) -> float:
    if not s:
        return 0.0
    s = s.lower().replace("s", "")
    if "/" in s:
        try:
            num, den = s.split("/")
            return float(num) / float(den)
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalize_path(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _parse_date_value(value) -> Optional[date]:
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if " " in candidate:
            candidate = candidate.split(" ", 1)[0]

        try:
            if ":" in candidate:
                return date(*map(int, candidate.split(":")))
            if "-" in candidate:
                return date(*map(int, candidate.split("-")))
        except (ValueError, TypeError):
            return None

    return None


def filter_files(
    files: List[str | Path],
    output_dir: str | Path,
    options: Options,
    query: FilterOptions,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
):
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Starting filtering {output_dir}")

    all_files = [Path(f) for f in files if not Path(f).is_dir()]
    filtered_files = []
    total_files = len(all_files)

    extraction_weight = 0.35
    extraction_progress = None
    if progress_callback:
        extraction_progress = (
            lambda value: progress_callback(min(value * extraction_weight, extraction_weight))
        )

    df_images, df_videos, df_others = analyze_files(
        all_files,
        stop_event=stop_event,
        pause_event=pause_event,
        progress_callback=extraction_progress,
    )

    metadata_lookup: dict[str, tuple[str, dict]] = {}
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

    if stop_event and stop_event.is_set():
        logger.warning("Filtering stopped by user during metadata extraction.")
        return

    normalized_extensions = (
        [e.lower() for e in query.extensions] if query.extensions else None
    )

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

        metadata_entry = metadata_lookup.get(_normalize_path(file))
        if metadata_entry:
            filetype, metadata = metadata_entry
        else:
            filetype, metadata = "other", None

        if not metadata:
            if progress_callback:
                progress_callback(
                    extraction_weight + ((i + 1) / total_files) * (1.0 - extraction_weight)
                )
            continue

        # Filter by filetype
        if query.filetypes:
            if filetype not in query.filetypes:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # If photo options are present, only allow images
        has_photo_options = (
            query.cameras
            or query.lenses
            or query.aperture_range
            or query.iso_range
            or query.shutter_speed_range
        )

        if has_photo_options and filetype != "image":
            if progress_callback:
                progress_callback(
                    extraction_weight + ((i + 1) / total_files) * (1.0 - extraction_weight)
                )
            continue

        # Filter by extensions
        if normalized_extensions:
            if file.suffix.lower() not in normalized_extensions:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by date taken / modified
        if query.date_range:
            start_date, end_date = query.date_range
            dt = _parse_date_value(metadata.get("date_taken"))

            if dt is None:
                # Fallback to modification date
                try:
                    mtime = file.stat().st_mtime
                    dt = date.fromtimestamp(mtime)
                except Exception:
                    pass

            if dt:
                if start_date and dt < start_date:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
                if end_date and dt > end_date:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
            else:
                # If still no date, skip
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by camera
        if query.cameras:
            camera = metadata.get("camera")
            if not camera or camera not in query.cameras:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by lens
        if query.lenses:
            lens = metadata.get("lens")
            if not lens or lens not in query.lenses:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by aperture
        if query.aperture_range:
            min_ap, max_ap = query.aperture_range
            aperture = metadata.get("aperture")
            if aperture is not None:
                if min_ap is not None and aperture < min_ap:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
                if max_ap is not None and aperture > max_ap:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
            else:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by ISO
        if query.iso_range:
            min_iso, max_iso = query.iso_range
            iso = metadata.get("iso")
            if iso is not None:
                if min_iso is not None and iso < min_iso:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
                if max_iso is not None and iso > max_iso:
                    if progress_callback:
                        progress_callback(
                            extraction_weight
                            + ((i + 1) / total_files) * (1.0 - extraction_weight)
                        )
                    continue
            else:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        # Filter by shutter speed
        if query.shutter_speed_range:
            min_ss_str, max_ss_str = query.shutter_speed_range
            ss_str = metadata.get("shutter_speed")
            if ss_str:
                ss_val = _parse_shutter_speed(ss_str)
                if min_ss_str:
                    min_ss = _parse_shutter_speed(min_ss_str)
                    if ss_val < min_ss:
                        if progress_callback:
                            progress_callback(
                                extraction_weight
                                + ((i + 1) / total_files) * (1.0 - extraction_weight)
                            )
                        continue
                if max_ss_str:
                    max_ss = _parse_shutter_speed(max_ss_str)
                    if ss_val > max_ss:
                        if progress_callback:
                            progress_callback(
                                extraction_weight
                                + ((i + 1) / total_files) * (1.0 - extraction_weight)
                            )
                        continue
            else:
                if progress_callback:
                    progress_callback(
                        extraction_weight
                        + ((i + 1) / total_files) * (1.0 - extraction_weight)
                    )
                continue

        filtered_files.append(file)
        if progress_callback:
            progress_callback(
                extraction_weight + ((i + 1) / total_files) * (1.0 - extraction_weight)
            )

    organize_files_by_options(
        filtered_files,
        output_dir,
        options,
        stop_event,
        pause_event,
        progress_callback,
        metadata_lookup=metadata_lookup,
    )
