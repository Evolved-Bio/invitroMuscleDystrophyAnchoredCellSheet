import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from google.colab import files
import os
from scipy.stats import ttest_ind, mannwhitneyu, shapiro, levene
from statsmodels.stats.multitest import multipletests
from matplotlib.ticker import FixedFormatter

def upload_files():
    print("Uploading files...")
    return files.upload()

def create_combined_violin_plot(dfs, names, figsize=(12, 5)):
    plt.figure(figsize=figsize)
    all_differences = []
    all_comparisons = []

    for df, name in zip(dfs, names):
        log2_fold_changes = df['Difference']
        all_differences.extend(log2_fold_changes)
        all_comparisons.extend([name] * len(df))

    formatted_comparisons = [name.replace(' vs ', '\nvs\n').replace(' ', '\n') for name in all_comparisons]

    combined_df = pd.DataFrame({
        'Comparison': formatted_comparisons,
        'Log2 Fold Change': all_differences
    })

    sns.violinplot(x='Comparison', y='Log2 Fold Change', data=combined_df, palette='Set2', inner=None)
    plt.xticks(rotation=0, ha='center', fontsize=12)
    plt.yticks([-40, -20, 0, 20, 40], fontsize=12)
    plt.ylabel('Log2 Fold Change', fontsize=14)
    plt.xlabel('', fontsize=14)
    plt.title('Violin Plot', fontsize=16)
    plt.grid(True)
    plt.tight_layout()

    plot_path = 'Combined_Violin_Plot.svg'
    plt.savefig(plot_path)
    plt.show()

    return combined_df, plot_path

def perform_statistical_analysis(dfs, names):
    results = []
    for i in range(len(dfs)):
        for j in range(i + 1, len(dfs)):
            differences_i = dfs[i]['Difference']
            differences_j = dfs[j]['Difference']

            # Normality tests
            stat_i, p_value_i = shapiro(differences_i)
            stat_j, p_value_j = shapiro(differences_j)
            normal_i = p_value_i > 0.05
            normal_j = p_value_j > 0.05

            # Variance homogeneity test
            stat, p_value_levene = levene(differences_i, differences_j)
            equal_var = p_value_levene > 0.05

            # Decide which test to use
            if normal_i and normal_j and equal_var:
                t_stat, p_value = ttest_ind(differences_i, differences_j, equal_var=True)
                test_used = 't-test'
            elif normal_i and normal_j:
                t_stat, p_value = ttest_ind(differences_i, differences_j, equal_var=False)
                test_used = 'Welch\'s t-test'
            else:
                u_stat, p_value = mannwhitneyu(differences_i, differences_j)
                test_used = 'Mann-Whitney U'

            results.append({
                'Comparison 1': names[i],
                'Comparison 2': names[j],
                'Test Used': test_used,
                't Statistic': t_stat if test_used != 'Mann-Whitney U' else 'N/A',
                'U Statistic': u_stat if test_used == 'Mann-Whitney U' else 'N/A',
                'p-value': p_value
            })

    results_df = pd.DataFrame(results)

    # Multiple testing correction
    corrected_pvals = multipletests(results_df['p-value'], method='fdr_bh')[1]
    results_df['Adjusted p-value'] = corrected_pvals

    return results_df

def create_statistical_dot_plot(stats_df, figsize=(10, 8), dot_size=(20, 200), font_size=12):
    plt.figure(figsize=figsize)
    stats_df['-log10(p-value)'] = -np.log10(stats_df['Adjusted p-value'])

    # Modify labels to be displayed in multiple lines
    stats_df['Comparison 1'] = stats_df['Comparison 1'].str.replace(' vs ', '\nvs\n').str.replace(' ', '\n')
    stats_df['Comparison 2'] = stats_df['Comparison 2'].str.replace(' vs ', '\nvs\n').str.replace(' ', '\n')

    # Create dot plot
    ax = sns.scatterplot(data=stats_df, x='Comparison 1', y='Comparison 2', size='-log10(p-value)', hue='-log10(p-value)', palette='viridis', sizes=dot_size)
    plt.title('Dot Plot of Adjusted p-values for Pairwise Comparisons', fontsize=font_size + 2)
    plt.xticks(rotation=0, ha='center', fontsize=font_size)
    ax.yaxis.set_major_formatter(FixedFormatter(ax.get_yticklabels()))
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, ha='right', fontsize=font_size, rotation_mode='anchor')
    plt.xlabel('Comparison 1', fontsize=font_size)
    plt.ylabel('Comparison 2', fontsize=font_size)
    plt.tight_layout()

    dot_plot_path = 'Statistical_Dot_Plot.svg'
    plt.savefig(dot_plot_path)
    plt.show()

    return dot_plot_path

def process_files(uploaded_files, figsize=(12, 5), dot_size=(20, 200), font_size=12):
    dfs = []
    names = []
    for filename, content in uploaded_files.items():
        try:
            with open(filename, 'wb') as f:
                f.write(content)
            df = pd.read_csv(filename)
            if 'Difference' not in df.columns:
                raise ValueError(f"File {filename} does not contain 'Difference' column.")
            base_name = filename.split('.')[0]
            dfs.append(df)
            names.append(base_name)
            os.remove(filename)
        except Exception as e:
            print(f"Error processing file {filename}: {e}")

    if not dfs:
        print("No valid files to process.")
        return

    stats_df = perform_statistical_analysis(dfs, names)
    stats_file_path = 'statistical_analysis_results.csv'
    stats_df.to_csv(stats_file_path, index=False)
    files.download(stats_file_path)

    combined_df, plot_path = create_combined_violin_plot(dfs, names, figsize)
    dot_plot_path = create_statistical_dot_plot(stats_df, figsize=(10, 8), dot_size=dot_size, font_size=font_size)

    files.download(plot_path)
    files.download(dot_plot_path)

def main():
    uploaded_files = upload_files()
    process_files(uploaded_files, figsize=(12, 5), dot_size=(50, 500), font_size=14)

main()
