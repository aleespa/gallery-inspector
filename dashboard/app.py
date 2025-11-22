import sys
from pathlib import Path

# Add project root to sys.path to allow importing gallery_inspector
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import streamlit as st
import pandas as pd
from gallery_inspector.generate import generate_images_table, generated_directory, generated_directory_from_list
from gallery_inspector.figures import plot_interactive_timeline, plot_sunburst, plot_scatter, plot_file_types, plot_size_distribution

@st.cache_data
def cached_generate_images_table(path: Path) -> pd.DataFrame:
    return generate_images_table(path)

st.set_page_config(page_title="Gallery Inspector", layout="wide")

st.title("Gallery Inspector Dashboard")

# Sidebar
st.sidebar.header("Configuration")
source_dir = st.sidebar.text_input("Source Directory", value="")
analyze_btn = st.sidebar.button("Analyze")
if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()

if analyze_btn and source_dir:
    path = Path(source_dir)
    if not path.exists() or not path.is_dir():
        st.error("Invalid directory path.")
    else:
        with st.spinner("Analyzing directory..."):
            try:
                df = cached_generate_images_table(path)
                st.session_state['df'] = df
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Error during analysis: {e}")

if 'df' in st.session_state:
    df = st.session_state['df']
    
    # General Statistics
    st.header("General Statistics")
    
    total_files = len(df)
    total_images = len(df[df['media_type'] == 'image'])
    total_videos = len(df[df['media_type'] == 'video'])
    total_size_mb = df['size (MB)'].sum()
    
    total_duration_sec = 0
    if 'Duration' in df.columns:
        total_duration_sec = df['Duration'].sum() / 1000  # Duration is usually in ms
    
    hours = int(total_duration_sec // 3600)
    minutes = int((total_duration_sec % 3600) // 60)
    seconds = int(total_duration_sec % 60)
    duration_str = f"{hours}h {minutes}m {seconds}s"
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Files", f"{total_files:,}")
    c2.metric("Images", f"{total_images:,}")
    c3.metric("Videos", f"{total_videos:,}")
    c4.metric("Total Size", f"{total_size_mb:,.0f} MB")
    c5.metric("Total Video Length", duration_str)

    # Advanced Metrics
    st.subheader("Advanced Metrics")
    ac1, ac2, ac3 = st.columns(3)
    
    avg_size = df['size (MB)'].mean()
    ac1.metric("Average File Size", f"{avg_size:.2f} MB")
    
    if 'Model' in df.columns:
        top_camera = df['Model'].mode()
        top_camera_str = top_camera[0] if not top_camera.empty else "N/A"
        ac2.metric("Most Common Camera", top_camera_str)
        
    if 'LensModel' in df.columns:
        top_lens = df['LensModel'].mode()
        top_lens_str = top_lens[0] if not top_lens.empty else "N/A"
        ac3.metric("Most Common Lens", top_lens_str)

    # Filters
    st.header("Data Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    # Date Filter
    min_date = None
    max_date = None
    date_range = []
    
    if 'DateTimeOriginal' in df.columns:
        min_date = df['DateTimeOriginal'].min()
        max_date = df['DateTimeOriginal'].max()
        
        if pd.notnull(min_date) and pd.notnull(max_date):
            date_range = col1.date_input("Date Range", [min_date, max_date])
    
    # Camera Filter
    cameras = df['Model'].dropna().unique().tolist() if 'Model' in df.columns else []
    selected_cameras = col2.multiselect("Camera Model", cameras, default=cameras)
    
    # Lens Filter
    lenses = df['LensModel'].dropna().unique().tolist() if 'LensModel' in df.columns else []
    selected_lenses = col3.multiselect("Lens Model", lenses, default=lenses)
    
    # Apply Filters
    mask = pd.Series(True, index=df.index)
    
    if 'DateTimeOriginal' in df.columns and pd.notnull(min_date) and pd.notnull(max_date) and len(date_range) == 2:
         mask &= (df['DateTimeOriginal'].dt.date >= date_range[0]) & (df['DateTimeOriginal'].dt.date <= date_range[1])
    
    if 'Model' in df.columns and selected_cameras:
        mask &= df['Model'].isin(selected_cameras)
        
    if 'LensModel' in df.columns and selected_lenses:
        mask &= df['LensModel'].isin(selected_lenses)
        
    filtered_df = df[mask]
    
    st.dataframe(filtered_df)
    
    # Plotting
    st.subheader("Interactive Timeline (Images)")
    # Filter for images for this plot to keep it relevant to camera/lens variables
    images_df = filtered_df[filtered_df['media_type'] == 'image']
    
    plot_cols = [c for c in ['LensModel', 'Model', 'FNumber', 'ISOSpeedRatings'] if c in images_df.columns]
    if plot_cols and not images_df.empty:
        variable_to_plot = st.selectbox("Variable to Group By", plot_cols)
        
        if variable_to_plot:
            fig = plot_interactive_timeline(images_df, variable=variable_to_plot)
            st.plotly_chart(fig, use_container_width=True)
    elif images_df.empty:
        st.info("No images found in the current selection.")
    else:
        st.info("No suitable columns found for plotting images.")

    # Video Plotting
    videos_df = filtered_df[filtered_df['media_type'] == 'video']
    if not videos_df.empty:
        st.subheader("Video Timeline")
        # For videos, we just want to see the count over time, so we can group by 'media_type' (which is all 'video')
        # or just pass a dummy variable if needed. But plot_interactive_timeline expects a variable to group/color by.
        # We can use 'media_type' as the variable.
        fig_video = plot_interactive_timeline(videos_df, variable='media_type')
        st.plotly_chart(fig_video, use_container_width=True)

    # New Plots
    st.header("Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Directory Size Distribution")
        fig_sunburst = plot_sunburst(filtered_df)
        if fig_sunburst:
            st.plotly_chart(fig_sunburst, use_container_width=True)
        else:
            st.info("Not enough data for Sunburst chart.")

        st.subheader("File Size Distribution")
        fig_size = plot_size_distribution(filtered_df)
        st.plotly_chart(fig_size, use_container_width=True)


            
    with col2:
        st.subheader("File Type Distribution")
        fig_types = plot_file_types(filtered_df)
        st.plotly_chart(fig_types, use_container_width=True)


        st.subheader("Exposure Triangle (ISO vs Shutter Speed)")
        if 'ISOSpeedRatings' in filtered_df.columns and 'ExposureTime' in filtered_df.columns:
            fig_scatter = plot_scatter(filtered_df, x='ISOSpeedRatings', y='ExposureTime', color='Model' if 'Model' in filtered_df.columns else None)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("ISO or Exposure Time data missing.")



    # Organization
    st.header("Organize Files")
    st.markdown("Organize files from the filtered list into a new directory structure.")
    
    with st.expander("Organization Settings"):
        output_dir = st.text_input("Output Directory")
        by_media_type = st.checkbox("Separate by Media Type (Photos/Videos)", value=True)
        
        # Arguments for generated_directory (it takes *args for metadata fields to use in folder structure)
        # Based on _process_single_file logic: target_dir / val1 / val2 ...
        available_fields = ['Year', 'Month', 'Model', 'Lens'] # These seem to be the keys returned by _get_image_metadata
        selected_structure = st.multiselect("Folder Structure (Order matters)", available_fields, default=['Year', 'Month'])
        
        on_exist = st.radio("If file exists", ['rename', 'skip'], index=0)
        
        organize_btn = st.button("Start Organization")
        
        if organize_btn:
            if not output_dir:
                st.error("Please specify an output directory.")
            else:
                out_path = Path(output_dir)
                # We need to pass the filtered files to the organization function.
                # generated_directory iterates over input_path. 
                # generated_directory_from_list iterates over a list of files.
                # I should check if generated_directory_from_list exists in generate.py
                
                # Let's check generate.py content again to be sure about generated_directory_from_list
                # It was in the file view earlier: line 211 def generated_directory_from_list
                
                files_to_process = [Path(row['directory']) / row['name'] for _, row in filtered_df.iterrows()]
                
                if not files_to_process:
                    st.warning("No files to process.")
                else:
                    with st.spinner(f"Organizing {len(files_to_process)} files..."):
                        try:
                            # generated_directory_from_list(files, output, by_media_type, *args, verbose, on_exist)
                            generated_directory_from_list(
                                files_to_process,
                                out_path,
                                by_media_type,
                                *selected_structure,
                                verbose=True,
                                on_exist=on_exist
                            )
                            st.success(f"Successfully organized {len(files_to_process)} files to {out_path}")
                        except Exception as e:
                            st.error(f"Error during organization: {e}")
