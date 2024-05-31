import pandas as pd
from google.colab import files
import re
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.stats import entropy

def upload_files():
    """Prompt user to upload CSV files and return the list of filenames."""
    print("Please upload your CSV files:")
    uploaded = files.upload()
    return uploaded.keys()

def process_data(filename):
    """Read the CSV file, extract condition groups based on column names."""
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

def calculate_shannon_diversity(df, column_groups):
    """Calculate Shannon Diversity Index for each condition."""
    shannon_diversity = {}
    for prefix, columns in column_groups.items():
        condition_data = df[columns].mean(axis=1)
        condition_data = condition_data[condition_data > 0]  # Remove zero values to avoid log(0)
        if len(condition_data) > 0:
            proportions = condition_data / condition_data.sum()
            shannon_diversity[prefix] = entropy(proportions)
        else:
            shannon_diversity[prefix] = 0  # If all values are zero, set Shannon diversity to 0
    return shannon_diversity

def plot_log_transformed_histogram(df, column_groups, filename):
    """Plot log-transformed abundance histograms for each condition."""
    fig, axes = plt.subplots(len(column_groups), 1, figsize=(10, 8))
    fig.suptitle(f'Log-Transformed Abundance Histograms for {filename}', fontsize=12)

    if len(column_groups) == 1:
        axes = [axes]

    for ax, (prefix, columns) in zip(axes, column_groups.items()):
        condition_data = df[columns].mean(axis=1)
        log_transformed_data = np.log10(condition_data[condition_data > 0])
        ax.hist(log_transformed_data, bins=30, alpha=0.7, color='blue')
        ax.set_title(f'{prefix}', fontsize=10)
        ax.set_xlabel('log10(Protein Abundance)', fontsize=9)
        ax.set_ylabel('Frequency', fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    hist_path = f'Log_Transformed_Histogram_{filename}.svg'
    plt.savefig(hist_path)
    plt.show()

    return hist_path

def plot_combined_with_heatmap(df, column_groups, shannon_diversity, filename):
    """Plot rank-abundance plot combined with Shannon Diversity Index heatmap."""
    fig, ax1 = plt.subplots(figsize=(10, 8))  # Combined plot format

    # Rank-Abundance Plot
    custom_colors = ['#1f77b4', '#ffdf01', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    colors = custom_colors[:len(column_groups)]  # Adjust number of colors based on number of conditions
    for (prefix, columns), color in zip(column_groups.items(), colors):
        condition_data = df[columns].mean(axis=1).sort_values(ascending=False)
        condition_data = condition_data[condition_data > 0]  # Remove zero values to avoid log(0)
        ax1.scatter(range(1, len(condition_data) + 1), np.log10(condition_data), label=prefix, color=color, alpha=0.6, edgecolors='none')
    ax1.set_title(f'Rank-Abundance Plot for {filename}', fontsize=12)
    ax1.set_xlabel('Rank', fontsize=10)
    ax1.set_ylabel('log10(Mean Protein Abundance)', fontsize=10)
    ax1.legend(title="Condition", fontsize=9)
    ax1.grid(True)

    # Normalize Shannon Diversity Index for color mapping
    norm = plt.Normalize(min(shannon_diversity.values()), max(shannon_diversity.values()))

    # Create a color bar based on Shannon Diversity Index
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax1, orientation="vertical", pad=0.02)
    cbar.set_label('Shannon Diversity Index', fontsize=10)

    # Add colored ticks to represent Shannon Diversity Index
    for idx, (prefix, value) in enumerate(shannon_diversity.items()):
        color = sm.to_rgba(value)
        ax1.text(len(df) + 5, idx + 1, f"{prefix}\n{value:.2f}", color=color, ha='left', fontsize=9, va='center')

    plt.tight_layout(rect=[0, 0, 0.85, 1])  # Adjust the layout to make room for the color bar and text
    combined_plot_path = f'Combined_Plot_with_Heatmap_{filename}.svg'
    plt.savefig(combined_plot_path)
    plt.show()

    return combined_plot_path

def save_shannon_diversity(shannon_diversity, filename):
    """Save Shannon Diversity Index to a CSV file."""
    diversity_df = pd.DataFrame(list(shannon_diversity.items()), columns=['Condition', 'Shannon Diversity Index'])
    diversity_path = f'Shannon_Diversity_{filename}.csv'
    diversity_df.to_csv(diversity_path, index=False)
    return diversity_path

def main():
    """Main function to handle file upload, processing, and plotting."""
    filenames = upload_files()
    for filename in filenames:
        df, column_groups = process_data(filename)

        # Plot log-transformed histograms to check log-normal distribution assumption
        hist_path = plot_log_transformed_histogram(df, column_groups, filename)
        files.download(hist_path)

        # Calculate Shannon Diversity
        shannon_diversity = calculate_shannon_diversity(df, column_groups)

        # Plot combined figure with heatmap
        combined_plot_path = plot_combined_with_heatmap(df, column_groups, shannon_diversity, filename)
        files.download(combined_plot_path)

        # Save Shannon Diversity Index
        diversity_path = save_shannon_diversity(shannon_diversity, filename)
        files.download(diversity_path)

main()
