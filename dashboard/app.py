import sys
from pathlib import Path

# Add project root to sys.path to allow importing gallery_inspector
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Gallery Inspector", layout="wide")
st.title("Gallery Inspector Dashboard")

# ── Helpers & Caching ─────────────────────────────────────────────────────────

STACKED_COLORS = [
    "#e60000", "#3d6ba6", "#65880f", "#4e4e94",
    "#a70000", "#2b4e72", "#5f720f", "#313178",
    "#ff5252", "#5a8cc2", "#8eb027", "#7474b0",
    "#ff7b7b", "#a7c6ed", "#c1d64d", "#a1a1ce",
]


@st.cache_data
def load_all_data(file_path):
    """Load all 3 sheets and pre-process dates."""
    xls = pd.ExcelFile(file_path)

    def _load(name):
        return pd.read_excel(xls, sheet_name=name) if name in xls.sheet_names else pd.DataFrame()

    df_images = _load("images")
    df_videos = _load("videos")
    df_others = _load("others")

    for df in (df_images, df_videos):
        if "date_taken" in df.columns:
            df["date_taken"] = pd.to_datetime(df["date_taken"], errors="coerce")

    return df_images, df_videos, df_others


def _parse_shutter(s) -> float | None:
    if pd.isna(s): return None
    try:
        s_str = str(s).rstrip("s")
        if "/" in s_str:
            num, den = s_str.split("/")
            return float(num) / float(den)
        return float(s_str)
    except Exception: return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Configuration")
excel_file = st.sidebar.file_uploader("Select Excel Workbook (.xlsx)", type=["xlsx"])

if not excel_file:
    st.info("Upload a Gallery Inspector Excel workbook to get started.")
    st.stop()

# ── Load Data (Cached) ───────────────────────────────────────────────────────
df_images, df_videos, df_others = load_all_data(excel_file)

if df_images.empty and df_videos.empty and df_others.empty:
    st.error("No data found in the uploaded workbook.")
    st.stop()


# ── The Filtering + Viz Block (Fragmentized for performance) ──────────────────

