import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from google.colab import files
import zipfile
import os


def upload_files():
    print("Uploading files...")
    return files.upload()


def create_volcano_plot(df, base_name, title_fontsize=16, label_fontsize=14, tick_fontsize=12):
    plt.figure(figsize=(10, 6))
    filtered_df = df.dropna(subset=['LogPvalue', 'Difference'])

    # Define significance thresholds
    p_value_threshold = -np.log10(0.01)  # Corresponds to p-value < 0.01
    fold_change_threshold = 10  # Usually log2 fold change > 1 is significant, adjust as needed

    # Adjusting colors based on significance criteria
    colors = ['red' if y > p_value_threshold and x > fold_change_threshold else
              'blue' if y > p_value_threshold and x < -fold_change_threshold else
              'grey' for x, y in zip(filtered_df['Difference'], filtered_df['LogPvalue'])]

    plt.scatter(filtered_df['Difference'], filtered_df['LogPvalue'], c=colors, alpha=0.5)
    plt.title(f'Volcano Plot for {base_name}', fontsize=title_fontsize)
    plt.xlabel('Difference', fontsize=label_fontsize)
    plt.ylabel('Log P-value', fontsize=label_fontsize)
    plt.axhline(y=p_value_threshold, color='red', linestyle='--')  # p-value threshold
    plt.axvline(x=0, color='black', linestyle='--')  # zero change line, indicating no fold change
    plt.grid(True)
    plt.xticks(fontsize=tick_fontsize)
    plt.yticks(fontsize=tick_fontsize)
    plot_path = f'{base_name}_Volcano.svg'
    plt.savefig(plot_path)
    plt.show()
    return plot_path


def save_significant_proteins(df, base_name):
    p_value_threshold = -np.log10(0.01)  # Corresponds to p-value < 0.01
    fold_change_threshold = 10  # Usually log2 fold change > 1 is significant, adjust as needed

    upregulated = df[(df['LogPvalue'] > p_value_threshold) & (df['Difference'] > fold_change_threshold)]['Accession_Number'].reset_index(drop=True)
    downregulated = df[(df['LogPvalue'] > p_value_threshold) & (df['Difference'] < -fold_change_threshold)]['Accession_Number'].reset_index(drop=True)

    max_length = max(len(upregulated), len(downregulated))
    upregulated = upregulated.reindex(range(max_length))
    downregulated = downregulated.reindex(range(max_length))

    significant_df = pd.DataFrame({
        'Upregulated': upregulated,
        'Downregulated': downregulated
    })
    sig_csv_name = f'{base_name}_Significant_Proteins.csv'
    significant_df.to_csv(sig_csv_name, index=False)
    return sig_csv_name


def zip_files(base_name, files_to_zip):
    zip_path = f'{base_name}_Files.zip'
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file)
    return zip_path


def process_files(uploaded_files, title_fontsize=16, label_fontsize=14, tick_fontsize=12):
    for filename, content in uploaded_files.items():
        with open(filename, 'wb') as f:
            f.write(content)
        df = pd.read_csv(filename)
        base_name = os.path.splitext(filename)[0]
        plot_path = create_volcano_plot(df, base_name, title_fontsize, label_fontsize, tick_fontsize)
        sig_csv_name = save_significant_proteins(df, base_name)
        zip_path = zip_files(base_name, [plot_path, sig_csv_name])
        files.download(zip_path)
        os.remove(filename)
        os.remove(plot_path)
        os.remove(sig_csv_name)


def main():
    uploaded_files = upload_files()
    # Adjust the font sizes here as needed
    title_fontsize = 20
    label_fontsize = 18
    tick_fontsize = 16
    process_files(uploaded_files, title_fontsize, label_fontsize, tick_fontsize)


main()
