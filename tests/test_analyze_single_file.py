from pathlib import Path
from unittest import TestCase

from gallery_inspector.generate import analyze_raw, analyze_jpeg

class TestAnalyzeSingleFile(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.image_path = cls.resources_dir / "images" / "test.JPG"
        cls.raw_cr2_path = cls.resources_dir / "images" / "test.CR2"
        cls.raw_cr3_path = cls.resources_dir / "images" / "test.CR3"

    def test_analyze_image(self):
        self.assertTrue(self.image_path.exists(), "Test image file is missing")

        result = analyze_jpeg(self.image_path)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "test")
        self.assertEqual(result.get("filetype"), ".jpg")
        self.assertEqual(result.get("camera"), "Canon EOS Rebel T6")
        self.assertEqual(result.get("lens"), "EF-S18-55mm f/3.5-5.6 III")
        self.assertEqual(result.get("date_taken"), "2021:05:17 11:49:34")
        self.assertEqual(result.get("width"), 5184)
        self.assertEqual(result.get("height"), 3456)
        self.assertEqual(result.get("focal_length"), 55.0)
        self.assertEqual(result.get("aperture"), 5.6)
        self.assertEqual(result.get("iso"), 100)
        self.assertEqual(result.get("shutter_speed"), "1/800s")

    def test_analyze_raw_cr2(self):
        self.assertTrue(self.raw_cr2_path.exists(), "Test image file is missing")

        result = analyze_raw(self.raw_cr2_path)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "test")
        self.assertEqual(result.get("filetype"), ".cr2")
        self.assertEqual(result.get("camera"), "Canon EOS Rebel T6")
        self.assertEqual(result.get("lens"), "EF-S18-55mm f/3.5-5.6 III")
        self.assertEqual(result.get("date_taken"), "2025:04:19 16:59:43")
        self.assertEqual(result.get("width"), 5184)
        self.assertEqual(result.get("height"), 3456)
        self.assertEqual(result.get("focal_length"), 28.0)
        self.assertEqual(result.get("aperture"), 4.0)
        self.assertEqual(result.get("iso"), 100)
        self.assertEqual(result.get("shutter_speed"), "1/400")

    def test_analyze_raw_cr3(self):
        self.assertTrue(self.raw_cr3_path.exists(), "Test image file is missing")
        result = analyze_raw(self.raw_cr3_path)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "test")
        self.assertEqual(result.get("filetype"), ".cr3")
        self.assertEqual(result.get("camera"), "Canon EOS R8")
        self.assertEqual(result.get("lens"), "RF24-105mm F4-7.1 IS STM")
        self.assertEqual(result.get("date_taken"), "2026:02:14 14:00:21")
        self.assertEqual(result.get("width"), 6000)
        self.assertEqual(result.get("height"), 4000)
        self.assertEqual(result.get("focal_length"), 24.0)
        self.assertEqual(result.get("aperture"), 4.0)
        self.assertEqual(result.get("iso"), 100)
        self.assertEqual(result.get("shutter_speed"), "1/2000")