@st.fragment
def main_app_block(df_images, df_videos, df_others):
    # ── Filters ───────────────────────────────────────────────────────────────
    st.header("Filters")

    # Date Range Slider (by Month/Year)
    date_mask = pd.Series(True, index=df_images.index)
    if "date_taken" in df_images.columns and not df_images["date_taken"].dropna().empty:
        df_dates = df_images[df_images["date_taken"].notna()]
        min_date = df_dates["date_taken"].min()
        max_date = df_dates["date_taken"].max()

        # Generate monthly periods
        periods = pd.period_range(start=min_date, end=max_date, freq="M")
        period_strs = [p.strftime("%b %Y") for p in periods]

        if len(period_strs) > 1:
            st.write("**Image Date Range**")
            selected_range = st.select_slider(
                "Select month/year range",
                options=period_strs,
                value=(period_strs[0], period_strs[-1]),
                label_visibility="collapsed"
            )

            # Map back to dates
            start_p = periods[period_strs.index(selected_range[0])]
            end_p = periods[period_strs.index(selected_range[1])]
            date_mask &= (df_images["date_taken"].dt.to_period("M") >= start_p) & \
                        (df_images["date_taken"].dt.to_period("M") <= end_p)
        else:
            st.write(f"Date: {min_date.strftime('%b %Y')}")

    col1, col2 = st.columns(2)

    cameras = sorted(df_images["camera"].dropna().unique()) if "camera" in df_images.columns else []
    selected_cameras = col1.multiselect("Camera Model", cameras, default=cameras)

    lenses = sorted(df_images["lens"].dropna().unique()) if "lens" in df_images.columns else []
    selected_lenses = col2.multiselect("Lens Model", lenses, default=lenses)

    # Apply all masks
    mask = date_mask
    if selected_cameras and "camera" in df_images.columns:
        mask &= df_images["camera"].isin(selected_cameras)
    if selected_lenses and "lens" in df_images.columns:
        mask &= df_images["lens"].isin(selected_lenses)

    fi = df_images[mask]
    fv = df_videos # Currently not filtered by date/camera, but could be unified if needed.

    # ── Summary Metrics ───────────────────────────────────────────────────────
    st.header("General Statistics")
    total_images, total_videos, total_others = len(fi), len(fv), len(df_others)
    total_files = total_images + total_videos + total_others
    total_size = sum(df["size (MB)"].sum() for df in (fi, fv, df_others) if "size (MB)" in df.columns)

    total_duration_sec = 0.0
    if "duration_ms" in fv.columns:
        total_duration_sec = fv["duration_ms"].sum(skipna=True) / 1000.0
    h, m, s = int(total_duration_sec // 3600), int((total_duration_sec % 3600) // 60), int(total_duration_sec % 60)

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total Files", f"{total_files:,}")
    mc2.metric("Filtered Images", f"{total_images:,}")
    mc3.metric("Videos", f"{total_videos:,}")
    mc4.metric("Total Size", f"{total_size:,.0f} MB")
    mc5.metric("Total Video Length", f"{h}h {m}m {s}s")

    # ── Data Tables ───────────────────────────────────────────────────────────
    st.header("Data")
    t1, t2, t3 = st.tabs([f"📷 Images ({len(fi):,})", f"🎬 Videos ({len(fv):,})", f"📄 Others ({len(df_others):,})"])
    with t1: st.dataframe(fi, use_container_width=True, height=300)
    with t2: st.dataframe(fv, use_container_width=True, height=300)
    with t3: st.dataframe(df_others, use_container_width=True, height=300)

    # ── Visualizations ────────────────────────────────────────────────────────
    st.header("Visualizations")

    # Row 1: Donut Charts
    dist_col1, dist_col2, dist_col3 = st.columns(3)
    with dist_col1:
        st.subheader("File Types")
        counts = {"Images": len(fi), "Videos": len(fv), "Others": len(df_others)}
        counts = {k: v for k, v in counts.items() if v > 0}
        if counts:
            fig = px.pie(names=list(counts.keys()), values=list(counts.values()),
                         color_discrete_sequence=["#66b3ff", "#99ff99", "#ff9999"], hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=300)
            st.plotly_chart(fig, use_container_width=True, key="pie_file")

    with dist_col2:
        st.subheader("Cameras")
        if "camera" in fi.columns and fi["camera"].dropna().any():
            cam_counts = fi["camera"].value_counts().nlargest(10).reset_index()
            cam_counts.columns = ["camera", "count"]
            fig = px.pie(cam_counts, names="camera", values="count", color_discrete_sequence=STACKED_COLORS, hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.5), height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True, key="pie_cam")

    with dist_col3:
        st.subheader("Lenses")
        if "lens" in fi.columns and fi["lens"].dropna().any():
            lens_counts = fi["lens"].value_counts().nlargest(10).reset_index()
            lens_counts.columns = ["lens", "count"]
            fig = px.pie(lens_counts, names="lens", values="count", color_discrete_sequence=STACKED_COLORS, hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.5), height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True, key="pie_lens")

    # Row 2: Settings (Reactive)
    st.subheader("Camera Settings Distribution")
    if not fi.empty:
        settings_available = [c for c in ("aperture", "shutter_speed", "iso", "focal_length") if c in fi.columns]
        if settings_available:
            fig = make_subplots(rows=2, cols=2, subplot_titles=["Aperture", "Shutter Speed", "ISO", "Focal Length"])
            STD_APERTURES = [1.2, 1.8, 2.2, 2.8, 3.5, 4.0, 5.6, 8, 11, 16, 22]
            STD_SHUTTERS = [1/4000, 1/2000, 1/1000, 1/500, 1/250, 1/125, 1/60, 1/30, 1/15, 1/8, 1/4, 1/2, 1, 2, 4, 8, 15, 30]
            STD_ISOS = [100, 200, 400, 800, 1600, 3200, 6400, 12800]
            STD_FOCALS = [14, 18, 24, 28, 35, 50, 70, 85, 105, 135, 200, 300, 400]

            def _log_hist(fig, series, row, col, color, tickvals, ticktext, name):
                data = pd.to_numeric(series, errors="coerce").dropna()
                data = data[(data > data.quantile(0.01)) & (data <= data.quantile(0.99)) & (data > 0)]
                if data.empty: return
                log_data = np.log10(data)
                fig.add_trace(go.Histogram(x=log_data, nbinsx=30, marker_color=color, opacity=0.7, name=name, showlegend=False), row=row, col=col)
                valid = [(v, t) for v, t in zip(tickvals, ticktext) if log_data.min()*0.9 <= np.log10(v) <= log_data.max()*1.1]
                if valid:
                    v_t, t_t = zip(*valid)
                    fig.update_xaxes(tickvals=[np.log10(v) for v in v_t], ticktext=list(t_t), row=row, col=col, tickangle=45)
                fig.update_yaxes(title_text="Count", row=row, col=col)

            _log_hist(fig, fi.get("aperture", pd.Series()), 1, 1, "coral", STD_APERTURES, [f"f{v:g}" for v in STD_APERTURES], "Aperture")
            ss = fi["shutter_speed"].apply(_parse_shutter) if "shutter_speed" in fi.columns else pd.Series()
            _log_hist(fig, ss, 1, 2, "orchid", STD_SHUTTERS, [f"1/{int(round(1/v))}" if v < 1 else f"{v:g}s" for v in STD_SHUTTERS], "Shutter")
            _log_hist(fig, fi.get("iso", pd.Series()), 2, 1, "gold", STD_ISOS, [str(v) for v in STD_ISOS], "ISO")
            _log_hist(fig, fi.get("focal_length", pd.Series()), 2, 2, "teal", STD_FOCALS, [f"{v}mm" for v in STD_FOCALS], "Focal Length")
            fig.update_layout(height=600, margin=dict(t=50, b=50))
            st.plotly_chart(fig, use_container_width=True, key="settings_hist")

    # Row 3: Timelines
    st.subheader("Photography Timeline")
    _stacked_timeline(fi, "camera", "month", "Monthly Photo Count by Camera")

    # Row 4: Video Timeline (Minutes per month)
    if not fv.empty and "date_taken" in fv.columns and "duration_ms" in fv.columns:
        st.subheader("Video Recording Summary")
        tmp_v = fv.copy()
        tmp_v["date_taken"] = pd.to_datetime(tmp_v["date_taken"], errors="coerce")
        tmp_v = tmp_v.dropna(subset=["date_taken"])
        if not tmp_v.empty:
            tmp_v["month"] = tmp_v["date_taken"].dt.to_period("M").astype(str)
            aggs = tmp_v.groupby("month")["duration_ms"].sum().reset_index()
            aggs["minutes"] = aggs["duration_ms"] / 60000.0
            fig = px.line(aggs, x="month", y="minutes", markers=True, title="Minutes Recorded per Month", color_discrete_sequence=["crimson"])
            fig.update_layout(xaxis_tickangle=45, yaxis_title="Duration (Minutes)")
            st.plotly_chart(fig, use_container_width=True, key="video_minutes")

    # Row 5: Map (Optimized)
    has_coords = not fi.empty and "latitude" in fi.columns and "longitude" in fi.columns and fi[["latitude","longitude"]].dropna().shape[0] > 0
    if has_coords:
        st.header("Photo Map")
        df_loc = fi[["latitude", "longitude", "camera", "date_taken", "name"]].copy()
        df_loc["latitude"] = pd.to_numeric(df_loc["latitude"], errors="coerce")
        df_loc["longitude"] = pd.to_numeric(df_loc["longitude"], errors="coerce")
        df_loc = df_loc.dropna(subset=["latitude", "longitude"])
        st.caption(f"Displaying {len(df_loc):,} geotagged photos")

        # Map combined: Heatmap + Scatter dots
        fig_map = px.density_mapbox(df_loc, lat="latitude", lon="longitude", radius=8,
                                    zoom=1, mapbox_style="carto-positron", color_continuous_scale="YlOrBr")

        # For performant scatter on maps with large data, we use go.Scattermapbox
        fig_map.add_trace(go.Scattermapbox(
            lat=df_loc["latitude"], lon=df_loc["longitude"], mode="markers",
            marker=dict(size=4, color="blue", opacity=0.3),
            text=df_loc["camera"] + " - " + df_loc["name"],
            hoverinfo="text", name="Photos", showlegend=False
        ))
        fig_map.update_layout(height=600, margin=dict(l=0, r=0, t=30, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_map, use_container_width=True, key="combined_map")


def _stacked_timeline(df: pd.DataFrame, group_by: str, time_by: str, title: str):
    if "date_taken" not in df.columns or group_by not in df.columns or df.empty: return
    tmp = df.copy()
    tmp["period"] = tmp["date_taken"].dt.year.astype(str) if time_by == "year" else tmp["date_taken"].dt.to_period("M").astype(str)
    tmp = tmp.dropna(subset=["period", group_by])
    top = tmp[group_by].value_counts().nlargest(10).index
    tmp[group_by] = tmp[group_by].where(tmp[group_by].isin(top), other="Other")
    pivot = tmp.groupby(["period", group_by]).size().reset_index(name="count")
    fig = px.bar(pivot, x="period", y="count", color=group_by, barmode="stack", color_discrete_sequence=STACKED_COLORS, title=title)
    fig.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig, use_container_width=True, key=f"timeline_{group_by}_{time_by}")


# ── Executing the Main Block ──────────────────────────────────────────────────
main_app_block(df_images, df_videos, df_others)
