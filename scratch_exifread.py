import exifread

path = "c:\\Users\\Alejandro\\Projects\\gallery-inspector\\tests\\resources\\images\\test_with_location.jpg"
try:
    with open(path, "rb") as f:
        tags = exifread.process_file(f)

        for k, v in tags.items():
            if "GPS" in k:
                print(f"{k}: {v}")
except Exception as e:
    print(f"Error: {e}")
