import os
import re
import shutil
from pathlib import Path
from typing import List

from loguru import logger


def clean_excel_unsafe(val):
    if isinstance(val, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', val)
    return val


def rational_to_float(r):
    try:
        return float(r)
    except Exception:
        return None


def compare_directories(
        path_a: Path,
        path_b: Path
) -> tuple[List, List, List]:
    # List files in both directories
    files_a = set(os.listdir(path_a))
    files_b = set(os.listdir(path_b))

    # Find common and differing files
    common_files = list(files_a & files_b)
    only_in_a = list(files_a - files_b)
    only_in_b = list(files_b - files_a)

    return common_files, only_in_a, only_in_b


def copy_from_list(list_files: list, to_directory: Path):
    to_directory.mkdir(parents=True, exist_ok=True)  # Ensure target directory exists

    for file_path in list_files:
        file_path = Path(file_path)
        if file_path.exists() and file_path.is_file():
            destination = to_directory / file_path.name
            shutil.copy2(file_path, destination)
        else:
            logger.warning(f"Skipped: {file_path} (does not exist or is not a file)")
