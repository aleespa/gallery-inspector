import sys
from pathlib import Path
import pandas as pd
import flet as ft

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from gallery_inspector.generate import generate_images_table

def main(page: ft.Page):
    page.title = "Gallery Inspector"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # State
    df = None

    # UI Elements
    txt_source_dir = ft.TextField(
        label="Source Directory", 
        expand=True
    )
    
    chart_container = ft.Container(expand=True)

    def process_data_for_chart(df: pd.DataFrame, variable: str = 'LensModel'):
        # Copy logic from plot_interactive_timeline but adapt for Flet Chart
        df = df.copy()
        date_column = 'DateTimeOriginal'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        df[date_column] = pd.to_datetime(df[date_column], format=date_format, errors='coerce')
        df[variable] = df[variable].replace("", pd.NA)
        df = df.dropna(subset=[date_column, variable])
        df['Month'] = df[date_column].dt.to_period('M').apply(lambda r: r.start_time)
        
        # Group by Month and Variable to get counts
        monthly_counts = df.groupby(['Month', variable]).size().reset_index(name='Count')
        
        return monthly_counts

    def create_flet_bar_chart(data: pd.DataFrame, variable: str):
        # Get unique groups (e.g., Lens Models) for coloring/stacking
        groups = data[variable].unique()
        months = sorted(data['Month'].unique())
        
        # Create a color map
        colors = [
            ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN, ft.Colors.ORANGE, 
            ft.Colors.PURPLE, ft.Colors.CYAN, ft.Colors.PINK, ft.Colors.TEAL,
            ft.Colors.AMBER, ft.Colors.INDIGO
        ]
        color_map = {group: colors[i % len(colors)] for i, group in enumerate(groups)}
        
        bar_groups = []
        
        for i, month in enumerate(months):
            month_data = data[data['Month'] == month]
            rods = []
            
            for _, row in month_data.iterrows():
                group_name = row[variable]
                count = row['Count']
                
                rods.append(
                    ft.BarChartRod(
                        to_y=count,
                        color=color_map.get(group_name, ft.Colors.GREY),
                        tooltip=f"{group_name}: {count}",
                        width=20,
                        border_radius=0
                    )
                )
            
            bar_groups.append(
                ft.BarChartGroup(
                    x=i,
                    bar_rods=rods,
                )
            )

        # X-Axis Labels (simplify to show every Nth label to avoid crowding)
        step = max(1, len(months) // 10)
        bottom_axis = ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=i, 
                    label=ft.Text(month.strftime("%Y-%m"), size=10, rotate=ft.Rotate(angle=-0.5))
                )
                for i, month in enumerate(months) if i % step == 0
            ],
        )

        chart = ft.BarChart(
            bar_groups=bar_groups,
            bottom_axis=bottom_axis,
            left_axis=ft.ChartAxis(labels_size=40),
            border=ft.border.all(1, ft.Colors.GREY_800),
            horizontal_grid_lines=ft.ChartGridLines(
                color=ft.Colors.GREY_800, width=1, dash_pattern=[3, 3]
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.GREY_900),
            max_y=data.groupby('Month')['Count'].sum().max() * 1.1, # Add some headroom
            interactive=True,
            expand=True
        )
        
        return chart

    def on_analyze_click(e):
        nonlocal df
        path_str = txt_source_dir.value
        if not path_str:
            page.open(ft.SnackBar(ft.Text("Please enter a directory path")))
            return

        path = Path(path_str)
        if not path.exists() or not path.is_dir():
            page.open(ft.SnackBar(ft.Text("Invalid directory path")))
            return

        page.open(ft.SnackBar(ft.Text("Analyzing directory...")))
        btn_analyze.disabled = True
        page.update()

        try:
            # Generate Data
            df = generate_images_table(path)
            
            # Filter for images only
            images_df = df[df['media_type'] == 'image']
            
            if not images_df.empty:
                # Process data for Flet Chart
                chart_data = process_data_for_chart(images_df, variable='LensModel')
                
                if not chart_data.empty:
                    chart = create_flet_bar_chart(chart_data, variable='LensModel')
                    chart_container.content = ft.Container(
                        content=chart,
                        padding=20,
                        expand=True
                    )
                    page.open(ft.SnackBar(ft.Text(f"Analysis complete. Found {len(images_df)} images.")))
                else:
                    chart_container.content = ft.Text("No data available for plotting.")
            else:
                chart_container.content = ft.Text("No images found in directory.")
                
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error: {ex}")))
            print(ex) # Print to console for debugging
        finally:
            btn_analyze.disabled = False
            page.update()

    btn_analyze = ft.ElevatedButton(
        "Analyze", 
        on_click=on_analyze_click
    )

    # Layout
    page.add(
        ft.Row(
            [
                txt_source_dir,
                btn_analyze
            ],
            alignment=ft.MainAxisAlignment.CENTER
        ),
        ft.Divider(),
        chart_container
    )

if __name__ == "__main__":
    ft.app(target=main)
