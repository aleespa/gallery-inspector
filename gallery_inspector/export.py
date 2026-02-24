from pathlib import Path

import pandas as pd


def export_files_table(
    images_df: pd.DataFrame,
    videos_df: pd.DataFrame,
    others_df: pd.DataFrame,
    output_path: Path,
) -> None:
    with pd.ExcelWriter(output_path) as writer:
        to_sheet_formatted(images_df, writer, sheet_name="images", index=False)
        to_sheet_formatted(videos_df, writer, sheet_name="videos", index=False)
        to_sheet_formatted(others_df, writer, sheet_name="others", index=False)


def to_sheet_formatted(
    df: pd.DataFrame,
    writer: pd.ExcelWriter,
    sheet_name: str,
    index: bool = False,
) -> None:
    # Write dataframe first
    df.to_excel(writer, sheet_name=sheet_name, index=index)

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    # Header format: black background, white bold text
    header_format = workbook.add_format({
        "bold": True,
        "text_wrap": False,
        "valign": "middle",
        "align": "left",
        "fg_color": "#000000",
        "font_color": "#FFFFFF",
        "border": 1,
    })

    # Rewrite headers with formatting
    for col_num, column in enumerate(df.columns):
        worksheet.write(0, col_num, column, header_format)

    # Adjust column widths
    for col_num, column in enumerate(df.columns):
        # Convert all values to string to measure length
        column_data = df[column].astype(str)

        max_length = max(
            column_data.map(len).max(),
            len(str(column))
        )

        worksheet.set_column(col_num, col_num, max_length + 2)

    # Add filters
    last_row = len(df)
    last_col = len(df.columns) - 1
    worksheet.autofilter(0, 0, last_row, last_col)

    # Optional: Freeze header row
    worksheet.freeze_panes(1, 0)