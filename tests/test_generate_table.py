import unittest
from pathlib import Path
import pandas as pd
from gallery_inspector.generate import generate_images_table

class TestGenerateTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Define the path to the resources directory
        cls.resources_dir = Path(__file__).parent / "resources" / "images"
        if not cls.resources_dir.exists():
            raise unittest.SkipTest("Resources directory not found")

    def test_generate_images_table_with_resources(self):
        # Call generate_images_table
        images_df, videos_df, others_df = generate_images_table([self.resources_dir])

        # Assertions
        self.assertIsInstance(images_df, pd.DataFrame)
        self.assertIsInstance(videos_df, pd.DataFrame)
        self.assertIsInstance(others_df, pd.DataFrame)

        # We expect 3 images based on our previous 'ls': test.CR2, test.CR3, test.JPG
        self.assertEqual(len(images_df), 3)
        
        # Check if expected files are in the dataframe
        filenames = images_df["name"].tolist()
        self.assertIn("test", filenames)

        # Check for time_taken column
        self.assertIn("time_taken", images_df.columns)
        self.assertTrue(images_df["time_taken"].notna().any())
        
        # Check extensions
        extensions = [ext.lower() for ext in images_df["filetype"].tolist()]
        self.assertIn(".jpg", extensions)
        self.assertIn(".cr2", extensions)
        self.assertIn(".cr3", extensions)

        # Videos and others should be empty for now as per instructions
        self.assertEqual(len(videos_df), 0)
        self.assertEqual(len(others_df), 0)

    def test_generate_images_table_empty(self):
        # Test with an empty list of paths
        images_df, videos_df, others_df = generate_images_table([])
        self.assertEqual(len(images_df), 0)
        self.assertEqual(len(videos_df), 0)
        self.assertEqual(len(others_df), 0)
        self.assertIn("name", images_df.columns)
