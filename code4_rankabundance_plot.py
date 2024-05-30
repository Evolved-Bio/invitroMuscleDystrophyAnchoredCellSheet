import pandas as pd
from google.colab import files
import re
import matplotlib.pyplot as plt
import numpy as np
import os

def upload_files():
    print("Please upload your CSV files:")
    uploaded = files.upload()
    return uploaded.keys()

def process_data(filename):
    df = pd.read_csv(filename, index_col=0)
    # Extract unique prefixes and group columns accordingly
    column_groups = {}
    for col in df.columns:
        prefix = re.split(r'-\d+', col)[0]  # Extract prefix before "-"
        if prefix in column_groups:
            column_groups[prefix].append(col)
        else:
            column_groups[prefix] = [col]
    return df, column_groups

def plot_rank_abundance(df, column_groups, filename):
    plt.figure(figsize=(5.5, 5))  # plot format
    # Define a custom set of colors, adjusting as needed
    custom_colors = ['#1f77b4', '#ffdf01', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    colors = custom_colors[:len(column_groups)]  # Adjust number of colors based on number of conditions
    for (prefix, columns), color in zip(column_groups.items(), colors):
        # Calculate median for each protein within the condition
        condition_data = df[columns].median(axis=1).sort_values(ascending=False)
        # Log transform and plot
        plt.scatter(range(1, len(condition_data) + 1), np.log10(condition_data), label=prefix, color=color, alpha=0.6, edgecolors='none')

    plt.title(f'Rank-Abundance Plot for {filename}', fontsize=10)
    plt.xlabel('Rank', fontsize=9)
    plt.ylabel('log2(Median Protein Abundance)', fontsize=9)
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    plt.legend(title="", fontsize=8)
    plt.grid(True)
    plt.tight_layout()
    plot_path = f'Rank_Abundance_Plot_{filename}.svg'
    plt.savefig(plot_path)
    plt.show()
    return plot_path

def main():
    filenames = upload_files()
    for filename in filenames:
        df, column_groups = process_data(filename)
        plot_path = plot_rank_abundance(df, column_groups, filename)
        files.download(plot_path)

main()
