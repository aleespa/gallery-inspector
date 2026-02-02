from pathlib import Path
from typing import Optional
import os

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px


def plot_monthly_by_variable(
    df: pd.DataFrame,
    output: Optional[Path] = None,
    variable: str = "LensModel",
    date_column: str = "DateTimeOriginal",
    date_format: str = "%Y-%m-%d %H:%M:%S",
):
    df = df.copy()
    df[date_column] = pd.to_datetime(
        df[date_column], format=date_format, errors="coerce"
    )
    df[variable] = df[variable].replace("", pd.NA)
    df = df.dropna(subset=[date_column, variable])
    df["Month"] = df[date_column].dt.to_period("M").apply(lambda r: r.start_time)
    monthly_counts = df.groupby(["Month", variable]).size().unstack()
    fig, ax = plt.subplots(figsize=(14, 8))
    monthly_counts_cumsum = monthly_counts.cumsum(axis=1)
    for i, lens in enumerate(monthly_counts.columns):
        ax.bar(
            monthly_counts.index,
            monthly_counts[lens],
            width=15,
            bottom=monthly_counts_cumsum[lens] - monthly_counts[lens],
            label=lens,
        )
    ax.set_title(f"Monthly Number of Pictures Taken by {variable}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of Pictures")
    ax.spines[["right", "top"]].set_visible(False)
    ax.legend(title="Lens Model", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    if output:
        plt.savefig(output / f"plot_weekly_{variable}.png")
    return fig


def plot_interactive_timeline(
    df: pd.DataFrame,
    variable: str = "LensModel",
    date_column: str = "DateTimeOriginal",
    date_format: str = "%Y-%m-%d %H:%M:%S",
):
    df = df.copy()
    df[date_column] = pd.to_datetime(
        df[date_column], format=date_format, errors="coerce"
    )
    df[variable] = df[variable].replace("", pd.NA)
    df = df.dropna(subset=[date_column, variable])
    df["Month"] = df[date_column].dt.to_period("M").apply(lambda r: r.start_time)

    # Group by Month and Variable to get counts
    monthly_counts = df.groupby(["Month", variable]).size().reset_index(name="Count")

    fig = px.bar(
        monthly_counts,
        x="Month",
        y="Count",
        color=variable,
        title=f"Monthly Number of Pictures Taken by {variable}",
        labels={"Count": "Number of Pictures", "Month": "Month"},
    )

    return fig


def plot_sunburst(
    df: pd.DataFrame, path_column: str = "directory", size_column: str = "size (MB)"
):
    """
    Creates a sunburst chart representing the directory structure and file sizes.
    """
    if df.empty:
        return None

    # We need to process the paths to create a hierarchy
    # This is a simplified version, assuming 'directory' contains the full path
    # We'll take the last few components of the path to avoid too much clutter

    df = df.copy()

    # Helper to get relative path parts
    # We'll try to find a common prefix and remove it
    try:
        common_prefix = os.path.commonpath(df[path_column].unique())
        df["rel_path"] = df[path_column].apply(
            lambda x: os.path.relpath(x, common_prefix)
        )
    except Exception:
        df["rel_path"] = df[path_column]

    df["path_parts"] = df["rel_path"].apply(lambda x: x.split(os.sep) + ["(Files)"])

    # Limit depth for visualization
    max_depth = 3
    for i in range(max_depth):
        df[f"level_{i}"] = df["path_parts"].apply(
            lambda x: x[i] if i < len(x) else None
        )

    # Aggregate size
    # We'll group by the levels
    levels = [f"level_{i}" for i in range(max_depth)]
    # fillna with a placeholder to ensure groupby doesn't drop rows, then replace back if needed
    # or just use dropna=False which is available in newer pandas
    df_agg = df.groupby(levels, dropna=False)[size_column].sum().reset_index()

    fig = px.sunburst(
        df_agg,
        path=levels,
        values=size_column,
        title="Directory Size Distribution",
        color=size_column,
        color_continuous_scale="RdBu_r",
    )
    return fig


def plot_scatter(df: pd.DataFrame, x: str, y: str, color: str = None):
    """
    Creates a scatter plot for two variables.
    """
    df = df.copy()
    df = df.dropna(subset=[x, y])

    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color,
        title=f"{y} vs {x}",
        hover_data=["name", "Model", "LensModel"],
    )
    return fig


def plot_file_types(df: pd.DataFrame):
    """
    Creates a pie chart of file types.
    """
    counts = df["filetype"].value_counts().reset_index()
    counts.columns = ["filetype", "count"]

    fig = px.pie(
        counts, names="filetype", values="count", title="File Type Distribution"
    )
    return fig


def plot_size_distribution(df: pd.DataFrame):
    """
    Creates a histogram of file sizes.
    """
    fig = px.histogram(
        df,
        x="size (MB)",
        nbins=50,
        title="File Size Distribution",
        labels={"size (MB)": "Size (MB)"},
    )
    return fig
