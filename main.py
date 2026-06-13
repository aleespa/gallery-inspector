import sys
import argparse
from datetime import date, datetime
from pathlib import Path
from loguru import logger

from gallery_inspector.filtering import FilterOptions, filter_files, is_query_empty, analyze_with_filters
from gallery_inspector.generate import Options
from gallery_inspector.export import export_files_table
from gallery_inspector.analysis import analyze_files


class TqdmProgressCallback:
    def __init__(self, desc="Processing"):
        try:
            from tqdm import tqdm
            self.pbar = tqdm(total=100, desc=desc)
        except ImportError:
            self.pbar = None
        self.last_val = 0

    def __call__(self, progress: float):
        val = int(progress * 100)
        if val > self.last_val:
            if self.pbar:
                self.pbar.update(val - self.last_val)
            else:
                sys.stdout.write(f"\r{self.pbar.desc if self.pbar else 'Progress'}: {val}%")
                sys.stdout.flush()
            self.last_val = val

    def close(self):
        if self.last_val < 100:
            if self.pbar:
                self.pbar.update(100 - self.last_val)
            else:
                sys.stdout.write(f"\rProgress: 100%\n")
                sys.stdout.flush()
        if self.pbar:
            self.pbar.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gallery Inspector CLI - Analyze, visualize, and organize photo and video collections."
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")
    
    # Parent parser for shared filter options
    filter_parser = argparse.ArgumentParser(add_help=False)
    filter_parser.add_argument(
        "--file-types",
        nargs="+",
        choices=["image", "video", "other"],
        help="Filter by file type(s) (image, video, other)."
    )
    filter_parser.add_argument(
        "--extensions",
        nargs="+",
        help="Filter by specific file extensions (e.g., .jpg .png .mp4)."
    )
    filter_parser.add_argument(
        "--date-start",
        type=date.fromisoformat,
        help="Filter files taken/modified on or after this date (YYYY-MM-DD)."
    )
    filter_parser.add_argument(
        "--date-end",
        type=date.fromisoformat,
        help="Filter files taken/modified on or before this date (YYYY-MM-DD)."
    )
    filter_parser.add_argument(
        "--cameras",
        nargs="+",
        help="Filter by camera model name(s) (case-sensitive)."
    )
    filter_parser.add_argument(
        "--lenses",
        nargs="+",
        help="Filter by lens name(s) (case-sensitive)."
    )
    filter_parser.add_argument(
        "--min-aperture",
        type=float,
        help="Filter by minimum aperture (f-number)."
    )
    filter_parser.add_argument(
        "--max-aperture",
        type=float,
        help="Filter by maximum aperture (f-number)."
    )
    filter_parser.add_argument(
        "--min-iso",
        type=int,
        help="Filter by minimum ISO value."
    )
    filter_parser.add_argument(
        "--max-iso",
        type=int,
        help="Filter by maximum ISO value."
    )
    filter_parser.add_argument(
        "--min-shutter-speed",
        help="Filter by minimum shutter speed string (e.g., 1/100)."
    )
    filter_parser.add_argument(
        "--max-shutter-speed",
        help="Filter by maximum shutter speed string (e.g., 1/200)."
    )
    
    # 1. Analyze Subparser
    analyze_parser = subparsers.add_parser(
        "analyze",
        parents=[filter_parser],
        help="Scan directories to extract metadata (EXIF/Video info), export results to Excel, and generate plots."
    )
    analyze_parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more input directories to scan."
    )
    analyze_parser.add_argument(
        "-o", "--output",
        required=True,
        type=Path,
        help="Output directory where the analysis report and plots will be saved."
    )
    
    # 2. Filter Subparser
    filter_cmd_parser = subparsers.add_parser(
        "filter",
        parents=[filter_parser],
        help="Organize files from input directories into the output directory based on filters and organization options."
    )
    filter_cmd_parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more input directories to scan."
    )
    filter_cmd_parser.add_argument(
        "-o", "--output",
        required=True,
        type=Path,
        help="Output directory where organized folders/files will be created."
    )
    filter_cmd_parser.add_argument(
        "--by-media-type",
        action="store_true",
        default=True,
        help="Separate organized files by media type (Photos/Videos) (default: True)."
    )
    filter_cmd_parser.add_argument(
        "--no-by-media-type",
        action="store_false",
        dest="by_media_type",
        help="Do not separate organized files by media type."
    )
    filter_cmd_parser.add_argument(
        "--structure",
        nargs="+",
        default=["Year", "Month"],
        choices=["Year", "Month", "Model", "Lens"],
        help="Folder structure hierarchy (e.g., --structure Year Month Model) (default: Year Month)."
    )
    filter_cmd_parser.add_argument(
        "--on-exist",
        choices=["rename", "skip"],
        default="rename",
        help="Handling of file name conflict in destination (default: rename)."
    )
    filter_cmd_parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose logging (default: True)."
    )
    filter_cmd_parser.add_argument(
        "--no-verbose",
        action="store_false",
        dest="verbose",
        help="Disable verbose logging."
    )
    
    return parser.parse_args()


