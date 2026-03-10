import time
import argparse
import sys
from pathlib import Path
from gallery_inspector.analysis import analyze_directories

def run_benchmark(directory_path: str):
    path = Path(directory_path)
    if not path.exists():
        print(f"Error: Path '{directory_path}' does not exist.")
        return

    print(f"\nBenchmarking metadata extraction for: {path.absolute()}")
    print("-" * 60)

    # 1. Benchmark ExifTool Batch
    print("Running with ExifTool (Batch Mode)...")
    start_time = time.time()
    df_images_exif, df_videos_exif, df_others_exif = analyze_directories([path], use_exiftool=True)
    exif_time = time.time() - start_time
    total_files_exif = len(df_images_exif) + len(df_videos_exif) + len(df_others_exif)
    
    # 2. Benchmark Original Mode
    print("Running with Original Mode (One-by-one)...")
    start_time = time.time()
    df_images_orig, df_videos_orig, df_others_orig = analyze_directories([path], use_exiftool=False)
    orig_time = time.time() - start_time
    total_files_orig = len(df_images_orig) + len(df_videos_orig) + len(df_others_orig)

    # Results Comparison
    print("\nBenchmark Results:")
    print("-" * 60)
    print(f"Total files detected: {total_files_exif}")
    print(f"{'Method':<25} | {'Total Time':<12} | {'Avg per file':<12}")
    print("-" * 60)
    print(f"{'ExifTool (Batch)':<25} | {exif_time:>10.2f}s | {exif_time/total_files_exif:>10.4f}s" if total_files_exif > 0 else "N/A")
    print(f"{'Original (One-by-one)':<25} | {orig_time:>10.2f}s | {orig_time/total_files_orig:>10.4f}s" if total_files_orig > 0 else "N/A")
    print("-" * 60)
    
    if exif_time > 0:
        speedup = orig_time / exif_time
        print(f"Speedup: {speedup:.2f}x faster with ExifTool batching.")
    
    # Data Integrity Check
    print("\nData Integrity Check:")
    print(f"Images: ExifTool={len(df_images_exif)}, Original={len(df_images_orig)}")
    print(f"Videos: ExifTool={len(df_videos_exif)}, Original={len(df_videos_orig)}")
    print(f"Others: ExifTool={len(df_others_exif)}, Original={len(df_others_orig)}")
    
    if len(df_images_exif) != len(df_images_orig) or len(df_videos_exif) != len(df_videos_orig):
        print("WARNING: File counts mismatch between methods!")
    else:
        print("SUCCESS: File counts match.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark metadata extraction methods.")
    parser.add_argument("directory", help="Directory to analyze")
    args = parser.parse_args()
    
    run_benchmark(args.directory)
