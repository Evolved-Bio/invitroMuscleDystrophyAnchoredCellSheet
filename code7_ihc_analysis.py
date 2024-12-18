# Step 1: Loading Files and Extracting Metadata

import os
import re
import pandas as pd
from google.colab import files
from PIL import Image
import matplotlib.pyplot as plt
from IPython.display import display
import io
import numpy as np

def upload_files():
    uploaded = files.upload()
    if not uploaded:
        raise ValueError("No files uploaded!")
    return uploaded

def extract_metadata(filename):
    pattern = r'([^-]+)-([^-]+)-(\d+)'
    match = re.match(pattern, os.path.splitext(filename)[0])
    if match:
        condition, staining, replicate = match.groups()
        return condition, staining, replicate
    else:
        print(f"Filename format error: {filename}")
        return (None,) * 3

def process_image(file_data, filename):
    condition, staining, replicate = extract_metadata(filename)
    if condition is None:
        return None, None

    try:
        image = Image.open(io.BytesIO(file_data))
        display_image = image.copy()
        display_image.thumbnail((800, 800))

        # Create 'Original-Images' folder and save the image
        os.makedirs('/content/Original-Images', exist_ok=True)
        file_path = f"/content/Original-Images/{filename}"
        image.save(file_path)

        return display_image, {
            'Filename': filename,
            'FilePath': file_path,
            'Condition': condition,
            'Staining': staining,
            'Replicate': replicate,
            'Format': image.format,
            'OriginalSize': image.size
        }
    except IOError:
        print(f"Error opening image file: {filename}")
        return None, None

def display_representative_images(images, metadata_list):
    grouped_images = {}
    for image, metadata in zip(images, metadata_list):
        key = (metadata['Condition'], metadata['Staining'])
        if key not in grouped_images:
            grouped_images[key] = (image, metadata)

    sorted_data = sorted(grouped_images.values(), key=lambda x: (x[1]['Condition'], x[1]['Staining']))

    num_images = len(sorted_data)
    columns = min(5, num_images)
    rows = (num_images + columns - 1) // columns

    fig, axs = plt.subplots(rows, columns, figsize=(20, rows * 4))
    axs = axs.flatten() if isinstance(axs, np.ndarray) else [axs]

    for ax, (image, metadata) in zip(axs, sorted_data):
        ax.imshow(image)
        ax.set_title(f"{metadata['Condition']}, {metadata['Staining']}", fontsize=8)
        ax.axis('off')

    for ax in axs[num_images:]:
        ax.axis('off')

    plt.tight_layout()
    plt.close()

def process_and_display_files():
    try:
        uploaded_files = upload_files()
    except ValueError as e:
        print(e)
        return None, None

    display_images = []
    metadata_list = []

    for filename, file_data in uploaded_files.items():
        display_image, metadata = process_image(file_data, filename)
        if display_image and metadata:
            display_images.append(display_image)
            metadata_list.append(metadata)

    if display_images:
        display_representative_images(display_images, metadata_list)

    df = pd.DataFrame(metadata_list)
    display(df)

    metadata_path = '/content/metadata.csv'
    df.to_csv(metadata_path, index=False)
    print(f"Metadata saved to {metadata_path}")

    return df, display_images

# Run the process
metadata_df, processed_images = process_and_display_files()





# Step 2: Flourescent-based Segmentation

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cv2
from tqdm import tqdm
import os
import re

def sanitize_filename(name):
    return re.sub(r'[^\w\-_]', '_', name)

def load_metadata(file_path):
    try:
        metadata_df = pd.read_csv(file_path)
        if metadata_df.empty:
            raise ValueError("The metadata file is empty.")
        return metadata_df
    except Exception as e:
        print(f"Error loading metadata: {e}")
        exit(1)

def detect_stain_types(metadata_df):
    return metadata_df['Staining'].unique()

