import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
import piexif
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional
import concurrent.futures
import pandas as pd
from loguru import logger
import exifread
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
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return analyze_jpeg(path)
    elif path.suffix.lower() in {".cr2", ".cr3"}:
        return analyze_raw(path)
    return None


def analyze_jpeg(path: Path) -> Optional[Dict]:
    try:
        file_name = path.name
        name = file_name.rsplit(".", 1)[0]
        filetype = path.suffix.lower()
        if filetype not in {".jpg", ".jpeg"}:
            raise ValueError("Not a JPEG file")
        directory = str(path.parent)
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        with Image.open(path) as img:
            width, height = img.size

        exif_dict = piexif.load(str(path))
        zeroth = exif_dict["0th"]
        exif = exif_dict["Exif"]

        date_taken = _decode_if_bytes(exif.get(piexif.ExifIFD.DateTimeOriginal))
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

    camera = lens = date_taken = iso = shutter_speed = aperture = focal_length = None
    width = height = None
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    if filetype in {".cr2"}:
        date_taken = _decode_if_bytes(tags.get("EXIF DateTimeOriginal"))
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
                date_taken = getattr(track, "tagged_date", None) or getattr(track, "encoded_date", None)
                iso = getattr(track, "ISO", None)
                aperture = getattr(track, "FNumber", None)
                shutter_speed = getattr(track, "ExposureTime", None)
                focal_length = getattr(track, "FocalLength", None)
            elif track.track_type == "Video":
                if width is None or (track.width and track.width > width):
                    width = track.width
                if height is None or (track.height and track.height > height):
                    height = track.height

        # Fallback for camera, lens, date, and other EXIF tags using raw byte search and exifread
        try:
            with open(path, 'rb') as f:
                # CR3 files often have metadata near the beginning
                head = f.read(100000)
                
                # Try to use exifread by finding TIFF headers
                # CR3 is ISO BMFF, and it contains multiple TIFF-based metadata blocks
                for header in [b"II\x2a\x00", b"MM\x00\x2a"]:
                    idx = head.find(header)
                    while idx != -1:
                        import io
                        f_tiff = io.BytesIO(head[idx:])
                        tags = exifread.process_file(f_tiff, details=False)
                        if tags:
                            if not camera:
                                camera = _decode_if_bytes(tags.get("Image Model"))
                            if not lens:
                                lens = _decode_if_bytes(tags.get("EXIF LensModel") or tags.get("Image LensModel"))
                            if not date_taken:
                                date_taken = _decode_if_bytes(tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime"))
                            
                            if not iso:
                                iso = tags.get("EXIF ISOSpeedRatings") or tags.get("Image ISOSpeedRatings")
                            # Aperture: prefer sensible numeric value
                            cand_ap = _rational_to_float(tags.get("EXIF FNumber") or tags.get("Image FNumber"))
                            if cand_ap:
                                aperture = cand_ap
                            # Shutter speed: prefer a clean fractional like '1/2000'
                            exp_val = tags.get("EXIF ExposureTime") or tags.get("Image ExposureTime")
                            if exp_val:
                                cand_ss = str(exp_val)
                                if (not shutter_speed) or (not str(shutter_speed).startswith('1/') and cand_ss.startswith('1/')):
                                    shutter_speed = cand_ss
                            # Focal length
                            cand_fl = _rational_to_float(tags.get("EXIF FocalLength") or tags.get("Image FocalLength"))
                            if cand_fl:
                                focal_length = cand_fl
                                
                            if not width:
                                width = tags.get("EXIF ExifImageWidth") or tags.get("Image ImageWidth")
                            if not height:
                                height = tags.get("EXIF ExifImageLength") or tags.get("Image ImageLength")
                        
                        # Continue scanning all possible TIFF blocks; some early blocks contain placeholder values
                        idx = head.find(header, idx + 1)
                    # Do not break early; later blocks may contain the real EXIF values

                # Additional fallback for strings if still missing
                if not camera:
                    idx = head.find(b'Canon EOS ')
                    if idx != -1:
                        cam_bytes = head[idx:]
                        null_idx = cam_bytes.find(b'\x00')
                        if null_idx != -1:
                            cam_str = cam_bytes[:null_idx].decode('utf-8', errors='ignore')
                            if cam_str.startswith("Canon "):
                                camera = cam_str[6:]
                            else:
                                camera = cam_str

                if not lens:
                    # Look for common lens patterns or specific LensModel tag
                    # Many Canon lenses start with EF or RF
                    for pattern in [b'RF', b'EF']:
                        idx = head.find(pattern)
                        if idx != -1:
                            lens_bytes = head[idx:]
                            null_idx = lens_bytes.find(b'\x00')
                            if null_idx != -1:
                                lens = lens_bytes[:null_idx].decode('utf-8', errors='ignore')
                                break

                if not date_taken:
                    # Search for date pattern YYYY:MM:DD HH:MM:SS
                    m = re.search(rb'(\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2})', head)
                    if m:
                        date_taken = m.group(1).decode('utf-8')
        except Exception:
            pass

        # Normalize date format
        if date_taken:
            date_taken = str(date_taken)
            date_taken = re.sub(r" UTC$", "", date_taken)
            # Try YYYY-MM-DD HH:MM:SS
            m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", date_taken)
            if m:
                dt_obj = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                date_taken = dt_obj.strftime("%Y:%m:%d %H:%M:%S")
            else:
                # Try YYYY:MM:DD HH:MM:SS (already in correct format)
                m2 = re.search(r"(\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2})", date_taken)
                if m2:
                    date_taken = m2.group(1)

        # Normalize shutter speed (remove trailing 's')
        if shutter_speed:
            shutter_speed = str(shutter_speed).rstrip('s')

        # Normalize ISO
        if iso:
            try:
                iso = int(str(iso))
            except Exception:
                iso = None

        # Ensure aperture/focal_length are floats when possible
        if isinstance(aperture, str):
            try:
                aperture = float(aperture)
            except Exception:
                pass
        if isinstance(focal_length, str):
            try:
                focal_length = float(focal_length)
            except Exception:
                pass
        # Convert Ratio-like objects to float using helper
        if focal_length is not None and not isinstance(focal_length, (int, float)):
            try:
                focal_length = _rational_to_float(focal_length)
            except Exception:
                pass

    # Final normalization just before returning
    def _to_float(v):
        if isinstance(v, (int, float)):
            return float(v)
        # exifread Tag may wrap the underlying Ratio/number in .values
        if hasattr(v, 'values'):
            try:
                return float(v.values[0])
            except Exception:
                pass
        try:
            return _rational_to_float(v)
        except Exception:
            try:
                return float(str(v))
            except Exception:
                return v

    return {
        "name": name,
        "filetype": filetype,
        "directory": directory,
        "date_taken": date_taken,
        "camera": camera,
        "lens": lens,
        "focal_length": _to_float(focal_length) if focal_length is not None else None,
        "aperture": _to_float(aperture) if aperture is not None else None,
        "iso": int(str(iso)) if iso else None,
        "shutter_speed": str(shutter_speed) if shutter_speed is not None else None,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "width": int(str(width)) if width is not None else None,
        "height": int(str(height)) if height is not None else None,
    }


def _analyze_video(path: Path) -> Optional[Dict]:
    return {}




def generate_images_table(
    paths: List[Path],
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info(f"Starting directory analysis for: {[str(p) for p in paths]}")
    all_files = []
    files_to_process = []

    image_extensions = {".jpg", ".jpeg", ".cr2", ".cr3"}

    for path in paths:
        for dirpath, dir_names, filenames in os.walk(path, topdown=False):
            if stop_event and stop_event.is_set():
                logger.warning("Directory analysis stopped by user during walk.")
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

            if pause_event:
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
                    threading.Event().wait(0.1)

            logger.debug(f"Analyzing directory: {dirpath}")
            for f in filenames:
                fp = Path(dirpath) / f
                if fp.suffix.lower() in image_extensions:
                    files_to_process.append(fp)

    total_files = len(files_to_process)
    if total_files == 0:
        logger.warning("No files found to analyze.")
        empty_df = pd.DataFrame(
            columns=[
                "name",
                "filetype",
                "directory",
                "date_taken",
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
        return empty_df, pd.DataFrame(), pd.DataFrame()

    logger.info(f"Extracting metadata from {total_files} files...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(analyze_image, fp)
            for fp in files_to_process
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

            if pause_event:
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
                    threading.Event().wait(0.1)

            result = future.result()
            if result:
                all_files.append(result)
            if progress_callback:
                progress_callback((i + 1) / total_files)

    df_images = pd.DataFrame(all_files)

    if df_images.empty:
        df_images = pd.DataFrame(
            columns=[
                "name",
                "filetype",
                "directory",
                "date_taken",
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
    else:
        df_images = df_images.map(clean_excel_unsafe)
        if "size_bytes" in df_images.columns:
            df_images["size (MB)"] = (df_images["size_bytes"] / 1048576).round(2)
        # Remove duplicate size column if present
        if "size_mb" in df_images.columns:
            df_images = df_images.drop(columns=["size_mb"], errors="ignore")

        # Ensure columns exist before mapping (do NOT convert shutter_speed strings)
        for col in ["aperture", "focal_length"]:
            if col in df_images.columns:
                df_images[col] = df_images[col].map(rational_to_float)

        if "date_taken" in df_images.columns:
            df_images["date_taken"] = pd.to_datetime(
                df_images["date_taken"], errors="coerce", format="%Y:%m:%d %H:%M:%S"
            )

    return df_images, pd.DataFrame(), pd.DataFrame()


def sanitize_folder_name(name: str) -> str | None:
    if name is None:
        return None
    else:
        return re.sub(r"[^\w\-_. ]", "_", name)


def _get_image_metadata(file: Path) -> Optional[Dict[str, Optional[str]]]:
    date = None
    model = None
    lens = None
    try:
        # Try PIL first
        try:
            img = Image.open(file)
            exif_data = img._getexif()
            img.close()

            tag_ids = {v: k for k, v in TAGS.items()}

            if exif_data:
                date_str = exif_data.get(tag_ids.get("DateTimeOriginal"))
                if date_str:
                    try:
                        date_only = date_str.split(" ")[0]
                        date = datetime.strptime(date_only, "%Y:%m:%d")
                    except (ValueError, IndexError):
                        pass

                model = exif_data.get(tag_ids.get("Model"))
                lens = exif_data.get(tag_ids.get("LensModel"))
        except Exception:
            # PIL might fail to open or it might not have exif
            pass

        # If PIL failed to get critical info and it's a .cr3, try MediaInfo
        if (not date or not model) and file.suffix.lower() in {".cr2", ".cr3"}:
            try:
                media_info = MediaInfo.parse(file)
                for track in media_info.tracks:
                    if track.track_type == "General":
                        if not date:
                            creation_date = track.tagged_date or track.encoded_date
                            if creation_date:
                                # Remove UTC if present
                                creation_date = creation_date.replace(" UTC", "")
                                match = re.search(
                                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
                                    creation_date,
                                )
                                if match:
                                    date = datetime.strptime(
                                        match.group(1), "%Y-%m-%d %H:%M:%S"
                                    )
                        if not model:
                            model = track.model
                        if not lens:
                            lens = track.lens_model
                        break
            except Exception as e:
                logger.debug(f"MediaInfo error for {file}: {e}")

        if date or model or lens:
            return {
                "Year": f"{date.year:04d}" if date else None,
                "Month": f"{date.month:02d}" if date else None,
                "Model": sanitize_folder_name(model) if model else None,
                "Lens": sanitize_folder_name(lens) if lens else None,
            }
        return None
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


def _process_single_file(
    file: Path, output: Path, options: Options
) -> Literal["copied", "skipped", "error"]:
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
            logger.warning(f"Error extracting metadata from {file}: {e}")

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / file.name

        if options.on_exist == "skip" and destination.exists():
            if options.verbose:
                logger.info(f"Skipping {file} as it already exists at {destination}")
            return "skipped"
        elif options.on_exist == "rename":
            if destination.exists():
                stem, suffix = file.stem, file.suffix
                counter = 1
                while destination.exists():
                    destination = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

        logger.info(f"Copying {file} -> {destination}")
        shutil.copy2(file, destination)
        return "copied"
    except Exception as e:
        logger.error(f"Failed to copy {file} to {target_dir}: {e}")
        return "error"


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

    total_files = len(all_files)
    if total_files == 0:
        logger.warning("No files found to organize.")
        return

    logger.info(f"Organizing {total_files} files into {output}...")
    successful_copies = 0
    excluded_files = []

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

        status = _process_single_file(file, output, options)
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


def generated_directory_from_list(
    files: List[Path],
    output: Path,
    options: Options,
    stop_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    all_files = [f for f in files if not f.is_dir()]
    total_files = len(all_files)
    if total_files == 0:
        return

    successful_copies = 0
    excluded_files = []

    for i, file in enumerate(all_files):
        if stop_event and stop_event.is_set():
            logger.warning("Organization from list stopped by user.")
            break

        if pause_event:
            while pause_event.is_set():
                if stop_event and stop_event.is_set():
                    break
                threading.Event().wait(0.1)

            if stop_event and stop_event.is_set():
                logger.warning("Organization from list stopped by user during pause.")
                break

        status = _process_single_file(file, output, options)
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
