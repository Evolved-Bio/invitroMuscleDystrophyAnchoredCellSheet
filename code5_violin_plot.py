import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from google.colab import files
import os


def upload_files():
    print("Uploading files...")
    return files.upload()


def create_combined_volcano_plot(dfs, names, figsize=(12, 5)):
    plt.figure(figsize=figsize)
    all_differences = []
    all_comparisons = []

    for df, name in zip(dfs, names):
        # Use the 'Difference' column directly as log2 fold changes
        log2_fold_changes = df['Difference']
        all_differences.extend(log2_fold_changes)
        all_comparisons.extend([name] * len(df))

    # Replace spaces with newlines in comparison names
    formatted_comparisons = [name.replace(' vs ', '\nvs\n').replace(' ', '\n') for name in all_comparisons]

    combined_df = pd.DataFrame({
        'Comparison': formatted_comparisons,
        'Log2 Fold Change': all_differences
    })

    sns.violinplot(x='Comparison', y='Log2 Fold Change', data=combined_df, palette='Set2', inner=None)  # Remove inner points
    plt.xticks(rotation=0, ha='center', fontsize=12)  # Set the names on the x-axis with proper alignment
    plt.yticks([-40, -20, 0, 20, 40], fontsize=12)
    plt.ylabel('Log2 Fold Change', fontsize=14)
    plt.xlabel('', fontsize=14)
    plt.title('Violin Plot', fontsize=16)
    plt.grid(True)
    plt.tight_layout()  # Adjust layout to make room for the x-axis labels
    plot_path = 'Combined_Volcano_Plot.svg'
    plt.savefig(plot_path)
    plt.show()
    return plot_path

def process_files(uploaded_files, figsize=(12, 5)):
    dfs = []
    names = []
    for filename, content in uploaded_files.items():
        with open(filename, 'wb') as f:
            f.write(content)
        df = pd.read_csv(filename)
        base_name = filename.split('.')[0]  # Use the filename without extension as the comparison name
        dfs.append(df)
        names.append(base_name)
        os.remove(filename)

    plot_path = create_combined_volcano_plot(dfs, names, figsize)
    files.download(plot_path)

def main():
    uploaded_files = upload_files()
    process_files(uploaded_files, figsize=(12, 5))

main()
