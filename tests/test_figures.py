import unittest
from pathlib import Path
from gallery_inspector.figures import generate_plots

class TestFigures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Define resources and target directories
        cls.resources_dir = Path(__file__).parent / "resources"
        cls.metadata_file = cls.resources_dir / "metadata_test.xlsx"
        cls.target_dir = Path(__file__).parent / "target" / "Figures"
        
        # Ensure target directory exists
        cls.target_dir.mkdir(parents=True, exist_ok=True)
        
        if not cls.metadata_file.exists():
            raise unittest.SkipTest("Metadata test file not found")

    def test_generate_plots(self):
        # Generate plots
        generate_plots(self.metadata_file, self.target_dir)
        
        # Check generated files
        generated_files = [f.name for f in self.target_dir.iterdir() if f.is_file()]
        print("Generated files:", generated_files)
        
        # Ensure that all expected basic plots were generated
        expected_files = {
            "general_file_types.png",
            "images_cameras.png",
            "images_lenses.png",
            "images_settings.png",
            "images_monthly_camera.png",
            "images_monthly_lens.png",
            "images_yearly_camera.png",
            "images_yearly_lens.png",
            "locations_heatmap.png",
            "locations_map.png"
        }

        self.assertGreater(len(generated_files), 0, "No plots were generated")
        self.assertTrue(
            set(generated_files).issuperset(expected_files), 
            f"Missing some expected plots. Found: {generated_files}"
        )
        self.assertTrue(
            all(f.endswith(".png") for f in generated_files), 
            "Not all generated files are PNGs"
        )
