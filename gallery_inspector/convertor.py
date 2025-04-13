import os
import rawpy
import imageio


def cr2_to_jpg(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.cr2'):
            input_path = os.path.join(input_dir, filename)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, name + '.jpg')

            with rawpy.imread(input_path) as raw:
                rgb = raw.postprocess()
            imageio.imwrite(output_path, rgb)
            print(f"Converted: {filename} -> {name}.jpg")