def normalize_image(image):
    """Normalize image and enhance contrast"""
    img_float = image.astype(np.float32)
    img_norm = cv2.normalize(img_float, None, 0, 1, cv2.NORM_MINMAX)
    img_uint8 = (img_norm * 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img_clahe = clahe.apply(img_uint8)

    return img_clahe

def detect_sample_region(image, blur_size=45, large_kernel_size=35, smooth_kernel_size=7):
    """Detect the outer boundary of the tissue sample"""
    blurred = cv2.GaussianBlur(image, (blur_size, blur_size), 0)

    if blurred.dtype != np.uint8:
        blurred = (blurred * 255).astype(np.uint8)

    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel_large = np.ones((large_kernel_size, large_kernel_size), np.uint8)
    mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)

    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = (labels == largest_label).astype(np.uint8) * 255

    kernel_smooth = np.ones((smooth_kernel_size, smooth_kernel_size), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_smooth)

    return mask

def get_global_intensity_range(metadata_df, stain_type):
    """First pass: collect all pixel intensities from sample regions across all images"""
    print(f"\nCalculating global intensity range for {stain_type}...")
    all_sample_pixels = []
    stain_indices = metadata_df.index[metadata_df['Staining'] == stain_type]

    for index in tqdm(stain_indices, desc="Collecting pixel intensities"):
        try:
            image_path = metadata_df.at[index, 'FilePath']
            if not os.path.exists(image_path):
                continue

            # Load and normalize image
            image = load_image(image_path)
            normalized = normalize_image(image)

            # Get sample region
            sample_mask = detect_sample_region(normalized)

            # Collect pixels from sample region
            masked_image = cv2.bitwise_and(normalized, normalized, mask=sample_mask)
            sample_pixels = masked_image[sample_mask > 0]

            # Add to collection
            if len(sample_pixels) > 0:
                all_sample_pixels.extend(sample_pixels.tolist())

        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            continue

    if not all_sample_pixels:
        raise ValueError(f"No valid pixels found for stain type: {stain_type}")

    # Calculate global range
    all_pixels = np.array(all_sample_pixels)
    intensity_range = {
        'min': np.min(all_pixels),
        'max': np.max(all_pixels),
        'median': np.median(all_pixels),
        'threshold': np.percentile(all_pixels, 50)  # Use 50th percentile as threshold
    }

    return intensity_range

def detect_stained_regions_global(image, sample_mask, intensity_range):
    """Detect stained regions using global intensity threshold"""
    masked_image = cv2.bitwise_and(image, image, mask=sample_mask)

    # Calculate thresholds based on absolute range
    intensity_span = intensity_range['max'] - intensity_range['min']  # Changed from overwriting intensity_range
    lower_threshold = intensity_range['min'] + (intensity_span * 0.2)  # 20% of range
    middle_threshold = intensity_range['min'] + (intensity_span * 0.5)  # 50% of range

    # Create masks
    unstained_mask = np.where(
        (masked_image <= lower_threshold) & (sample_mask > 0),
        255, 0
    ).astype(np.uint8)

    high_intensity_mask = np.where(
        (masked_image > middle_threshold) & (sample_mask > 0),
        255, 0
    ).astype(np.uint8)

    low_intensity_mask = np.where(
        (masked_image > lower_threshold) &
        (masked_image <= middle_threshold) &
        (sample_mask > 0),
        255, 0
    ).astype(np.uint8)

    return high_intensity_mask, low_intensity_mask, unstained_mask

def calculate_statistics(sample_mask, high_intensity_mask, low_intensity_mask, unstained_mask):
    """Calculate statistics about the sample and staining levels"""
    total_sample_area = np.sum(sample_mask > 0)
    high_intensity_area = np.sum(high_intensity_mask > 0)
    low_intensity_area = np.sum(low_intensity_mask > 0)
    unstained_area = np.sum(unstained_mask > 0)

    if total_sample_area > 0:
        high_intensity_percentage = (high_intensity_area / total_sample_area) * 100
        low_intensity_percentage = (low_intensity_area / total_sample_area) * 100
        unstained_percentage = (unstained_area / total_sample_area) * 100
        total_stained_percentage = high_intensity_percentage + low_intensity_percentage
    else:
        high_intensity_percentage = 0
        low_intensity_percentage = 0
        unstained_percentage = 0
        total_stained_percentage = 0

    return {
        'total_sample_area': total_sample_area,
        'high_intensity_area': high_intensity_area,
        'low_intensity_area': low_intensity_area,
        'unstained_area': unstained_area,
        'high_intensity_percentage': high_intensity_percentage,
        'low_intensity_percentage': low_intensity_percentage,
        'unstained_percentage': unstained_percentage,
        'total_stained_percentage': total_stained_percentage
    }

