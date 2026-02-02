import os
import threading
from pathlib import Path
from typing import Optional, List, Callable
import rawpy
import imageio


from loguru import logger


def cr2_to_jpg(input_dirs: List[str | Path], output_dir: str | Path, stop_event: Optional[threading.Event] = None, progress_callback: Optional[Callable[[float], None]] = None):
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Starting CR2 to JPG conversion in {output_dir}")

    files_to_process = []
    for input_dir in input_dirs:
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.cr2'):
                files_to_process.append((input_dir, filename))
    
    total_files = len(files_to_process)
    if total_files == 0:
        return

    for i, (input_dir, filename) in enumerate(files_to_process):
        if stop_event and stop_event.is_set():
            break
        
        input_path = os.path.join(input_dir, filename)
        name, _ = os.path.splitext(filename)
        output_path = os.path.join(output_dir, name + '.jpg')

        with rawpy.imread(input_path) as raw:
            rgb = raw.postprocess()
        imageio.imwrite(output_path, rgb)
        logger.debug(f"Converted: {filename} -> {name}.jpg")
        
        if progress_callback:
            progress_callback((i + 1) / total_files)
