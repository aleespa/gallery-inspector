import os
import threading
from pathlib import Path
from typing import Optional, List
import rawpy
import imageio


def cr2_to_jpg(input_dirs: List[str | Path], output_dir: str | Path, stop_event: Optional[threading.Event] = None):
    os.makedirs(output_dir, exist_ok=True)

    for input_dir in input_dirs:
        for filename in os.listdir(input_dir):
            if stop_event and stop_event.is_set():
                break
            if filename.lower().endswith('.cr2'):
                input_path = os.path.join(input_dir, filename)
                name, _ = os.path.splitext(filename)
                output_path = os.path.join(output_dir, name + '.jpg')

                with rawpy.imread(input_path) as raw:
                    rgb = raw.postprocess()
                imageio.imwrite(output_path, rgb)
                print(f"Converted: {filename} -> {name}.jpg")
