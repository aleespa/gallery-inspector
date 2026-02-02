import os
import piexif


from loguru import logger


def fix_exif_dates(folder_path):
    logger.info(f"Fixing EXIF dates in {folder_path}")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg")):
            file_path = os.path.join(folder_path, filename)
            try:
                exif_dict = piexif.load(file_path)
                modified = False

                # Date tags to check
                date_tags = {
                    "0th": [piexif.ImageIFD.DateTime],
                    "Exif": [
                        piexif.ExifIFD.DateTimeOriginal,
                        piexif.ExifIFD.DateTimeDigitized,
                    ],
                }

                for ifd, tags in date_tags.items():
                    for tag in tags:
                        if tag in exif_dict[ifd]:
                            old_date = exif_dict[ifd][tag].decode()
                            if old_date[5:7] == "07":  # If month is July
                                new_date = (
                                    old_date[:5] + "06" + old_date[7:]
                                )  # Change to June
                                exif_dict[ifd][tag] = new_date.encode()
                                logger.info(
                                    f"{filename}: Tag {tag} changed from {old_date} to {new_date}"
                                )
                                modified = True

                if modified:
                    exif_bytes = piexif.dump(exif_dict)
                    piexif.insert(exif_bytes, file_path)

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    path_test = r"C:\Users\Alejandro\Desktop\aa"
    fix_exif_dates(path_test)
