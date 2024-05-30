!pip install upsetplot

import pandas as pd
import numpy as np
from google.colab import files
import re
from sklearn.preprocessing import QuantileTransformer
from upsetplot import UpSet, from_contents
import matplotlib.pyplot as plt

# Step 1: Upload the CSV file
uploaded = files.upload()

# Step 2: Read the CSV file into a DataFrame
filename = list(uploaded.keys())[0]
df = pd.read_csv(filename, index_col=0)

# Step 3: Log10 transformation to stabilize variance
df = np.log10(df + 1)  # Adding 1 to avoid log(0) issues

# Step 4: Quantile normalization to make distributions comparable
scaler = QuantileTransformer(output_distribution='normal', random_state=0)
df_normalized = pd.DataFrame(scaler.fit_transform(df), index=df.index, columns=df.columns)

# Step 5: Calculate the mean values for columns with the same prefix (handling replicates)
column_groups = {}
for col in df_normalized.columns:
    prefix = re.split(r'-\d+', col)[0]  # Extract prefix before "-"
    if prefix in column_groups:
        column_groups[prefix].append(col)
    else:
        column_groups[prefix] = [col]

# Calculate mean for each group
mean_df = pd.DataFrame()
for prefix, columns in column_groups.items():
    mean_df[prefix] = df_normalized[columns].mean(axis=1)

# Step 6: Define control condition and calculate Z-scores for other conditions
control_condition = '3D,HC'
control_mean = mean_df[control_condition].mean()
control_std = mean_df[control_condition].std()

# Step 7: Categorize proteins based on Z-scores and prepare data for UpSet plot
upregulated_data = {}
downregulated_data = {}
significant_threshold = 1  # Z-score threshold for significance

for column in mean_df.columns:
    if column != control_condition:
        z_scores = (mean_df[column] - control_mean) / control_std
        upregulated_data[column] = set(mean_df.index[z_scores > significant_threshold])
        downregulated_data[column] = set(mean_df.index[z_scores < -significant_threshold])

# Step 8: Plot UpSet plots for proteins with increased and decreased expressions compared to control
def plot_upset(data, title, bar_color):
    if any(len(d) > 0 for d in data.values()):
        keys_sorted = sorted(data.keys())
        sorted_data = {key: data[key] for key in keys_sorted}
        upset_data = from_contents(sorted_data)
        upset_plot = UpSet(upset_data, show_counts='%d', element_size=50, sort_categories_by=None, sort_by='cardinality')
        axes = upset_plot.plot()
        for bar in axes['intersections'].patches:
            bar.set_facecolor(bar_color)  # Color the vertical bars
        plt.title(title, fontsize=title_fontsize)
        plt.xticks(fontsize=tick_fontsize)
        plt.yticks(fontsize=tick_fontsize)
        plt.xlabel('Conditions', fontsize=label_fontsize)
        plt.ylabel('Number of Proteins', fontsize=label_fontsize)
        plt.show()
    else:
        print(f"No significant {title.lower()} found.")

# Font size settings
title_fontsize = 20
label_fontsize = 18
tick_fontsize = 16

plot_upset(upregulated_data, 'General Increase in Expression Relative to Control', 'darkred')
plot_upset(downregulated_data, 'General Decrease in Expression Relative to Control', 'darkblue')
