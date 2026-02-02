from pathlib import Path

import pandas as pd


def export_images_table(df: pd.DataFrame, output_path: Path) -> None:
    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name="files", index=False)
