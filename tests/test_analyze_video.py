from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from gallery_inspector.analysis import analyze_files

class TestAnalyzeVideo(TestCase):
    def test_analyze_video(self):
        with TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "test.MP4"
            video_path.write_bytes(b"")

            mocked_exif = [
                {
                    "SourceFile": str(video_path),
                    "Directory": str(video_path.parent),
                    "FileSize": 1024,
                    "CreateDate": "2026:01:14 16:57:59",
                    "ImageWidth": 1920,
                    "ImageHeight": 1080,
                    "Duration": 3.5,
                    "VideoCodecID": "avc1",
                    "VideoFrameRate": 29.97,
                }
            ]

            with patch(
                "gallery_inspector.analysis.run_exiftool_batch",
                return_value=mocked_exif,
            ) as mocked_batch:
                df_images, df_videos, df_others = analyze_files([video_path])

            self.assertGreaterEqual(mocked_batch.call_count, 1)
            self.assertEqual(len(df_images), 0)
            self.assertEqual(len(df_others), 0)
            self.assertEqual(len(df_videos), 1)

            result = df_videos.iloc[0]
            self.assertEqual(result["name"], "test")
            self.assertEqual(result["filetype"], ".mp4")
            self.assertEqual(result["date_taken"], "2026:01:14")
            self.assertEqual(result["time_taken"], "16:57:59")
            self.assertEqual(result["size_bytes"], 1024)
            self.assertEqual(result["width"], 1920)
            self.assertEqual(result["height"], 1080)
            self.assertEqual(result["duration_ms"], 3500.0)
            self.assertEqual(result["codec"], "avc1")
            self.assertEqual(result["frame_rate"], 29.97)
