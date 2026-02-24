from pathlib import Path

import pandas as pd


def export_files_table(
    images_df: pd.DataFrame,
    videos_df: pd.DataFrame,
    others_df: pd.DataFrame,
    output_path: Path,
) -> None:
    with pd.ExcelWriter(output_path) as writer:
        images_df.to_excel(writer, sheet_name="images", index=False)
        videos_df.to_excel(writer, sheet_name="videos", index=False)
        others_df.to_excel(writer, sheet_name="others", index=False)