def display_results(original, normalized, sample_mask, high_intensity_mask, low_intensity_mask,
                   unstained_mask, stats, image_path, stain_type, intensity_range):
    """Display analysis results with global threshold information"""
    fig, axes = plt.subplots(1, 5, figsize=(25, 5))

    # Original image
    axes[0].imshow(original, cmap='gray')
    axes[0].set_title('Original Image')
    axes[0].axis('off')

    # Normalized image
    axes[1].imshow(normalized, cmap='gray')
    axes[1].set_title('Normalized Image')
    axes[1].axis('off')

    # Sample region with total staining percentage
    axes[2].imshow(normalized, cmap='gray')
    contours, _ = cv2.findContours(sample_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        contour_points = np.squeeze(contour)
        if len(contour_points.shape) >= 2:
            axes[2].plot(contour_points[:, 0], contour_points[:, 1], 'r-', linewidth=2)
    axes[2].set_title(f'Sample Region\n(Total Stained: {stats["total_stained_percentage"]:.1f}% of sample)')
    axes[2].axis('off')

    # High intensity regions with sample boundary
    inverted_high = np.where(high_intensity_mask > 0, 0, 255)
    axes[3].imshow(inverted_high, cmap='gray')
    for contour in contours:
        contour_points = np.squeeze(contour)
        if len(contour_points.shape) >= 2:
            axes[3].plot(contour_points[:, 0], contour_points[:, 1], 'r-', linewidth=2)
    axes[3].set_title(f'High Intensity Regions\n({stats["high_intensity_percentage"]:.1f}% of sample)')
    axes[3].axis('off')

    # Low intensity regions with sample boundary
    inverted_low = np.where(low_intensity_mask > 0, 0, 255)
    axes[4].imshow(inverted_low, cmap='gray')
    for contour in contours:
        contour_points = np.squeeze(contour)
        if len(contour_points.shape) >= 2:
            axes[4].plot(contour_points[:, 0], contour_points[:, 1], 'r-', linewidth=2)
    axes[4].set_title(f'Low Intensity Regions\n({stats["low_intensity_percentage"]:.1f}% of sample)')
    axes[4].axis('off')

    # Add overall title with threshold info
    plt.suptitle(
        f"File: {os.path.basename(image_path)}\n"
        f"Stain: {stain_type} (Global Threshold: {intensity_range['threshold']:.1f})",
        fontsize=10
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig

def load_image(image_path):
    """Load image in grayscale"""
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    return image

def process_image(metadata_df, index, stain_type, intensity_range):
    """Process a single image using global intensity thresholds"""
    image_path = metadata_df.at[index, 'FilePath']
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return

    try:
        # Load and preprocess image
        image = load_image(image_path)
        normalized = normalize_image(image)
        sample_mask = detect_sample_region(normalized)

        # Get all three masks
        high_intensity_mask, low_intensity_mask, unstained_mask = detect_stained_regions_global(
            normalized, sample_mask, intensity_range
        )

        # Calculate statistics with all three masks
        stats = calculate_statistics(sample_mask, high_intensity_mask, low_intensity_mask, unstained_mask)

        # Create output directory if it doesn't exist
        output_dir = 'Fluorescence-Analysis'
        os.makedirs(output_dir, exist_ok=True)

        # Display results with all three masks
        fig = display_results(
            image, normalized, sample_mask,
            high_intensity_mask, low_intensity_mask, unstained_mask,
            stats, image_path, stain_type, intensity_range
        )

        # Save results
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        sanitized_stain = sanitize_filename(stain_type)
        results_filename = f"{base_filename}-{sanitized_stain}-analysis.png"
        results_path = os.path.join(output_dir, results_filename)
        fig.savefig(results_path)
        plt.close(fig)  # Close the figure to free memory

        # Update metadata
        metadata_df.at[index, 'Analysis_Path'] = results_path
        metadata_df.at[index, 'Sample_Area'] = stats['total_sample_area']
        metadata_df.at[index, 'High_Intensity_Area'] = stats['high_intensity_area']
        metadata_df.at[index, 'Low_Intensity_Area'] = stats['low_intensity_area']
        metadata_df.at[index, 'Unstained_Area'] = stats['unstained_area']
        metadata_df.at[index, 'High_Intensity_Percentage'] = stats['high_intensity_percentage']
        metadata_df.at[index, 'Low_Intensity_Percentage'] = stats['low_intensity_percentage']
        metadata_df.at[index, 'Unstained_Percentage'] = stats['unstained_percentage']
        metadata_df.at[index, 'Total_Stained_Percentage'] = stats['total_stained_percentage']

    except Exception as e:
        print(f"Error processing image {image_path}: {e}")

def process_stain_group(metadata_df, stain_type, intensity_range):
    """Process all images for a specific stain type using global intensity range"""
    print(f"\nProcessing {stain_type} stained images:")
    stain_indices = metadata_df.index[metadata_df['Staining'] == stain_type]

    for index in tqdm(stain_indices, desc=f"Processing {stain_type} images"):
        process_image(metadata_df, index, stain_type, intensity_range)

def main():
    metadata_df = load_metadata('metadata.csv')
    stain_types = detect_stain_types(metadata_df)
    print(f"Detected stain types: {stain_types}")

    # First pass: calculate global intensity ranges for each stain type
    intensity_ranges = {}
    for stain_type in stain_types:
        intensity_ranges[stain_type] = get_global_intensity_range(metadata_df, stain_type)

    # Second pass: process images using global thresholds
    for stain_type in stain_types:
        process_stain_group(metadata_df, stain_type, intensity_ranges[stain_type])

    metadata_df.to_csv('metadata.csv', index=False)
    print("Updated metadata saved to metadata.csv")

if __name__ == "__main__":
    main()



# Step 3: Quantification and Statsitical Analysis of Flourescent Images

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
import seaborn as sns
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
warnings.filterwarnings('ignore')

def sanitize_filename(name):
    return re.sub(r'[^\w\-_]', '_', name)

def load_metadata(file_path):
    try:
        metadata_df = pd.read_csv(file_path)
        if metadata_df.empty:
            raise ValueError("The metadata file is empty.")
        return metadata_df
    except Exception as e:
        print(f"Error loading metadata: {e}")
        exit(1)

def detect_stain_types(metadata_df):
    return metadata_df['Staining'].unique()

def create_analysis_plots(metadata_df, stain_type, output_dir):
    """Creates statistical plots for a specific stain type with total/low/high intensity boxes"""

    # Style parameters - adjust these values to modify the plot appearance
    FONT_SIZE = {
        'title': 14,        # Size of the plot title
        'axes_labels': 12,  # Size of x and y axis labels
        'tick_labels': 12,  # Size of tick labels
        'legend': 10        # Size of legend text
    }

    GRID_PARAMS = {
        'linewidth': 0.8,   # Thickness of grid lines (default was 0.5)
        'alpha': 0.3,       # Transparency of grid lines (0-1)
        'linestyle': '--'   # Style of grid lines
    }

    SEPARATOR_PARAMS = {
        'linewidth': 0.8,   # Thickness of vertical separator lines
        'alpha': 0.3,       # Transparency of separator lines
        'color': 'gray',    # Color of separator lines
        'linestyle': '--'   # Style of separator lines
    }

    # Color palette for different intensity levels
    COLOR_PALETTE = {
        'Total': '#e74c3c',
        'Low': '#2ecc71',
        'High': '#3498db'
    }

    stain_data = metadata_df[metadata_df['Staining'] == stain_type]
    if 'Condition' not in stain_data.columns:
        print(f"Warning: No condition data found for {stain_type}")
        return

    # Prepare data for plotting
    total_data = pd.DataFrame({
        'Condition': stain_data['Condition'],
        'Percentage': stain_data['Total_Stained_Percentage'],
        'Intensity_Level': 'Total'
    })
    low_data = pd.DataFrame({
        'Condition': stain_data['Condition'],
        'Percentage': stain_data['Low_Intensity_Percentage'],
        'Intensity_Level': 'Low'
    })
    high_data = pd.DataFrame({
        'Condition': stain_data['Condition'],
        'Percentage': stain_data['High_Intensity_Percentage'],
        'Intensity_Level': 'High'
    })

    # Concatenate in the desired order: Total, Low, High
    plot_data = pd.concat([total_data, low_data, high_data])

    # Create figure
    plt.figure(figsize=(12, 6))

    # Add horizontal gridlines with enhanced visibility
    plt.grid(axis='y',
            linestyle=GRID_PARAMS['linestyle'],
            linewidth=GRID_PARAMS['linewidth'],
            alpha=GRID_PARAMS['alpha'],
            zorder=0)

    # Create boxplot with ordered categories and no outliers
    ax = sns.boxplot(x='Condition', y='Percentage', hue='Intensity_Level',
                    data=plot_data, width=0.7, dodge=True,
                    hue_order=['Total', 'Low', 'High'],
                    palette=COLOR_PALETTE,
                    fliersize=0)

    # Add strip plots with matching order
    sns.stripplot(x='Condition', y='Percentage', hue='Intensity_Level',
                 data=plot_data, size=5, alpha=0.8, dodge=True,
                 hue_order=['Total', 'Low', 'High'],
                 edgecolor='black', linewidth=1,
                 palette=COLOR_PALETTE)

    # Set font sizes for title and labels
    plt.title(f'Stained Area Percentage by Condition for {stain_type}',
             fontsize=FONT_SIZE['title'])
    plt.xlabel('Condition',
              fontsize=FONT_SIZE['axes_labels'])
    plt.ylabel('Stained Area Percentage',
              fontsize=FONT_SIZE['axes_labels'])

    # Adjust tick label sizes
    plt.xticks(rotation=45, ha='right',
               fontsize=FONT_SIZE['tick_labels'])
    plt.yticks(fontsize=FONT_SIZE['tick_labels'])

    # Adjust legend with new font size
    plt.legend(title='Intensity Level',
              bbox_to_anchor=(1.05, 1),
              loc='upper left',
              fontsize=FONT_SIZE['legend'],
              title_fontsize=FONT_SIZE['legend'])

    # Add vertical separation lines with enhanced visibility
    conditions = len(plot_data['Condition'].unique())
    for x in range(conditions - 1):
        plt.axvline(x=x + 0.5,
                   color=SEPARATOR_PARAMS['color'],
                   linestyle=SEPARATOR_PARAMS['linestyle'],
                   linewidth=SEPARATOR_PARAMS['linewidth'],
                   alpha=SEPARATOR_PARAMS['alpha'])

    plt.tight_layout()

    # Save plots
    plt.savefig(os.path.join(output_dir, f'{sanitize_filename(stain_type)}_boxplot.svg'),
                format='svg', bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, f'{sanitize_filename(stain_type)}_boxplot.png'),
                format='png', dpi=300, bbox_inches='tight')
    plt.show()

def perform_statistical_analysis(metadata_df, stain_type, output_dir):
    """Performs statistical analysis for both high and low intensity measurements"""
    stain_data = metadata_df[metadata_df['Staining'] == stain_type]

    if 'Condition' not in stain_data.columns:
        return None

    # Perform analysis for both intensity levels and total
    intensity_levels = ['High_Intensity_Percentage', 'Low_Intensity_Percentage', 'Total_Stained_Percentage']
    results = {}

    for intensity in intensity_levels:
        # Perform one-way ANOVA
        conditions = [group for name, group in stain_data.groupby('Condition')[intensity]]
        f_val, p_val = stats.f_oneway(*conditions)

        # Perform Tukey's HSD test
        tukey = pairwise_tukeyhsd(stain_data[intensity], stain_data['Condition'])

        # Calculate descriptive statistics
        desc_stats = stain_data.groupby('Condition')[intensity].agg([
            'count', 'mean', 'std', 'sem'
        ])

        results[intensity] = {
            'anova_pvalue': p_val,
            'tukey_results': tukey,
            'descriptive_stats': desc_stats
        }

        # Create p-value heatmap for each intensity level
        conditions = sorted(stain_data['Condition'].unique())
        p_value_matrix = pd.DataFrame(1.0, index=conditions, columns=conditions)

        for row in tukey.summary().data[1:]:
            group1, group2, _, p_value = row[0], row[1], row[2], row[3]
            p_value_matrix.loc[group1, group2] = p_value
            p_value_matrix.loc[group2, group1] = p_value

        plt.figure(figsize=(10, 8))
        mask = np.triu(np.ones_like(p_value_matrix, dtype=bool), k=1)
        sns.heatmap(p_value_matrix, mask=mask, annot=True, cmap='coolwarm_r',
                    vmin=0, vmax=1, fmt='.5f', linewidths=0.5, square=True)
        plt.title(f'P-value Heatmap for {stain_type} ({intensity.split("_")[0]})')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save heatmap
        intensity_label = intensity.split('_')[0].lower()
        plt.savefig(os.path.join(output_dir,
                   f'{sanitize_filename(stain_type)}_{intensity_label}_pvalue_heatmap.svg'),
                   format='svg')
        plt.savefig(os.path.join(output_dir,
                   f'{sanitize_filename(stain_type)}_{intensity_label}_pvalue_heatmap.png'),
                   format='png', dpi=300)
        plt.show()

    # Save statistical results to file
    results_path = os.path.join(output_dir, f'{sanitize_filename(stain_type)}_statistical_results.txt')
    with open(results_path, 'w') as f:
        f.write(f"Statistical Analysis Results for {stain_type}\n\n")

        for intensity in intensity_levels:
            intensity_label = intensity.split('_')[0]
            f.write(f"\n{intensity_label} Intensity Results:\n")
            f.write(f"One-way ANOVA p-value: {results[intensity]['anova_pvalue']:.5f}\n\n")
            f.write(f"Tukey's HSD Test Results:\n")
            f.write(str(results[intensity]['tukey_results'].summary()))
            f.write("\n\nDescriptive Statistics:\n")
            f.write(str(results[intensity]['descriptive_stats']))
            f.write("\n" + "="*50 + "\n")

    return results

def main():
    # Create output directory for analysis results
    output_dir = 'Statistical-Analysis'
    os.makedirs(output_dir, exist_ok=True)

    # Load the processed metadata from the first script
    metadata_df = load_metadata('metadata.csv')
    stain_types = detect_stain_types(metadata_df)
    print(f"Detected stain types: {stain_types}")

    # Process each stain type
    all_results = {}
    for stain_type in stain_types:
        print(f"\nAnalyzing {stain_type}...")
        # Create plots and perform statistical analysis
        create_analysis_plots(metadata_df, stain_type, output_dir)
        all_results[stain_type] = perform_statistical_analysis(metadata_df, stain_type, output_dir)

    # Print summary of statistical results
    print("\nStatistical Analysis Summary:")
    for stain_type, results in all_results.items():
        if results:
            print(f"\n{stain_type}:")
            for intensity in ['High_Intensity_Percentage', 'Low_Intensity_Percentage', 'Total_Stained_Percentage']:
                intensity_label = intensity.split('_')[0]
                print(f"\n{intensity_label} Intensity Results:")
                print(f"ANOVA p-value: {results[intensity]['anova_pvalue']:.5f}")
                print("\nDescriptive Statistics:")
                print(results[intensity]['descriptive_stats'])

if __name__ == "__main__":
    main()
