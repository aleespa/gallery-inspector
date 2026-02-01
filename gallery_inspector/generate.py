import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal, List, Optional, Dict
from dataclasses import dataclass, field

import pandas as pd
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from loguru import logger
from pymediainfo import MediaInfo
from gallery_inspector.common import clean_excel_unsafe, rational_to_float

OrderType = Literal['Year/Month', 'Year', 'Camera', 'Lens', 'Camera/Lens']


@dataclass
class Options:
    by_media_type: bool = True
    structure: List[str] = field(default_factory=lambda: ["Year", "Month"])
    verbose: bool = True
    on_exist: Literal['rename', 'skip'] = 'rename'


import concurrent.futures

def _analyze_single_file(full_path: str, dirpath: str, f: str) -> Optional[Dict]:
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.gif'}
    try:
        size_bytes = os.path.getsize(full_path)
    except OSError:
        return None

    _, ext = os.path.splitext(f)
    ext_clean = ext.lower().lstrip('.') or 'none'
    image_info = {}
    fields_list = [
        'Model', 'LensModel', 'ISOSpeedRatings', 'FNumber',
        'ExposureTime', 'FocalLength', 'DateTime', 'DateTimeOriginal', 'Duration'
    ]
    
    media_type = 'other'
    
    if ext.lower() in {'.jpg', '.jpeg'}:
        media_type = 'image'
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
        media_type = 'video'
        try:
            media_info = MediaInfo.parse(full_path)
            creation_date = None
            for track in media_info.tracks:
                if track.track_type == "General":
                    creation_date = track.tagged_date or track.encoded_date
                    break
            
            if creation_date:
                # Try to find a date pattern
                match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", creation_date)
                if match:
                    # Format to match EXIF format: YYYY:MM:DD HH:MM:SS
                    dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                    image_info['DateTimeOriginal'] = dt.strftime("%Y:%m:%d %H:%M:%S")
                    image_info['DateTime'] = dt.strftime("%Y:%m:%d %H:%M:%S")
            
            # Extract duration
            for track in media_info.tracks:
                if track.track_type == "General":
                    image_info['Duration'] = track.duration
                    break
        except Exception:
            pass

    return {'name': f,
            'size_bytes': size_bytes,
            'directory': dirpath,
            'filetype': ext_clean,
            'media_type': media_type
            } | {field: image_info.get(field) for field in fields_list}


def generate_images_table(path: Path) -> pd.DataFrame:
    all_files = []
    files_to_process = []

    for dirpath, dir_names, filenames in os.walk(path, topdown=False):
        logger.info(f'{dirpath} analyzed')
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            files_to_process.append((full_path, dirpath, f))
            
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_analyze_single_file, fp, dp, fn) for fp, dp, fn in files_to_process]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                all_files.append(result)

    df_all = pd.DataFrame(all_files)
    fields_list = [
        'Model', 'LensModel', 'ISOSpeedRatings', 'FNumber',
        'ExposureTime', 'FocalLength', 'DateTime', 'DateTimeOriginal', 'Duration'
    ]
    
    if df_all.empty:
        return pd.DataFrame(columns=['name', 'size_bytes', 'directory', 'filetype', 'media_type', 'size (MB)'] + fields_list)

    df_all_clean = df_all.map(clean_excel_unsafe)
    df_all_clean['size (MB)'] = (df_all['size_bytes'] / 1048576).round(2)
    
    # Ensure columns exist before mapping
    for col in ['ExposureTime', 'FNumber', 'FocalLength', 'Duration']:
        if col in df_all_clean.columns:
            df_all_clean[col] = pd.to_numeric(df_all_clean[col], errors='coerce') if col == 'Duration' else df_all_clean[col].map(rational_to_float)
            
    if 'DateTime' in df_all_clean.columns:
        df_all_clean['DateTime'] = pd.to_datetime(df_all_clean['DateTime'], errors='coerce', format='%Y:%m:%d %H:%M:%S')
    if 'DateTimeOriginal' in df_all_clean.columns:
        df_all_clean['DateTimeOriginal'] = pd.to_datetime(df_all_clean['DateTimeOriginal'], errors='coerce',
                                                          format='%Y:%m:%d %H:%M:%S')

    return df_all_clean


def sanitize_folder_name(name: str) -> str | None:
    if name is None:
        return None
    else:
        return re.sub(r'[^\w\-_. ]', '_', name)


def _get_image_metadata(file: Path) -> Optional[Dict[str, Optional[str]]]:
    try:
        img = Image.open(file)
        exif_data = img._getexif()
        img.close()

        if not exif_data:
            return None

        tag_ids = {v: k for k, v in TAGS.items()}
        date_str = exif_data.get(tag_ids.get("DateTimeOriginal"))
        date_only = date_str.split(" ")[0] if date_str else None
        date = datetime.strptime(date_only, "%Y:%m:%d") if date_str else None

        model = exif_data.get(tag_ids.get('Model'))
        lens = exif_data.get(tag_ids.get('LensModel'))

        return {
            "Year": f"{date.year:04d}" if date else None,
            "Month": f"{date.month:02d}" if date else None,
            "Model": sanitize_folder_name(model) if model else None,
            "Lens": sanitize_folder_name(lens) if lens else None,
        }
    except Exception:
        raise


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

        if not date:
            return None

        return {
            "Year": f"{date.year:04d}",
            "Month": f"{date.month:02d}",
        }
    except Exception:
        raise


def _process_single_file(
        file: Path,
        output: Path,
        options: Options
) -> None:
    image_extensions = {'.jpg', '.jpeg', '.png', '.cr2', '.nef', '.tiff', '.arw'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.gif'}

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
                        target_dir = target_dir / (val if val is not None else "No Info")
        else:
            target_dir = target_dir / "No Info"
    except Exception as e:
        target_dir = target_dir / "No Info"
        if options.verbose:
            logger.warning(f"Error processing {file}: {e}")

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / file.name

    if options.on_exist == 'skip' and destination.exists():
        if options.verbose:
            logger.info(f"Skipping {file} as it already exists at {destination}")
        return
    elif options.on_exist == 'rename':
        if destination.exists():
            stem, suffix = file.stem, file.suffix
            counter = 1
            while destination.exists():
                destination = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

    shutil.copy2(file, destination)


def generated_directory(
        input_path: Path,
        output: Path,
        options: Options
) -> None:
    logger.info(f"Processing {input_path} -> {output}")
    for file in input_path.rglob('*'):
        if file.is_dir():
            continue
        _process_single_file(file, output, options)


def generated_directory_from_list(
        files: List[Path],
        output: Path,
        options: Options
) -> None:
    for file in files:
        if file.is_dir():
            continue
        _process_single_file(file, output, options)


