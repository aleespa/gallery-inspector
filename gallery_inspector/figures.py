import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# --- Plot Color Customization ---
PLOT_COLORS = {
    "camera": "skyblue",
    "lens": "lightgreen",
    "aperture": "coral",
    "shutter_speed": "orchid",
    "iso": "gold",
    "focal_length": "teal",
    "video_duration": "crimson",
    "timeline_count": "blue",
    "timeline_time": "darkorange",
    "map_land": "white",
    "map_border": "lightgray",
    "map_points": "blue",
    "heatmap_land": "#C5C5C5",
    "heatmap_cmap": "autumn",
    "stacked_colors": [
        "#e60000", "#3d6ba6", "#65880f", "#4e4e94",
        "#ff5252", "#5a8cc2", "#8eb027", "#7474b0",
        "#a70000", "#2b4e72", "#5f720f", "#313178",
        "#ff7b7b", "#a7c6ed", "#c1d64d", "#a1a1ce",
        "#ffbaba", "#e4ecf5", "#d1ef71", "#cfcfe8",

    ],
    "pie_chart": ["#ff9999", "#66b3ff", "#99ff99"]
}
# --------------------------------


def _save_plot(fig, output_dir: Path, filename: str):
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_image_cameras(df: pd.DataFrame, output_dir: Path):
    if "camera" not in df.columns or df["camera"].dropna().empty:
        return
    counts = df["camera"].value_counts().nlargest(15)
    fig, ax = plt.subplots(figsize=(10, 8))
    
    custom_colors = PLOT_COLORS["stacked_colors"]
    colors = [custom_colors[i % len(custom_colors)] for i in range(len(counts))]
    
    wedges, texts = ax.pie(
        counts.values,
        startangle=140,
        colors=colors,
    )
    
    total = sum(counts.values)
    legend_labels = [f"{idx} ({val/total*100:.1f}%)" for idx, val in zip(counts.index, counts.values)]
    
    ax.legend(
        wedges,
        legend_labels,
        title="Camera Model",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        frameon=False,
    )
    ax.set_title("Top Cameras Used", fontsize=16)
    _save_plot(fig, output_dir, "images_cameras.png")


def plot_image_lenses(df: pd.DataFrame, output_dir: Path):
    if "lens" not in df.columns or df["lens"].dropna().empty:
        return
    counts = df["lens"].value_counts().nlargest(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot(kind="bar", color=PLOT_COLORS["lens"], ax=ax)
    ax.set_title("Top Lenses Used", fontsize=16)
    ax.set_xlabel("Lens Model", fontsize=12)
    ax.set_ylabel("Number of Photos", fontsize=12)
    ax.tick_params(axis="x", rotation=45)
    _save_plot(fig, output_dir, "images_lenses.png")


def plot_image_settings(df: pd.DataFrame, output_dir: Path):
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))

    if "aperture" in df.columns and not df["aperture"].dropna().empty:
        counts = df["aperture"].value_counts().sort_index()
        axes[0].bar([str(x) for x in counts.index], counts.values, color=PLOT_COLORS["aperture"])
        axes[0].set_title("Aperture (f-stop)", fontsize=14)
        axes[0].set_xlabel("Aperture", fontsize=12)
        axes[0].set_ylabel("Count", fontsize=12)
        axes[0].tick_params(axis="x", rotation=90)

    if "shutter_speed" in df.columns and not df["shutter_speed"].dropna().empty:
        counts = df["shutter_speed"].value_counts()
        # Take top 15 most common shutter speeds and sort them logically if possible, or just by count
        counts = counts.nlargest(15)
        axes[1].bar([str(x) for x in counts.index], counts.values, color=PLOT_COLORS["shutter_speed"])
        axes[1].set_title("Shutter Speeds (Top 15)", fontsize=14)
        axes[1].set_xlabel("Shutter Speed", fontsize=12)
        axes[1].set_ylabel("Count", fontsize=12)
        axes[1].tick_params(axis="x", rotation=90)

    if "iso" in df.columns and not df["iso"].dropna().empty:
        counts = df["iso"].value_counts().sort_index()
        # Keep top 15
        counts = counts.nlargest(15).sort_index()
        axes[2].bar([str(x) for x in counts.index], counts.values, color=PLOT_COLORS["iso"])
        axes[2].set_title("ISO Settings (Top 15)", fontsize=14)
        axes[2].set_xlabel("ISO", fontsize=12)
        axes[2].set_ylabel("Count", fontsize=12)
        axes[2].tick_params(axis="x", rotation=90)

    if "focal_length" in df.columns and not df["focal_length"].dropna().empty:
        counts = df["focal_length"].value_counts().sort_index()
        # Keep top 15
        counts = counts.nlargest(15).sort_index()
        axes[3].bar([str(x) for x in counts.index], counts.values, color=PLOT_COLORS["focal_length"])
        axes[3].set_title("Focal Lengths (Top 15)", fontsize=14)
        axes[3].set_xlabel("Focal Length (mm)", fontsize=12)
        axes[3].set_ylabel("Count", fontsize=12)
        axes[3].tick_params(axis="x", rotation=90)

    fig.suptitle("Camera Settings Distribution", fontsize=18)
    _save_plot(fig, output_dir, "images_settings.png")


