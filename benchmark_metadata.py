import time
import argparse
from pathlib import Path
from gallery_inspector.analysis import analyze_directories


def _run_once(path: Path):
    start_time = time.time()
    df_images, df_videos, df_others = analyze_directories([path])
    elapsed = time.time() - start_time
    total_files = len(df_images) + len(df_videos) + len(df_others)
    return elapsed, total_files, df_images, df_videos, df_others


def run_benchmark(directory_path: str):
    path = Path(directory_path)
    if not path.exists():
        print(f"Error: Path '{directory_path}' does not exist.")
        return

    print(f"\nBenchmarking metadata extraction for: {path.absolute()}")
    print("-" * 60)

    print("Running ExifTool batch benchmark (3 passes)...")
    pass_1, total_files, df_images, df_videos, df_others = _run_once(path)
    pass_2, _, _, _, _ = _run_once(path)
    pass_3, _, _, _, _ = _run_once(path)
    avg_time = (pass_1 + pass_2 + pass_3) / 3

    # Results Comparison
    print("\nBenchmark Results:")
    print("-" * 60)
    print(f"Total files detected: {total_files}")
    print(f"Run times: {pass_1:.2f}s, {pass_2:.2f}s, {pass_3:.2f}s")
    print(f"{'Method':<25} | {'Total Time':<12} | {'Avg per file':<12}")
    print("-" * 60)
    print(
        f"{'ExifTool (Batch)':<25} | {avg_time:>10.2f}s | {avg_time/total_files:>10.4f}s"
        if total_files > 0
        else "N/A"
    )
    print("-" * 60)

    print("\nBreakdown:")
    print(f"Images: {len(df_images)}")
    print(f"Videos: {len(df_videos)}")
    print(f"Others: {len(df_others)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark metadata extraction methods.")
    parser.add_argument("directory", help="Directory to analyze")
    args = parser.parse_args()
    
    run_benchmark(args.directory)
