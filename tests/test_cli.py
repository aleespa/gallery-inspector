import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import date
import tempfile
import shutil

from main import parse_args, build_filter_query, main
from gallery_inspector.filtering import FilterOptions


class TestCLI(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.test_dir) / "input"
        self.input_dir.mkdir()
        self.output_dir = Path(self.test_dir) / "output"
        self.output_dir.mkdir()
        
        # Create a dummy file in the input directory
        self.dummy_file = self.input_dir / "file1.jpg"
        self.dummy_file.write_text("dummy content")

    def tearDown(self):
        # Remove the temporary directory after testing
        shutil.rmtree(self.test_dir)

    def test_parse_args_analyze(self):
        test_args = [
            "main.py",
            "analyze",
            "dir1", "dir2",
            "-o", "output_dir",
            "--file-types", "image", "video",
            "--extensions", ".jpg", "png",
            "--date-start", "2026-01-01",
            "--date-end", "2026-06-30",
            "--cameras", "Canon",
            "--min-aperture", "2.8",
            "--max-iso", "800",
        ]
        with patch("sys.argv", test_args):
            args = parse_args()
            self.assertEqual(args.command, "analyze")
            self.assertEqual([str(p) for p in args.inputs], ["dir1", "dir2"])
            self.assertEqual(str(args.output), "output_dir")
            self.assertEqual(args.file_types, ["image", "video"])
            self.assertEqual(args.extensions, [".jpg", "png"])
            self.assertEqual(args.date_start, date(2026, 1, 1))
            self.assertEqual(args.date_end, date(2026, 6, 30))
            self.assertEqual(args.cameras, ["Canon"])
            self.assertEqual(args.min_aperture, 2.8)
            self.assertEqual(args.max_iso, 800)

    def test_parse_args_filter(self):
        test_args = [
            "main.py",
            "filter",
            "dir1",
            "-o", "output_dir",
            "--no-by-media-type",
            "--structure", "Year", "Month", "Model",
            "--on-exist", "skip",
            "--no-verbose",
        ]
        with patch("sys.argv", test_args):
            args = parse_args()
            self.assertEqual(args.command, "filter")
            self.assertEqual([str(p) for p in args.inputs], ["dir1"])
            self.assertEqual(str(args.output), "output_dir")
            self.assertFalse(args.by_media_type)
            self.assertEqual(args.structure, ["Year", "Month", "Model"])
            self.assertEqual(args.on_exist, "skip")
            self.assertFalse(args.verbose)

    def test_build_filter_query(self):
        test_args = [
            "main.py",
            "analyze",
            "dir1",
            "-o", "output_dir",
            "--extensions", "jpg", ".png",
            "--min-iso", "100",
            "--max-iso", "400",
            "--min-shutter-speed", "1/100",
            "--max-shutter-speed", "1/500",
        ]
        with patch("sys.argv", test_args):
            args = parse_args()
            query = build_filter_query(args)
            self.assertIsInstance(query, FilterOptions)
            self.assertEqual(query.extensions, [".jpg", ".png"])  # checks the dot-addition normalization
            self.assertEqual(query.iso_range, (100, 400))
            self.assertEqual(query.shutter_speed_range, ("1/100", "1/500"))
            self.assertIsNone(query.cameras)

    @patch("main.analyze_files")
    @patch("main.export_files_table")
    @patch("main.logger")
    @patch("gallery_inspector.figures.generate_plots")
    def test_main_analyze_execution_empty_query(self, mock_generate, mock_logger, mock_export, mock_analyze):
        mock_analyze.return_value = (MagicMock(), MagicMock(), MagicMock())
        
        test_args = ["main.py", "analyze", str(self.input_dir), "-o", str(self.output_dir)]
        
        with patch("sys.argv", test_args):
            main()
            
            mock_analyze.assert_called_once()
            mock_export.assert_called_once()

    @patch("main.analyze_with_filters")
    @patch("main.export_files_table")
    @patch("main.logger")
    @patch("gallery_inspector.figures.generate_plots")
    def test_main_analyze_execution_with_filters(self, mock_generate, mock_logger, mock_export, mock_analyze_with_filters):
        mock_analyze_with_filters.return_value = (MagicMock(), MagicMock(), MagicMock())
        
        test_args = [
            "main.py",
            "analyze",
            str(self.input_dir),
            "-o", str(self.output_dir),
            "--file-types", "image",
        ]
        
        with patch("sys.argv", test_args):
            main()
            
            mock_analyze_with_filters.assert_called_once()
            mock_export.assert_called_once()

    @patch("main.filter_files")
    @patch("main.logger")
    def test_main_filter_execution(self, mock_logger, mock_filter):
        test_args = ["main.py", "filter", str(self.input_dir), "-o", str(self.output_dir)]
        
        with patch("sys.argv", test_args):
            main()
            
            mock_filter.assert_called_once()