def plot_timeline_stacked(df: pd.DataFrame, group_by: str, time_by: str, output_dir: Path):
    if "date_taken" not in df.columns or group_by not in df.columns:
        return

    df = df.copy()
    df["date_taken"] = pd.to_datetime(df["date_taken"], errors="coerce")
    df = df.dropna(subset=["date_taken", group_by])

    if df.empty:
        return

    if time_by == "year":
        df["time_period"] = df["date_taken"].dt.year
        xlabel = "Year"
        filename_prefix = "yearly"
    else:  # month
        df["time_period"] = df["date_taken"].dt.to_period("M").apply(lambda r: r.start_time)
        xlabel = "Month"
        filename_prefix = "monthly"

    # Keep only the top 15 groups to avoid cluttered legends
    top_groups = df[group_by].value_counts().nlargest(15).index
    df.loc[~df[group_by].isin(top_groups), group_by] = "Other"

    # Pivot table for stacked bars
    pivot_df = df.groupby(["time_period", group_by]).size().unstack(fill_value=0)

    if pivot_df.empty:
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    # Apply customizable colors, cycling via modulo if there's more groupings than colors
    custom_colors = PLOT_COLORS["stacked_colors"]
    colors = [custom_colors[i % len(custom_colors)] for i in range(len(pivot_df.columns))]

    pivot_df.plot(kind="bar", stacked=True, ax=ax, color=colors, width=0.8)

    title_entity = "Camera Model" if group_by == "camera" else "Lens"
    ax.set_title(f"Number of Pictures Taken per {xlabel}, Stacked by {title_entity}", fontsize=16)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("Number of Pictures", fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    # Clean up x-axis depending on the period format
    if time_by == "month":
        tick_labels = [x.strftime("%Y-%m") for x in pivot_df.index]
        # Only show a label at the first occurrence of each year
        year_seen = set()
        sparse_labels = []
        for x in pivot_df.index:
            year = x.year
            if year not in year_seen:
                year_seen.add(year)
                sparse_labels.append(str(year))
            else:
                sparse_labels.append("")
        ax.set_xticklabels(sparse_labels, rotation=45, ha="right")
    else:
        ax.tick_params(axis="x", rotation=45)

    ax.legend(title=title_entity, bbox_to_anchor=(1.05, 1), loc="upper left", frameon=False)

    filename = f"images_{filename_prefix}_{group_by}.png"
    _save_plot(fig, output_dir, filename)


def plot_video_duration(df: pd.DataFrame, output_dir: Path):
    if "duration_ms" not in df.columns or df["duration_ms"].dropna().empty:
        return
    durations_s = df["duration_ms"].dropna() / 1000.0
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(durations_s, bins=50, color=PLOT_COLORS["video_duration"], edgecolor="black")
    ax.set_title("Video Duration Distribution", fontsize=16)
    ax.set_xlabel("Duration (seconds)", fontsize=12)
    ax.set_ylabel("Number of Videos", fontsize=12)
    _save_plot(fig, output_dir, "videos_duration.png")


def plot_video_timeline(df: pd.DataFrame, output_dir: Path):
    if "date_taken" not in df.columns or "duration_ms" not in df.columns:
        return

    df = df.copy()
    df["date_taken"] = pd.to_datetime(df["date_taken"], errors="coerce")
    df = df.dropna(subset=["date_taken"])
    if df.empty:
        return

    df["month"] = df["date_taken"].dt.to_period("M").apply(lambda r: r.start_time)
    df["duration_s"] = df["duration_ms"].fillna(0) / 1000.0

    aggs = (
        df.groupby("month")
        .agg(count=("name", "count"), total_time=("duration_s", "sum"))
        .sort_index()
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    ax1.plot(aggs.index, aggs["count"], marker="o", color=PLOT_COLORS["timeline_count"], linewidth=2)
    ax1.set_title("Recording Activity Over Time (Videos per Month)", fontsize=14)
    ax1.set_ylabel("Number of Videos", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.7)

    ax2.plot(
        aggs.index,
        aggs["total_time"] / 60.0,
        marker="o",
        color=PLOT_COLORS["timeline_time"],
        linewidth=2,
    )
    ax2.set_title("Total Recording Time per Month", fontsize=14)
    ax2.set_ylabel("Total Duration (minutes)", fontsize=12)
    ax2.set_xlabel("Month", fontsize=12)
    ax2.grid(True, linestyle="--", alpha=0.7)

    fig.suptitle("Video Recording Timeline", fontsize=18)
    _save_plot(fig, output_dir, "videos_timeline.png")


def plot_locations(df: pd.DataFrame, output_dir: Path):
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return

    df_loc = df.dropna(subset=["latitude", "longitude"]).copy()
    # Need to make sure they are numeric
    df_loc["latitude"] = pd.to_numeric(df_loc["latitude"], errors="coerce")
    df_loc["longitude"] = pd.to_numeric(df_loc["longitude"], errors="coerce")
    df_loc = df_loc.dropna(subset=["latitude", "longitude"])

    if df_loc.empty:
        return

    try:
        import geopandas as gpd
        import geodatasets

        path = geodatasets.get_path("naturalearth.land")
        world = gpd.read_file(path)
        has_map = True
    except ImportError:
        has_map = False

    # Map with dots
    fig1, ax1 = plt.subplots(figsize=(12, 8), dpi=150)
    if has_map:
        world.plot(ax=ax1, color=PLOT_COLORS["map_land"], edgecolor=PLOT_COLORS["map_border"])
    ax1.scatter(
        df_loc["longitude"],
        df_loc["latitude"],
        alpha=0.5,
        c=PLOT_COLORS["map_points"],
        s=20,
        edgecolors="none",
        zorder=5,
    )
    ax1.axis("off")
    _save_plot(fig1, output_dir, "locations_map.png")

    # Heatmap
    fig2, ax2 = plt.subplots(figsize=(12, 8), dpi=150)
    if has_map:
        world.plot(ax=ax2, color=PLOT_COLORS["heatmap_land"], edgecolor=None)
    hb = ax2.hexbin(
        df_loc["longitude"],
        df_loc["latitude"],
        gridsize=45,
        cmap=PLOT_COLORS["heatmap_cmap"],
        mincnt=1,
        alpha=0.8,
        zorder=5,
    )
    ax2.set_title("Location Density Heatmap", fontsize=16)
    ax2.axis("off")
    _save_plot(fig2, output_dir, "locations_heatmap.png")


def plot_general_counts(
    df_images: pd.DataFrame,
    df_videos: pd.DataFrame,
    df_others: pd.DataFrame,
    output_dir: Path,
):
    counts = {
        "Images": len(df_images) if "name" in df_images.columns else 0,
        "Videos": len(df_videos) if "name" in df_videos.columns else 0,
        "Others": len(df_others) if "name" in df_others.columns else 0,
    }

    # Filter out zeros
    counts = {k: v for k, v in counts.items() if v > 0}
    if not counts:
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        counts.values(),
        labels=counts.keys(),
        autopct="%1.1f%%",
        startangle=140,
        colors=PLOT_COLORS["pie_chart"],
    )
    ax.set_title("File Type Distribution", fontsize=16)
    _save_plot(fig, output_dir, "general_file_types.png")


def generate_plots(metadata_file: Path, figures_dir: Path):
    """
    Main function to generate matplotlib plots from the Metadata.xlsx file.
    """
    try:
        # Check if the file exists and is readable
        if not metadata_file.exists():
            print(f"Error: {metadata_file} not found.")
            return

        xls = pd.ExcelFile(metadata_file)

        # Load dataframes safely
        df_images = (
            pd.read_excel(xls, sheet_name="images")
            if "images" in xls.sheet_names
            else pd.DataFrame()
        )
        df_videos = (
            pd.read_excel(xls, sheet_name="videos")
            if "videos" in xls.sheet_names
            else pd.DataFrame()
        )
        df_others = (
            pd.read_excel(xls, sheet_name="others")
            if "others" in xls.sheet_names
            else pd.DataFrame()
        )

        # General plots
        plot_general_counts(df_images, df_videos, df_others, figures_dir)

        # Image plots
        if not df_images.empty:
            plot_image_cameras(df_images, figures_dir)
            plot_image_lenses(df_images, figures_dir)
            plot_image_settings(df_images, figures_dir)
            plot_timeline_stacked(df_images, "camera", "year", figures_dir)
            plot_timeline_stacked(df_images, "lens", "year", figures_dir)
            plot_timeline_stacked(df_images, "camera", "month", figures_dir)
            plot_timeline_stacked(df_images, "lens", "month", figures_dir)

        # Video plots
        if not df_videos.empty:
            plot_video_duration(df_videos, figures_dir)
            plot_video_timeline(df_videos, figures_dir)

        # Combine locations from images and videos
        dfs_loc = []
        if (
            not df_images.empty
            and "latitude" in df_images.columns
            and "longitude" in df_images.columns
        ):
            dfs_loc.append(df_images[["latitude", "longitude"]])
        if (
            not df_videos.empty
            and "latitude" in df_videos.columns
            and "longitude" in df_videos.columns
        ):
            dfs_loc.append(df_videos[["latitude", "longitude"]])

        if dfs_loc:
            df_combined_loc = pd.concat(dfs_loc, ignore_index=True)
            plot_locations(df_combined_loc, figures_dir)

        print(f"All plots saved to {figures_dir}")

    except Exception as e:
        print(f"Failed during plot generation: {e}")
