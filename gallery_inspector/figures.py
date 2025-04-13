import pandas as pd
import matplotlib.pyplot as plt


def plot_weekly_lens_usage(df: pd.DataFrame,
                           date_column: str = 'DateTime',
                           lens_column: str = 'LensModel',
                           date_format: str = '%Y:%m:%d %H:%M:%S'):
    df[date_column] = pd.to_datetime(df[date_column], format=date_format, errors='coerce')
    df = df.dropna(subset=[date_column, lens_column])
    df['Month'] = df[date_column].dt.to_period('M').apply(lambda r: r.start_time)
    monthly_counts = df.groupby(['Month', lens_column]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(14, 8))
    monthly_counts_cumsum = monthly_counts.cumsum(axis=1)
    for i, lens in enumerate(monthly_counts.columns):
        ax.bar(monthly_counts.index, monthly_counts[lens],
               width=15,
               bottom=monthly_counts_cumsum[lens] - monthly_counts[lens],
               label=lens)
    ax.set_title('Monthly Number of Pictures Taken by Lens Model')
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Pictures')
    ax.spines[['right', 'top']].set_visible(False)
    ax.legend(title='Lens Model', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()
