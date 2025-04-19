import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal, List, Optional, Dict

import pandas as pd
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from loguru import logger
from pymediainfo import MediaInfo
from gallery_inspector.common import clean_excel_unsafe, rational_to_float

OrderType = Literal['Year/Month', 'Year', 'Camera', 'Lens', 'Camera/Lens']


def generate_images_table(path: Path) -> pd.DataFrame:
    all_files = []
    for dirpath, dir_names, filenames in os.walk(path, topdown=False):
        logger.info(f'{dirpath} analyzed')
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            try:
                size_bytes = os.path.getsize(full_path)
            except OSError:
                continue

            _, ext = os.path.splitext(f)
            ext = ext.lower().lstrip('.') or 'none'
            image_info = {}
            fields_list = [
                'Model', 'LensModel', 'ISOSpeedRatings', 'FNumber',
                'ExposureTime', 'FocalLength', 'DateTime', 'DateTimeOriginal'
            ]
            if ext.upper() == "JPG":
                try:
                    image = Image.open(full_path)
                    exif_data = image._getexif()

                    exif = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif[tag] = value
                    tag_ids = {v: k for k, v in TAGS.items()}

                    for field in fields_list:
                        image_info[field] = exif_data.get(tag_ids[field])
                except (AttributeError, UnidentifiedImageError):
                    pass

            all_files.append({'name': f,
                              'size_bytes': size_bytes,
                              'directory': dirpath,
                              'filetype': ext
                              } | {field: image_info.get(field) for field in fields_list})

    df_all = pd.DataFrame(all_files)
    df_all_clean = df_all.map(clean_excel_unsafe)
    df_all['size (MB)'] = (df_all['size_bytes'] / 1048576).round(2)
    df_all_clean['ExposureTime'] = df_all_clean['ExposureTime'].map(rational_to_float)
    df_all_clean['FNumber'] = df_all_clean['FNumber'].map(rational_to_float)
    df_all_clean['FocalLength'] = df_all_clean['FocalLength'].map(rational_to_float)
    df_all_clean['DateTime'] = pd.to_datetime(df_all_clean['DateTime'], errors='coerce', format='%Y:%m:%d %H:%M:%S')
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
        by_media_type: bool,
        args: tuple,
        verbose: bool
) -> None:
    image_extensions = {'.jpg', '.jpeg', '.png', '.cr2', '.nef', '.tiff', '.arw'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.gif'}

    suffix = file.suffix.lower()
    is_image = suffix in image_extensions
    is_video = suffix in video_extensions

    target_dir = output

    if by_media_type and (is_image or is_video):
        media_folder = "Photos" if is_image else "Videos"
        target_dir = target_dir / media_folder

    try:
        if is_image:
            metadata = _get_image_metadata(file)
            if metadata is None:
                target_dir = target_dir / "No Info"
            else:
                for arg in args:
                    val = metadata.get(arg)
                    target_dir = target_dir / (val if val is not None else "No Info")
        elif is_video:
            metadata = _get_video_metadata(file)
            if metadata is None:
                target_dir = target_dir / "No Info"
            else:
                if not args:
                    target_dir = target_dir / "No Info"
                else:
                    for arg in args:
                        val = metadata.get(arg)
                        target_dir = target_dir / (val if val is not None else "No Info")
        else:
            target_dir = target_dir / "No Info"
    except Exception as e:
        target_dir = target_dir / "No Info"
        if verbose:
            logger.warning(f"Error processing {file}: {e}")

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / file.name

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
        by_media_type: bool,
        *args: str,
        verbose: bool = True
) -> None:
    for file in input_path.rglob('*'):
        if file.is_dir():
            continue
        _process_single_file(file, output, by_media_type, args, verbose)


def generated_directory_from_list(
        files: List[Path],
        output: Path,
        by_media_type: bool,
        *args: str,
        verbose: bool = True
) -> None:
    for file in files:
        if file.is_dir():
            continue
        _process_single_file(file, output, by_media_type, args, verbose)


