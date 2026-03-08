import piexif
from PIL import Image

path = "c:\\Users\\Alejandro\\Projects\\gallery-inspector\\tests\\resources\\images\\test_with_location.jpg"
try:
    with Image.open(path) as img:
        exif_bytes = img.info.get("exif")
        exif_dict = piexif.load(exif_bytes)

        print("GPS Dict:")
        gps = exif_dict.get("GPS", {})
        for k, v in gps.items():
            print(f"{k}: {v}")
except Exception as e:
    print(f"Error: {e}")
