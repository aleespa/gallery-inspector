import os
from pathlib import Path
from typing import List, Union, Any, Dict

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from tqdm import tqdm


def select_from_filter(
        path: Path,
        **kwargs: Union[str, int, List[Any]]
) -> List[Path]:
    filter_files = []
    fields_list = [
        'Model', 'LensModel', 'ISOSpeedRatings', 'FNumber',
        'ExposureTime', 'FocalLength', 'DateTime', 'DateTimeOriginal'
    ]

    def matches_filters(image_info: Dict[str, Any]) -> bool:
        for key, expected in kwargs.items():
            actual = image_info.get(key)
            if callable(expected):
                if not expected(actual):
                    return False
            elif isinstance(expected, list):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False
        return True

    # Gather all files first for a nice tqdm experience
    all_files = []
    for dirpath, dir_names, filenames in os.walk(path, topdown=False):
        for f in filenames:
            all_files.append(os.path.join(dirpath, f))

    # Now wrap with tqdm
    for full_path in tqdm(all_files, desc="Processing images"):
        try:
            size_bytes = os.path.getsize(full_path)
        except OSError:
            continue

        _, ext = os.path.splitext(full_path)
        ext = ext.lower().lstrip('.') or 'none'
        image_info = {}

        if ext.upper() == "JPG":
            try:
                image = Image.open(full_path)
                exif_data = image._getexif()
                if exif_data is None:
                    continue

                tag_ids = {v: k for k, v in TAGS.items()}
                for field in fields_list:
                    tag_id = tag_ids.get(field)
                    if tag_id and tag_id in exif_data:
                        image_info[field] = exif_data[tag_id]

                if matches_filters(image_info):
                    filter_files.append(Path(full_path))

            except (AttributeError, UnidentifiedImageError, KeyError, TypeError):
                continue

    return filter_files
