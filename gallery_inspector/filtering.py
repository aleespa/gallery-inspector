from dataclasses import dataclass
import os
import threading
from pathlib import Path
from typing import Optional, List, Callable
import rawpy
import imageio

from loguru import logger

from gallery_inspector.analysis import analyze_any
from gallery_inspector.generate import Options, organize_files_by_options


@dataclass
class FilterOptions:
    by_media_type: bool = True
    structure: List[str] = field(default_factory=lambda: ["Year", "Month"])
    verbose: bool = True



def filter_files(
        files: List[str | Path], output_dir: str | Path,
        output_path: str | Path,
        options: Options,
        query: FilterOptions,
        stop_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
        progress_callback: Optional[Callable[[float], None]] = None
):
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Starting filtering {output_dir}")

    all_files = [f for f in files if not f.is_dir()]
    filtered_files = []
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

        filetype, metadata = analyze_any(file)

        if True:
            filtered_files.append(file)

    organize_files_by_options(filtered_files, output_dir, options, stop_event, pause_event, progress_callback)

