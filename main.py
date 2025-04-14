import argparsefrom pathlib import Pathfrom gallery_inspector.convertor import cr2_to_jpgfrom gallery_inspector.export import export_images_tablefrom gallery_inspector.figures import plot_monthly_by_variablefrom gallery_inspector.generate import generate_images_tableparser = argparse.ArgumentParser(description="Gallery inspector")parser.add_argument('--function', type=str, required=True, help='Function name')parser.add_argument('--input', type=str, required=True, help='Path to the image folder')parser.add_argument('--output', type=str, required=True, help='Path to the outputs')args = parser.parse_args()match args.function:    case "analysis":        input_path = Path(args.input)        output_path = Path(args.output)        df = generate_images_table(input_path)        export_images_table(df, output_path / "images_table.xlsx")        plot_monthly_by_variable(df, output_path, 'LensModel')        plot_monthly_by_variable(df, output_path, 'Model')        plot_monthly_by_variable(df, output_path, 'ISOSpeedRatings')    case "convert":        input_path = Path(args.input)        output_path = Path(args.output)        cr2_to_jpg(input_path, output_path)