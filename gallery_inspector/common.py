import re
import shutil
from pathlib import Path
from typing import List, Tuple

from loguru import logger


def clean_excel_unsafe(val):
    if isinstance(val, str):
        return re.sub(r"[\x00-\x1F\x7F-\x9F]", "", val)
    return val


def rational_to_float(r):
    try:
        return float(r)
    except Exception:
        return None


def compare_directories(
    path_a: Path, path_b: Path
) -> Tuple[List[Path], List[Path], List[Path]]:
    # Create mappings: relative path -> full path
    files_a = {
        file.relative_to(path_a): file for file in path_a.rglob("*") if file.is_file()
    }
    files_b = {
        file.relative_to(path_b): file for file in path_b.rglob("*") if file.is_file()
    }

    # Determine common and unique relative paths
    common_keys = files_a.keys() & files_b.keys()
    only_in_a = [files_a[key] for key in (files_a.keys() - files_b.keys())]
    only_in_b = [files_b[key] for key in (files_b.keys() - files_a.keys())]
    common_files = [files_a[key] for key in common_keys]

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
