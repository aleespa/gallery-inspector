import unittest
import pandas as pd
from pathlib import Path
from gallery_inspector.export import export_files_table
from gallery_inspector.generate import analyze_directories

class TestExportTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Define the path to the resources directory
        cls.resources_dir = Path(__file__).parent / "resources" / "images"
        if not cls.resources_dir.exists():
            raise unittest.SkipTest("Resources directory not found")

    def test_export_files_table(self):
        # Generate real data from resources
        df_images, df_videos, df_others = analyze_directories([self.resources_dir])
        
        # We expect 3 images based on resources: test.CR2, test.CR3, test.JPG
        self.assertEqual(len(df_images), 3)
        
        output_path = Path("test_export.xlsx")
        
        try:
            # Export
            export_files_table(df_images, df_videos, df_others, output_path)
            
            # Verify file existence
            self.assertTrue(output_path.exists())
            
            # Verify sheets
            with pd.ExcelFile(output_path) as excel_file:
                self.assertIn("images", excel_file.sheet_names)
                self.assertIn("videos", excel_file.sheet_names)
                self.assertIn("others", excel_file.sheet_names)
            
            # Verify content
            df_read_images = pd.read_excel(output_path, sheet_name="images")
            self.assertEqual(len(df_read_images), 3)
            # Check if one of our test files is present
            self.assertIn("test", df_read_images["name"].tolist())
            
        finally:
            # Cleanup
            if output_path.exists():
                output_path.unlink()

if __name__ == "__main__":
    unittest.main()
