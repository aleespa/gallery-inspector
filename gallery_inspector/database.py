"""Per-drive Excel metadata database with incremental, additive updates.

Each managed drive carries a single ``Metadata.xlsx`` at its root describing the
media that lives on it. Imports update this database incrementally, reusing the
metadata already extracted while copying instead of re-scanning the whole drive.

Sync policy: *add + refresh, keep rest*. New files are appended; a file whose
``Full path`` already exists has its row refreshed; rows are never pruned.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import pandas as pd
from loguru import logger

from gallery_inspector.analysis import _empty_df
from gallery_inspector.export import export_files_table

SHEET_BY_TYPE = {"image": "images", "video": "videos", "other": "others"}

RowInput = Union[Sequence[Dict], pd.DataFrame]


def _normalize_path(path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _to_frame(rows: Optional[RowInput], type_name: str) -> pd.DataFrame:
    """Coerce a list of row dicts (or a DataFrame) into a typed DataFrame."""
    if rows is None:
        return _empty_df(type_name)
    if isinstance(rows, pd.DataFrame):
        df = rows.copy()
    else:
        df = pd.DataFrame(list(rows))
    if df.empty:
        return _empty_df(type_name)
    return df


def _coerce_date_taken(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a read-back ``date_taken`` column to plain ``date`` objects."""
    if "date_taken" not in df.columns or df.empty:
        return df
    parsed = pd.to_datetime(df["date_taken"], errors="coerce")
    df["date_taken"] = parsed.dt.date
    return df


def read_database(
    excel_path: Union[str, Path]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read an existing database workbook.

    Returns three correctly-columned DataFrames (images, videos, others).
    A missing or unreadable file yields three empty frames.
    """
    excel_path = Path(excel_path)
    empties = (_empty_df("image"), _empty_df("video"), _empty_df("other"))

    if not excel_path.exists():
        return empties

    try:
        with pd.ExcelFile(excel_path) as xls:
            available = set(xls.sheet_names)
            frames = []
            for type_name, sheet in SHEET_BY_TYPE.items():
                if sheet in available:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    df = _coerce_date_taken(df)
                else:
                    df = _empty_df(type_name)
                frames.append(df)
            return frames[0], frames[1], frames[2]
    except Exception as exc:
        logger.warning(f"Could not read existing database '{excel_path}': {exc}")
        return empties


def _merge(existing: pd.DataFrame, new: pd.DataFrame, type_name: str) -> pd.DataFrame:
    """Concat existing + new, dedupe on normalized Full path (keep last)."""
    columns = list(_empty_df(type_name).columns)

    frames = [df for df in (existing, new) if df is not None and not df.empty]
    if not frames:
        return _empty_df(type_name)

    merged = pd.concat(frames, ignore_index=True)

    if "Full path" in merged.columns:
        key = merged["Full path"].map(
            lambda p: _normalize_path(p) if pd.notna(p) else p
        )
        merged = merged.loc[~key.duplicated(keep="last")].reset_index(drop=True)

    # Keep the canonical column order/set; tolerate stray or missing columns.
    return merged.reindex(columns=columns)


def update_database(
    excel_path: Union[str, Path],
    new_images: Optional[RowInput] = None,
    new_videos: Optional[RowInput] = None,
    new_others: Optional[RowInput] = None,
) -> None:
    """Additively merge new rows into the drive database at ``excel_path``.

    Existing rows are preserved; rows whose ``Full path`` matches an incoming
    row are refreshed; nothing is pruned. The workbook is written atomically so
    an interrupted write cannot corrupt the existing database.
    """
    excel_path = Path(excel_path)

    existing_images, existing_videos, existing_others = read_database(excel_path)

    images = _merge(existing_images, _to_frame(new_images, "image"), "image")
    videos = _merge(existing_videos, _to_frame(new_videos, "video"), "video")
    others = _merge(existing_others, _to_frame(new_others, "other"), "other")

    excel_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then atomically replace.
    fd, tmp_name = tempfile.mkstemp(
        suffix=".xlsx", prefix=".metadata_", dir=str(excel_path.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        export_files_table(images, videos, others, tmp_path)
        os.replace(tmp_path, excel_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    logger.info(
        f"Database updated: {excel_path} "
        f"(images={len(images)}, videos={len(videos)}, others={len(others)})"
    )


def destination_row(raw_metadata: Dict, destination: Path) -> Dict:
    """Rewrite an analyzed metadata row to point at its destination on the drive.

    EXIF/size fields are unchanged (same file content); only the path-derived
    fields (``Full path``, ``directory``, ``name``) are updated.
    """
    destination = Path(destination)
    row = dict(raw_metadata)
    row["Full path"] = str(destination)
    row["directory"] = str(destination.parent)
    row["name"] = destination.stem
    return row
