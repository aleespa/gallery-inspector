import os
from pathlib import Path

import pandas as pd
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

from gallery_inspector.common import clean_excel_unsafe, rational_to_float


def generate_images_table(path: Path) -> pd.DataFrame:
    all_files = []
    for dirpath, dir_names, filenames in os.walk(path, topdown=False):
        print(dirpath)
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
    df_all_clean['DateTimeOriginal'] = pd.to_datetime(df_all_clean['DateTimeOriginal'], errors='coerce', format='%Y:%m:%d %H:%M:%S')

    return df_all_clean
