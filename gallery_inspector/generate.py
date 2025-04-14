import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from PIL import Image, UnidentifiedImageError, ExifTags
from PIL.ExifTags import TAGS
from loguru import logger

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


def sanitize_folder_name(name: str) -> str:
    return re.sub(r'[^\w\-_. ]', '_', name)


def generated_directory(
        input_path: Path,
        output: Path,
        organized_by: OrderType = 'Year/Month',
        verbose: bool = True
) -> None:
    image_extensions = {'.jpg', '.jpeg', '.png', '.cr2', '.nef', '.tiff', '.arw'}
    for file in input_path.rglob('*'):
        if file.suffix.lower() in image_extensions:
            try:
                img = Image.open(file)
                exif_data = img._getexif()
                img.close()

                exif = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value
                tag_ids = {v: k for k, v in TAGS.items()}

                date_str = exif_data.get(tag_ids.get("DateTimeOriginal"))
                if date_str:
                    date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    year = f"{date.year:04d}"
                    month = f"{date.month:02d}"

                match organized_by:
                    case "Year/Month":
                        target_dir = output / year / month
                    case "Year":
                        target_dir = output / year
                    case "Camera":
                        model = sanitize_folder_name(exif_data[tag_ids['Model']])
                        target_dir = output / model
                    case "Lens":
                        lens = sanitize_folder_name(exif_data[tag_ids['LensModel']])
                        target_dir = output / lens
                    case "Camera/Lens":
                        model = sanitize_folder_name(exif_data[tag_ids['Model']])
                        lens = sanitize_folder_name(exif_data[tag_ids['LensModel']])
                        target_dir = output / model / lens
                    case _:
                        continue

                target_dir.mkdir(parents=True, exist_ok=True)
                destination = target_dir / file.name

                if destination.exists():
                    stem, suffix = file.stem, file.suffix
                    counter = 1
                    while destination.exists():
                        destination = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                shutil.copy2(file, destination)
                if verbose:
                    logger.info(f"{file} moved to {destination}")

            except Exception as e:
                logger.info(f"{file} not moved: {e}")
