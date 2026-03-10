from pathlib import Path
from unittest import TestCase
from gallery_inspector.analysis import analyze_directories

class TestExifToolIntegration(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.images_dir = cls.resources_dir / "images"

    def test_analyze_directories_with_exiftool(self):
        # We know these files exist from previous checks
        paths = [self.images_dir]
        df_images, df_videos, df_others = analyze_directories(paths)

        self.assertFalse(df_images.empty, "Images DataFrame should not be empty")
        
        # Check for test.JPG specifically
        test_jpg = df_images[(df_images["name"] == "test") & (df_images["filetype"] == ".jpg")]
        self.assertFalse(test_jpg.empty, "test.JPG should be in the DataFrame")
        
        # Verify some fields
        row = test_jpg.iloc[0]
        self.assertEqual(row["camera"], "Canon EOS Rebel T6")
        self.assertEqual(row["lens"], "EF-S18-55mm f/3.5-5.6 III")
        # format_df converts "2021:05:17" to date object, which stringifies as "2021-05-17"
        self.assertEqual(str(row["date_taken"]), "2021-05-17")
        self.assertEqual(row["shutter_speed"], "1/800s")
        self.assertEqual(row["iso"], 100)
        self.assertEqual(row["aperture"], 5.6)
        self.assertEqual(row["focal_length"], 55.0)

    def test_analyze_directories_raw_cr2(self):
        paths = [self.images_dir]
        df_images, df_videos, df_others = analyze_directories(paths)
        
        test_cr2 = df_images[(df_images["name"] == "test") & (df_images["filetype"] == ".cr2")]
        self.assertFalse(test_cr2.empty, "test.CR2 should be in the DataFrame")
        
        row = test_cr2.iloc[0]
        self.assertEqual(row["camera"], "Canon EOS Rebel T6")
        self.assertEqual(str(row["date_taken"]), "2025-04-19")
        self.assertEqual(row["shutter_speed"], "1/400s")

    def test_analyze_directories_raw_cr3(self):
        paths = [self.images_dir]
        df_images, df_videos, df_others = analyze_directories(paths)
        
        test_cr3 = df_images[(df_images["name"] == "test") & (df_images["filetype"] == ".cr3")]
        self.assertFalse(test_cr3.empty, "test.CR3 should be in the DataFrame")
        
        row = test_cr3.iloc[0]
        self.assertEqual(row["camera"], "Canon EOS R8")
        self.assertEqual(str(row["date_taken"]), "2026-02-14")
        self.assertEqual(row["shutter_speed"], "1/2000s")

    def test_analyze_directories_with_location(self):
        paths = [self.images_dir]
        df_images, df_videos, df_others = analyze_directories(paths)
        
        loc_img = df_images[df_images["name"] == "test_with_location"]
        self.assertFalse(loc_img.empty)
        
        row = loc_img.iloc[0]
        self.assertAlmostEqual(row["latitude"], 51.512586, places=5)
        self.assertAlmostEqual(row["longitude"], -0.136975, places=5)
        self.assertAlmostEqual(row["altitude"], 71.16, places=2)
