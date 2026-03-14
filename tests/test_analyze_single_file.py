from pathlib import Path
from unittest import TestCase

from gallery_inspector.analysis import analyze_files

class TestAnalyzeSingleFile(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.image_path = cls.resources_dir / "images" / "test.JPG"
        cls.image_with_location_path = cls.resources_dir / "images" / "test_with_location.jpg"
        cls.raw_cr2_path = cls.resources_dir / "images" / "test.CR2"
        cls.raw_cr3_path = cls.resources_dir / "images" / "test.CR3"

    def test_analyze_image(self):
        self.assertTrue(self.image_path.exists(), "Test image file is missing")
        df_images, df_videos, df_others = analyze_files([self.image_path])
        self.assertEqual(len(df_images), 1)
        self.assertEqual(len(df_videos), 0)
        self.assertEqual(len(df_others), 0)

        result = df_images.iloc[0]
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["filetype"], ".jpg")
        self.assertEqual(result["camera"], "Canon EOS Rebel T6")
        self.assertEqual(result["lens"], "EF-S18-55mm f/3.5-5.6 III")
        self.assertEqual(str(result["date_taken"]), "2021-05-17")
        self.assertEqual(result["time_taken"], "11:49:34")
        self.assertEqual(result["width"], 5184)
        self.assertEqual(result["height"], 3456)
        self.assertEqual(result["focal_length"], 55.0)
        self.assertEqual(result["aperture"], 5.6)
        self.assertEqual(result["iso"], 100)
        self.assertEqual(result["shutter_speed"], "1/800s")

    def test_analyze_raw_cr2(self):
        self.assertTrue(self.raw_cr2_path.exists(), "Test image file is missing")
        df_images, df_videos, df_others = analyze_files([self.raw_cr2_path])
        self.assertEqual(len(df_images), 1)
        self.assertEqual(len(df_videos), 0)
        self.assertEqual(len(df_others), 0)

        result = df_images.iloc[0]
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["filetype"], ".cr2")
        self.assertEqual(result["camera"], "Canon EOS Rebel T6")
        self.assertEqual(result["lens"], "EF-S18-55mm f/3.5-5.6 III")
        self.assertEqual(str(result["date_taken"]), "2025-04-19")
        self.assertEqual(result["time_taken"], "16:59:43")
        self.assertEqual(result["width"], 5184)
        self.assertEqual(result["height"], 3456)
        self.assertEqual(result["focal_length"], 28.0)
        self.assertEqual(result["aperture"], 4.0)
        self.assertEqual(result["iso"], 100)
        self.assertEqual(result["shutter_speed"], "1/400s")

    def test_analyze_raw_cr3(self):
        self.assertTrue(self.raw_cr3_path.exists(), "Test image file is missing")
        df_images, df_videos, df_others = analyze_files([self.raw_cr3_path])
        self.assertEqual(len(df_images), 1)
        self.assertEqual(len(df_videos), 0)
        self.assertEqual(len(df_others), 0)

        result = df_images.iloc[0]
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["filetype"], ".cr3")
        self.assertEqual(result["camera"], "Canon EOS R8")
        self.assertEqual(result["lens"], "RF24-105mm F4-7.1 IS STM")
        self.assertEqual(str(result["date_taken"]), "2026-02-14")
        self.assertEqual(result["time_taken"], "14:00:21")
        self.assertEqual(result["width"], 6000)
        self.assertEqual(result["height"], 4000)
        self.assertEqual(result["focal_length"], 24.0)
        self.assertEqual(result["aperture"], 4.0)
        self.assertEqual(result["iso"], 100)
        self.assertEqual(result["shutter_speed"], "1/2000s")

    def test_analyze_image_with_location(self):
        self.assertTrue(self.image_with_location_path.exists(), "Test image file is missing")
        df_images, _, _ = analyze_files([self.image_with_location_path])
        self.assertEqual(len(df_images), 1)

        result = df_images.iloc[0]
        self.assertAlmostEqual(result["latitude"], 51.512586, places=6)
        self.assertAlmostEqual(result["longitude"], -0.136975, places=6)
        self.assertAlmostEqual(result["altitude"], 71.16, places=2)
