from pathlib import Path
from unittest import TestCase
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gallery_inspector.analysis import analyze_video

class TestAnalyzeVideo(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.video_path = cls.resources_dir / "videos" / "test.MP4"

    def test_analyze_video(self):
        self.assertTrue(self.video_path.exists(), f"Test video file is missing at {self.video_path}")

        result = analyze_video(self.video_path)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "test")
        self.assertEqual(result.get("filetype"), ".mp4")
        
        # Extracted from previous verification
        self.assertEqual(result.get("date_taken"), "2026:01:14")
        self.assertEqual(result.get("time_taken"), "16:57:59")
        
        # Check that other basic fields are present
        self.assertIsNotNone(result.get("size_bytes"))
        self.assertIsNotNone(result.get("size_mb"))
        self.assertIsNotNone(result.get("width"))
        self.assertIsNotNone(result.get("height"))
        self.assertIsNotNone(result.get("duration_ms"))
        self.assertIsNotNone(result.get("codec"))
        self.assertIsNotNone(result.get("frame_rate"))