def build_filter_query(args) -> FilterOptions:
    date_range = None
    if args.date_start or args.date_end:
        date_range = (args.date_start, args.date_end)
        
    aperture_range = None
    if args.min_aperture is not None or args.max_aperture is not None:
        aperture_range = (args.min_aperture, args.max_aperture)
        
    iso_range = None
    if args.min_iso is not None or args.max_iso is not None:
        iso_range = (args.min_iso, args.max_iso)
        
    shutter_speed_range = None
    if args.min_shutter_speed or args.max_shutter_speed:
        shutter_speed_range = (args.min_shutter_speed, args.max_shutter_speed)

    # Normalize extensions to have a dot if the user forgot it
    extensions = None
    if args.extensions:
        extensions = []
        for ext in args.extensions:
            ext_str = ext.strip()
            if ext_str:
                if not ext_str.startswith("."):
                    ext_str = f".{ext_str}"
                extensions.append(ext_str)

    return FilterOptions(
        filetypes=args.file_types,
        extensions=extensions,
        date_range=date_range,
        cameras=args.cameras,
        lenses=args.lenses,
        aperture_range=aperture_range,
        iso_range=iso_range,
        shutter_speed_range=shutter_speed_range,
    )


def handle_analyze(args):
    # Collect all files from input directories/files
    all_files = []
    for p in args.inputs:
        if p.is_dir():
            for file in p.rglob("*"):
                if not file.is_dir():
                    all_files.append(file)
        elif p.is_file():
            all_files.append(p)
            
    if not all_files:
        logger.warning("No files found to analyze.")
        sys.exit(0)

    query = build_filter_query(args)
    
    logger.info(f"Scanning {len(all_files)} files...")
    
    cb = TqdmProgressCallback("Analyzing")
    try:
        if is_query_empty(query):
            df_images, df_videos, df_others = analyze_files(
                all_files,
                progress_callback=cb,
            )
        else:
            df_images, df_videos, df_others = analyze_with_filters(
                all_files,
                query,
                progress_callback=cb,
            )
    finally:
        cb.close()

    name_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    analysis_dir = args.output / f"Analysis {name_date}"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = analysis_dir / "Metadata.xlsx"
    export_files_table(df_images, df_videos, df_others, output_file)
    logger.info(f"Metadata exported to {output_file}")
    
    figures_dir = analysis_dir / "Figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from gallery_inspector.figures import generate_plots
        generate_plots(output_file, figures_dir)
        logger.info(f"Plots saved to {figures_dir}")
    except Exception as e:
        logger.error(f"Failed to generate plots: {e}")

    logger.success(f"Analysis complete. Results saved in: {analysis_dir}")


def handle_filter(args):
    # Collect all files from input directories/files
    all_files = []
    for p in args.inputs:
        if p.is_dir():
            for file in p.rglob("*"):
                if not file.is_dir():
                    all_files.append(file)
        elif p.is_file():
            all_files.append(p)
            
    if not all_files:
        logger.warning("No files found to filter.")
        sys.exit(0)

    query = build_filter_query(args)
    
    options = Options(
        by_media_type=args.by_media_type,
        structure=args.structure,
        on_exist=args.on_exist,
        verbose=args.verbose,
    )
    
    logger.info(f"Filtering and organizing {len(all_files)} files...")
    
    cb = TqdmProgressCallback("Organizing")
    try:
        filter_files(
            all_files,
            args.output,
            options,
            query,
            progress_callback=cb,
        )
    finally:
        cb.close()

    logger.success(f"Filtering complete. Files organized in: {args.output}")


def main():
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(str(log_dir / "cli_log.log"), rotation="10 MB", level="DEBUG")

    args = parse_args()
    
    try:
        if args.command == "analyze":
            handle_analyze(args)
        elif args.command == "filter":
            handle_filter(args)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()