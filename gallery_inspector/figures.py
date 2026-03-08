import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def _save_plot(fig, output_dir: Path, filename: str):
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_image_cameras(df: pd.DataFrame, output_dir: Path):
    if "camera" not in df.columns or df["camera"].dropna().empty:
        return
    counts = df["camera"].value_counts().nlargest(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot(kind="bar", color="skyblue", ax=ax)
    ax.set_title("Top Cameras Used", fontsize=16)
    ax.set_xlabel("Camera Model", fontsize=12)
    ax.set_ylabel("Number of Photos", fontsize=12)
    ax.tick_params(axis="x", rotation=45)
    _save_plot(fig, output_dir, "images_cameras.png")


def plot_image_lenses(df: pd.DataFrame, output_dir: Path):
    if "lens" not in df.columns or df["lens"].dropna().empty:
        return
    counts = df["lens"].value_counts().nlargest(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot(kind="bar", color="lightgreen", ax=ax)
    ax.set_title("Top Lenses Used", fontsize=16)
    ax.set_xlabel("Lens Model", fontsize=12)
    ax.set_ylabel("Number of Photos", fontsize=12)
    ax.tick_params(axis="x", rotation=45)
    _save_plot(fig, output_dir, "images_lenses.png")


def plot_image_settings(df: pd.DataFrame, output_dir: Path):
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))

    if "aperture" in df.columns and not df["aperture"].dropna().empty:
        counts = df["aperture"].value_counts().sort_index()
        axes[0].bar([str(x) for x in counts.index], counts.values, color="coral")
        axes[0].set_title("Aperture (f-stop)", fontsize=14)
        axes[0].set_xlabel("Aperture", fontsize=12)
        axes[0].set_ylabel("Count", fontsize=12)
        axes[0].tick_params(axis="x", rotation=90)

    if "shutter_speed" in df.columns and not df["shutter_speed"].dropna().empty:
        counts = df["shutter_speed"].value_counts()
        # Take top 15 most common shutter speeds and sort them logically if possible, or just by count
        counts = counts.nlargest(15)
        axes[1].bar([str(x) for x in counts.index], counts.values, color="orchid")
        axes[1].set_title("Shutter Speeds (Top 15)", fontsize=14)
        axes[1].set_xlabel("Shutter Speed", fontsize=12)
        axes[1].set_ylabel("Count", fontsize=12)
        axes[1].tick_params(axis="x", rotation=90)

    if "iso" in df.columns and not df["iso"].dropna().empty:
        counts = df["iso"].value_counts().sort_index()
        # Keep top 15
        counts = counts.nlargest(15).sort_index()
        axes[2].bar([str(x) for x in counts.index], counts.values, color="gold")
        axes[2].set_title("ISO Settings (Top 15)", fontsize=14)
        axes[2].set_xlabel("ISO", fontsize=12)
        axes[2].set_ylabel("Count", fontsize=12)
        axes[2].tick_params(axis="x", rotation=90)
        
    if "focal_length" in df.columns and not df["focal_length"].dropna().empty:
        counts = df["focal_length"].value_counts().sort_index()
        # Keep top 15
        counts = counts.nlargest(15).sort_index()
        axes[3].bar([str(x) for x in counts.index], counts.values, color="teal")
        axes[3].set_title("Focal Lengths (Top 15)", fontsize=14)
        axes[3].set_xlabel("Focal Length (mm)", fontsize=12)
        axes[3].set_ylabel("Count", fontsize=12)
        axes[3].tick_params(axis="x", rotation=90)

    fig.suptitle("Camera Settings Distribution", fontsize=18)
    _save_plot(fig, output_dir, "images_settings.png")


def plot_video_duration(df: pd.DataFrame, output_dir: Path):
    if "duration_ms" not in df.columns or df["duration_ms"].dropna().empty:
        return
    durations_s = df["duration_ms"].dropna() / 1000.0
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(durations_s, bins=50, color="crimson", edgecolor="black")
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

    aggs = df.groupby("month").agg(
        count=("name", "count"),
        total_time=("duration_s", "sum")
    ).sort_index()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    ax1.plot(aggs.index, aggs["count"], marker="o", color="blue", linewidth=2)
    ax1.set_title("Recording Activity Over Time (Videos per Month)", fontsize=14)
    ax1.set_ylabel("Number of Videos", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.7)

    ax2.plot(aggs.index, aggs["total_time"] / 60.0, marker="o", color="darkorange", linewidth=2)
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

    # Map with dots
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    ax1.scatter(df_loc["longitude"], df_loc["latitude"], alpha=0.5, c="blue", s=20, edgecolors="none")
    ax1.set_title("File Locations Map", fontsize=16)
    ax1.set_xlabel("Longitude", fontsize=12)
    ax1.set_ylabel("Latitude", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.5)
    _save_plot(fig1, output_dir, "locations_map.png")

    # Heatmap
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    hb = ax2.hexbin(df_loc["longitude"], df_loc["latitude"], gridsize=50, cmap="YlOrRd", mincnt=1)
    cb = fig2.colorbar(hb, ax=ax2)
    cb.set_label("Number of Files", fontsize=12)
    ax2.set_title("Location Density Heatmap", fontsize=16)
    ax2.set_xlabel("Longitude", fontsize=12)
    ax2.set_ylabel("Latitude", fontsize=12)
    ax2.grid(True, linestyle="--", alpha=0.5)
    _save_plot(fig2, output_dir, "locations_heatmap.png")


def plot_general_counts(df_images: pd.DataFrame, df_videos: pd.DataFrame, df_others: pd.DataFrame, output_dir: Path):
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
    ax.pie(counts.values(), labels=counts.keys(), autopct="%1.1f%%", startangle=140, colors=["#ff9999", "#66b3ff", "#99ff99"])
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
        df_images = pd.read_excel(xls, sheet_name="images") if "images" in xls.sheet_names else pd.DataFrame()
        df_videos = pd.read_excel(xls, sheet_name="videos") if "videos" in xls.sheet_names else pd.DataFrame()
        df_others = pd.read_excel(xls, sheet_name="others") if "others" in xls.sheet_names else pd.DataFrame()

        # General plots
        plot_general_counts(df_images, df_videos, df_others, figures_dir)
        
        # Image plots
        if not df_images.empty:
            plot_image_cameras(df_images, figures_dir)
            plot_image_lenses(df_images, figures_dir)
            plot_image_settings(df_images, figures_dir)
        
        # Video plots
        if not df_videos.empty:
            plot_video_duration(df_videos, figures_dir)
            plot_video_timeline(df_videos, figures_dir)
            
        # Combine locations from images and videos
        dfs_loc = []
        if not df_images.empty and "latitude" in df_images.columns and "longitude" in df_images.columns:
            dfs_loc.append(df_images[["latitude", "longitude"]])
        if not df_videos.empty and "latitude" in df_videos.columns and "longitude" in df_videos.columns:
            dfs_loc.append(df_videos[["latitude", "longitude"]])
            
        if dfs_loc:
            df_combined_loc = pd.concat(dfs_loc, ignore_index=True)
            plot_locations(df_combined_loc, figures_dir)

        print(f"All plots saved to {figures_dir}")
        
    except Exception as e:
        print(f"Failed during plot generation: {e}")
