from pathlib import Path
from unittest import TestCase

from gallery_inspector.generate import _analyze_single_file


class TestAnalyzeSingleFile(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.image_path = cls.resources_dir / "images" / "test.JPG"

    def test_analyze_single_file_extracts_metadata(self):
        # Ensure test file exists
        self.assertTrue(self.image_path.exists(), "Test image file is missing")

        result = _analyze_single_file(
            str(self.image_path),
            "",
            self.image_path.name
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "test.JPG")
        self.assertEqual(result.get("Model"), "Canon EOS Rebel T6")