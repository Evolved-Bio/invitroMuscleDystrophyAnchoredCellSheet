import pandas as pd
import matplotlib.pyplot as plt
import zipfile
from google.colab import files

def upload_file():
    print("Please upload your CSV file:")
    uploaded = files.upload()
    filename = next(iter(uploaded))
    return filename

def preprocess_data(filename):
    df = pd.read_csv(filename)
    df = df.drop(columns=['Alternate_ID', 'Identified_Proteins'])  # Drop unused identifier columns

    # Extract condition names and group by mean of replicates
    condition_names = df.columns[1:]  # assuming 'Accession_Number' is the first column
    conditions = {name.split('-')[0] for name in condition_names}
    condition_data = {cond: df.filter(regex=f'^{cond}').mean(axis=1) for cond in conditions}
    return condition_data, list(conditions)

def get_condition_pairs(conditions):
    pairs = []
    while True:
        print("Available conditions:", conditions)
        cond1 = input("Enter name of Condition 1 (or type 'done' to finish): ")
        if cond1.lower() == 'done':
            break
        cond2 = input("Enter name of Condition 2: ")
        if cond1 in conditions and cond2 in conditions:
            pairs.append((cond1, cond2))
        else:
            print("Invalid conditions entered. Please try again.")
    return pairs

def plot_conditions(condition_data, pairs):
    # Font size settings
    title_fontsize = 16
    label_fontsize = 14
    tick_fontsize = 12

    svg_files = []
    for cond1, cond2 in pairs:
        x = condition_data[cond1]
        y = condition_data[cond2]

        plt.figure(figsize=(6, 6))
        plt.scatter(x, y, alpha=0.6, edgecolors='w')
        plt.title(f'{cond1} vs {cond2}', fontsize=title_fontsize)
        plt.xlabel(f'{cond1} Mean Values', fontsize=label_fontsize)
        plt.ylabel(f'{cond2} Mean Values', fontsize=label_fontsize)
        plt.xticks(fontsize=tick_fontsize)
        plt.yticks(fontsize=tick_fontsize)
        plt.grid(True)

        file_name = f'{cond1}_vs_{cond2}_scatter.svg'
        plt.savefig(file_name, format='svg', bbox_inches='tight')
        plt.show()  # Display each plot as it is generated
        svg_files.append(file_name)

    return svg_files

def zip_and_download_files(svg_files):
    zip_filename = 'scatter_plots.zip'
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in svg_files:
            zipf.write(file)
    files.download(zip_filename)

def main():
    filename = upload_file()
    condition_data, conditions = preprocess_data(filename)
    pairs = get_condition_pairs(conditions)
    svg_files = plot_conditions(condition_data, pairs)
    zip_and_download_files(svg_files)

main()
