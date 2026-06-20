import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from gallery_inspector.database import (
    destination_row,
    read_database,
    update_database,
)


def _image_row(full_path, name=None, camera="Canon", date_taken=date(2026, 6, 7)):
    return {
        "name": name or Path(full_path).stem,
        "filetype": Path(full_path).suffix.lower(),
        "directory": str(Path(full_path).parent),
        "Full path": str(full_path),
        "date_taken": date_taken,
        "time_taken": "12:00:00",
        "camera": camera,
        "lens": "RF 50mm",
        "focal_length": 50.0,
        "aperture": 1.8,
        "iso": 100,
        "shutter_speed": "1/200s",
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "size_bytes": 1048576,
        "size (MB)": 1.0,
        "width": 6000,
        "height": 4000,
    }


class TestReadDatabase(unittest.TestCase):
    def test_missing_file_returns_empty_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            images, videos, others = read_database(db)
            self.assertTrue(images.empty)
            self.assertTrue(videos.empty)
            self.assertTrue(others.empty)
            # Columns are still canonical.
            self.assertIn("Full path", images.columns)
            self.assertIn("duration_ms", videos.columns)

    def test_date_taken_coerced_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            update_database(db, new_images=[_image_row(Path(tmp) / "a.jpg")])
            images, _, _ = read_database(db)
            self.assertEqual(len(images), 1)
            self.assertEqual(images.iloc[0]["date_taken"], date(2026, 6, 7))


class TestUpdateDatabase(unittest.TestCase):
    def test_fresh_creates_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_1.jpg")])
            self.assertTrue(db.exists())
            with pd.ExcelFile(db) as xls:
                self.assertEqual(
                    set(xls.sheet_names), {"images", "videos", "others"}
                )
            images, _, _ = read_database(db)
            self.assertEqual(len(images), 1)
            self.assertEqual(images.iloc[0]["name"], "IMG_1")

    def test_incremental_add_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_1.jpg")])
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_2.jpg")])
            images, _, _ = read_database(db)
            self.assertEqual(len(images), 2)
            self.assertEqual(
                set(images["name"]), {"IMG_1", "IMG_2"}
            )

    def test_refresh_no_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            path = Path(tmp) / "IMG_1.jpg"
            update_database(db, new_images=[_image_row(path, camera="Canon")])
            # Re-import the same path with refreshed metadata.
            update_database(db, new_images=[_image_row(path, camera="Sony")])
            images, _, _ = read_database(db)
            self.assertEqual(len(images), 1)
            self.assertEqual(images.iloc[0]["camera"], "Sony")

    def test_no_prune_keeps_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_1.jpg")])
            # A later import that does not mention IMG_1 must not remove it.
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_2.jpg")])
            images, _, _ = read_database(db)
            self.assertIn("IMG_1", set(images["name"]))

    def test_existing_db_intact_after_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "Metadata.xlsx"
            update_database(db, new_videos=[
                {
                    "name": "clip",
                    "filetype": ".mp4",
                    "directory": tmp,
                    "Full path": str(Path(tmp) / "clip.mp4"),
                    "date_taken": date(2026, 6, 7),
                    "time_taken": "10:00:00",
                    "size_bytes": 2097152,
                    "size (MB)": 2.0,
                    "width": 1920,
                    "height": 1080,
                    "duration_ms": 5000,
                    "codec": "avc1",
                    "frame_rate": 30,
                }
            ])
            update_database(db, new_images=[_image_row(Path(tmp) / "IMG_1.jpg")])
            images, videos, _ = read_database(db)
            self.assertEqual(len(images), 1)
            self.assertEqual(len(videos), 1)


class TestDestinationRow(unittest.TestCase):
    def test_rewrites_path_fields_only(self):
        src = _image_row(r"F:\DCIM\IMG_0001.CR3", name="IMG_0001")
        dest = Path(r"E:\Photos\Canon\2026\06\IMG_0001.CR3")
        row = destination_row(src, dest)
        self.assertEqual(row["Full path"], str(dest))
        self.assertEqual(row["directory"], str(dest.parent))
        self.assertEqual(row["name"], "IMG_0001")
        # EXIF preserved.
        self.assertEqual(row["camera"], src["camera"])
        self.assertEqual(row["iso"], src["iso"])
        # Source row not mutated.
        self.assertEqual(src["Full path"], r"F:\DCIM\IMG_0001.CR3")


class TestFilterFilesDatabaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources" / "images"
        if not cls.resources_dir.exists():
            raise unittest.SkipTest("Resources directory not found")

    def test_import_creates_and_updates_database(self):
        from gallery_inspector.filtering import FilterOptions, filter_files
        from gallery_inspector.generate import Options

        with tempfile.TemporaryDirectory() as tmp:
            drive = Path(tmp)
            db = drive / "Metadata.xlsx"
            options = Options(
                by_media_type=False, structure=["Year", "Month"], on_exist="skip"
            )
            query = FilterOptions(filetypes=["image"])
            files = [f for f in self.resources_dir.rglob("*") if f.is_file()]

            organized = filter_files(
                files=files,
                output_dir=drive / "Photos",
                options=options,
                query=query,
                database_path=db,
            )
            self.assertTrue(db.exists())
            self.assertGreater(len(organized["image"]), 0)

            images, _, _ = read_database(db)
            self.assertEqual(len(images), len(organized["image"]))
            # Full path points into the destination, not the source resources dir.
            for path in images["Full path"]:
                self.assertTrue(str(path).startswith(str(drive / "Photos")))

            # Re-importing the same files must not create duplicates (skip + refresh).
            count_before = len(images)
            filter_files(
                files=files,
                output_dir=drive / "Photos",
                options=options,
                query=query,
                database_path=db,
            )
            images_after, _, _ = read_database(db)
            self.assertEqual(len(images_after), count_before)


if __name__ == "__main__":
    unittest.main()
