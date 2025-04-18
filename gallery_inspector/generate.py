import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

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


def generated_directory(
        input_path: Path,
        output: Path,
        by_media_type: bool,
        *args: str,
        verbose: bool = True
) -> None:
    image_extensions = {'.jpg', '.jpeg', '.png', '.cr2', '.nef', '.tiff', '.arw'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.gif'}

    for file in input_path.rglob('*'):
        if file.is_dir():
            continue
        suffix = file.suffix.lower()
        is_image = suffix in image_extensions
        is_video = suffix in video_extensions

        target_dir = output

        if by_media_type and (is_image or is_video):
            media_folder = "Photos" if is_image else "Videos"
            target_dir = target_dir / media_folder

        if is_image:
            try:
                img = Image.open(file)
                exif_data = img._getexif()
                img.close()

                exif = {}
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif[tag] = value
                    tag_ids = {v: k for k, v in TAGS.items()}

                    date_str = exif_data.get(tag_ids.get("DateTimeOriginal"))
                    date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S") if date_str else None

                    vars = {
                        "Year": f"{date.year:04d}" if date else None,
                        "Month": f"{date.month:02d}" if date else None,
                        "Model": sanitize_folder_name(exif_data.get(tag_ids.get('Model'))),
                        "Lens": sanitize_folder_name(exif_data.get(tag_ids.get('LensModel')))
                    }

                    for arg in args:
                        if vars.get(arg) is not None:
                            target_dir = target_dir / vars.get(arg)
                        else:
                            target_dir = target_dir / "No Info"
                else:
                    target_dir = target_dir / "No Info"
            except Exception as e:
                target_dir = target_dir / "No Info"
                target_dir.mkdir(parents=True, exist_ok=True)
                destination = target_dir / file.name
                shutil.copy2(file, destination)
                if verbose:
                    logger.warning(f"Error processing {file}: {e}. Moved to {destination}")
        elif is_video:
            try:
                media_info = MediaInfo.parse(file)
                creation_date = None
                for track in media_info.tracks:
                    if track.track_type == "General":
                        creation_date = track.tagged_date or track.encoded_date
                        break

                date = None
                if creation_date:
                    # Sample format: "UTC 2017-06-24 06:53:34"
                    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", creation_date)
                    if match:
                        date = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")

                vars = {
                    "Year": f"{date.year:04d}" if date else None,
                    "Month": f"{date.month:02d}" if date else None,
                }

                for arg in args:
                    if vars.get(arg) is not None:
                        target_dir = target_dir / vars.get(arg)
                    else:
                        target_dir = target_dir / "No Info"
                if not args:
                    target_dir = target_dir / "No Info"
            except Exception as e:
                target_dir = target_dir / "No Info"
                if verbose:
                    logger.warning(f"Error processing video {file}: {e}. Moved to {target_dir}")

        else:
            target_dir = target_dir / "No Info"

        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / file.name
        if destination.exists():
            stem, suffix = file.stem, file.suffix
            counter = 1
            while destination.exists():
                destination = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.copy2(file, destination)

