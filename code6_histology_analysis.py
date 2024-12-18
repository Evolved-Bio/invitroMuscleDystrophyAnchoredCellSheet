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




# Step 2: Staining-Dependent Color Segmentation

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cv2
from tqdm import tqdm
import os
import re

# Keep all existing helper functions the same
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

def define_predefined_color_groups():
    # Keep your existing color groups exactly as they are
    return {
        'HE': {
            'Nuclei': [(93, 51, 105), (132, 80, 136), (79, 51, 98)],
            'Cytoplasm/Fibrosis/Muscle': [(163, 107, 158), (143, 103, 143), (157, 132, 155)],
            'Other': [(239, 221, 236), (240, 224, 237), (226, 169, 213)]
        },
        'Trichrome': {
            'Nuclei/Cytoplasm/Muscle': [(114, 52, 66), (175, 141, 154), (122, 59, 73), (151, 56, 63), (178, 94, 107), (196, 131, 145), (123, 47, 60), (141, 42, 46), (169, 73, 84)],
            'Fibrosis': [(175, 141, 154), (204, 189, 197), (156, 137, 149)],
            'Other': [(233, 217, 224), (215, 175, 187), (211, 188, 197)]
        },
        'Movat': {
            'Nuclei/Elastin': [(40, 20, 31), (53, 33, 57)],
            'Muscle/Cytoplasm/Fibrosis': [(79, 61, 83), (190, 165, 180), (121, 104, 128)],
            'Other': [(216, 209, 220), (214, 198, 211)]
        }
    }

def detect_sample_region(image, white_threshold=220, blur_size=25, large_kernel_size=15, smooth_kernel_size=7):
    """Detect the sample region in histology images by finding non-white regions"""
    # Create mask for non-white pixels
    # A pixel is considered white if all RGB values are above threshold
    mask = np.any(image < white_threshold, axis=2).astype(np.uint8) * 255

    # Apply Gaussian blur to smooth the mask
    blurred = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)

    # Threshold to clean up the mask
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY)

    # Morphological operations to clean up the mask
    kernel_large = np.ones((large_kernel_size, large_kernel_size), np.uint8)
    mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_large)

    # Find the largest connected component
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)

    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = (labels == largest_label).astype(np.uint8) * 255

    # Final smoothing
    kernel_smooth = np.ones((smooth_kernel_size, smooth_kernel_size), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_smooth)

    return mask

def get_color_group(stain):
    predefined_groups = define_predefined_color_groups()
    return predefined_groups.get(stain, None)

def segment_image(image, color_groups):
    pixels = image.reshape(-1, 3).astype(np.float64)
    distances = np.zeros((len(pixels), len(color_groups)))

    # Calculate distances to each color group
    for i, colors in enumerate(color_groups.values()):
        colors_array = np.array(colors)
        distances[:, i] = np.min(np.linalg.norm(pixels[:, np.newaxis] - colors_array, axis=2), axis=1)

    # Create mask for white/background pixels
    white_pixels = np.all(pixels > 240, axis=1)

    # Assign labels only to non-white pixels
    labels = np.zeros(len(pixels), dtype=int)
    non_white_mask = ~white_pixels
    labels[non_white_mask] = np.argmin(distances[non_white_mask], axis=1)

    # Set white pixels to a special label (e.g., -1)
    labels[white_pixels] = -1

    return labels.reshape(image.shape[:2])

def display_color_palette(color_groups, stain, title):
    fig, ax = plt.subplots(figsize=(10, 2))
    for i, (name, colors) in enumerate(color_groups.items()):
        for j, color in enumerate(colors):
            ax.add_patch(plt.Rectangle((i + j/len(colors), 0), 1/len(colors), 1, facecolor=np.array(color)/255))
        ax.text(i+0.5, -0.1, name, ha='center', va='center', rotation=45)
    ax.set_xlim(0, len(color_groups))
    ax.set_ylim(-0.5, 1)
    ax.axis('off')
    plt.title(title)
    plt.tight_layout()
    plt.show()

def process_and_display_image(metadata_df, index, stain, color_groups):
    image_path = metadata_df.at[index, 'FilePath']
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return

    # Load image
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detect sample region and get contours
    sample_mask = detect_sample_region(img_rgb)
    contours, _ = cv2.findContours(sample_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Segment the image within sample region
    masked_img = cv2.bitwise_and(img_rgb, img_rgb, mask=sample_mask)
    segmented = segment_image(masked_img, color_groups)

    output_dir = 'Staining-Seg'
    os.makedirs(output_dir, exist_ok=True)

    base_filename = os.path.splitext(os.path.basename(image_path))[0]
    sanitized_stain = sanitize_filename(stain)

    # Save individual segments
    white_mask = np.all(img_rgb > 240, axis=2)
    effective_mask = np.logical_and(sample_mask > 0, ~white_mask)

    for i, (name, colors) in enumerate(color_groups.items()):
        segment = np.where(np.logical_and(segmented[..., np.newaxis] == i, effective_mask[..., np.newaxis]),
                          img_rgb,
                          [255, 255, 255])
        segment = segment.astype(np.uint8)

        sanitized_name = sanitize_filename(name)
        seg_filename = f"{base_filename}-{sanitized_stain}-{sanitized_name}.png"
        seg_path = os.path.join(output_dir, seg_filename)

        # Add red contour to segment before saving
        segment_with_contour = segment.copy()
        cv2.drawContours(segment_with_contour, contours, -1, (255, 0, 0), 2)
        cv2.imwrite(seg_path, cv2.cvtColor(segment_with_contour, cv2.COLOR_RGB2BGR))

        metadata_df.at[index, f'Staining_Segment_{sanitized_name}_Path'] = seg_path

    # Display and save results with contours
    row_image = display_results(img_rgb, color_groups, segmented, image_path, stain, sample_mask, contours)
    row_filename = f"{base_filename}-{sanitized_stain}-row.png"
    row_path = os.path.join(output_dir, row_filename)
    cv2.imwrite(row_path, cv2.cvtColor(row_image, cv2.COLOR_RGB2BGR))
    metadata_df.at[index, 'Staining_Row_Path'] = row_path

def display_results(img_rgb, color_groups, segmented, image_path, stain, sample_mask, contours):
    n_colors = len(color_groups)
    fig, axes = plt.subplots(1, n_colors + 1, figsize=(5 * (n_colors + 1), 5))

    # Original image with contour
    axes[0].imshow(img_rgb.astype(np.uint8))
    for contour in contours:
        contour_points = np.squeeze(contour)
        if len(contour_points.shape) >= 2:
            axes[0].plot(contour_points[:, 0], contour_points[:, 1], 'r-', linewidth=2)
    axes[0].set_title("Original Image")
    axes[0].axis('off')

    # Create additional mask for white/near-white pixels
    white_mask = np.all(img_rgb > 240, axis=2)  # Adjust threshold as needed
    # Combine with sample mask to exclude both background and white pixels
    effective_mask = np.logical_and(sample_mask > 0, ~white_mask)

    # Calculate total non-white pixels within sample region for percentage
    total_valid_pixels = np.sum(effective_mask)

    # Display segments with contours
    for i, (name, colors) in enumerate(color_groups.items()):
        segment = np.where(np.logical_and(segmented[..., np.newaxis] == i, effective_mask[..., np.newaxis]),
                          img_rgb,
                          [255, 255, 255])
        axes[i + 1].imshow(segment.astype(np.uint8))

        # Add red contour
        for contour in contours:
            contour_points = np.squeeze(contour)
            if len(contour_points.shape) >= 2:
                axes[i + 1].plot(contour_points[:, 0], contour_points[:, 1], 'r-', linewidth=2)

        # Calculate percentage within effective region (non-white within sample)
        if total_valid_pixels > 0:
            segment_pixels = np.sum(np.logical_and(segmented == i, effective_mask))
            percentage = (segment_pixels / total_valid_pixels) * 100
        else:
            percentage = 0

        axes[i + 1].set_title(f"{name}\n{percentage:.1f}% of tissue")  # Changed to "of tissue" for clarity
        axes[i + 1].axis('off')

    plt.suptitle(f"File: {os.path.basename(image_path)} - Stain: {stain}", fontsize=10)
    plt.tight_layout()

    fig.canvas.draw()
    row_image = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    row_image = row_image.reshape(fig.canvas.get_width_height()[::-1] + (3,))

    plt.close()
    return row_image

def process_stain_group(metadata_df, stain, color_groups):
    print(f"\nProcessing {stain} stained images:")
    stain_indices = metadata_df.index[metadata_df['Staining'] == stain]

    display_color_palette(color_groups, stain, f"Color Palette for {stain} Stain")

    for index in tqdm(stain_indices, desc=f"Processing {stain} images"):
        process_and_display_image(metadata_df, index, stain, color_groups)

def main():
    metadata_df = load_metadata('metadata.csv')
    stain_types = detect_stain_types(metadata_df)
    print(f"Detected stain types: {stain_types}")

    for stain in stain_types:
        print(f"\nAnalyzing colors for {stain} stain:")
        color_group = get_color_group(stain)
        if color_group is None:
            print(f"No color groups defined for {stain}. Skipping.")
            continue
        process_stain_group(metadata_df, stain, color_group)

    metadata_df.to_csv('metadata.csv', index=False)
    print("Updated metadata saved to metadata.csv")

if __name__ == "__main__":
    main()




# Step 3: Quantification and Statistical Analysis of Segments

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import seaborn as sns
from PIL import Image
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
warnings.filterwarnings('ignore')

def create_original_mask(image_path, white_threshold=240):
    """
    Creates two masks:
    1. Sample region mask (from edge detection)
    2. Non-white tissue mask (excluding white/near-white pixels)
    """
    with Image.open(image_path) as img:
        img_array = np.array(img)

        # Create mask for the sample region (using the same logic as in first code)
        sample_region = np.any(img_array < 250, axis=2)

        # Create mask for non-white pixels (more stringent threshold)
        tissue_mask = ~np.all(img_array > white_threshold, axis=2)

        # Combine masks: must be both within sample region AND not white
        final_mask = np.logical_and(sample_region, tissue_mask)

        return final_mask

def calculate_non_white_percentage(segment_path, original_mask, white_threshold=240):
    """
    Calculates the percentage of tissue in a segment, considering:
    1. Only pixels within the original sample region
    2. Excluding white/near-white pixels
    3. Only counting actual tissue pixels
    """
    try:
        with Image.open(segment_path) as img:
            segment_array = np.array(img)

            # Create mask for non-white pixels in segment
            segment_tissue = ~np.all(segment_array > white_threshold, axis=2)

            # Combine with original mask (must be tissue in both original AND segment)
            valid_tissue = np.logical_and(segment_tissue, original_mask)

            # Calculate percentage relative to total valid tissue area in original
            total_tissue_pixels = np.sum(original_mask)
            segment_tissue_pixels = np.sum(valid_tissue)

            if total_tissue_pixels == 0:
                return 0

            percentage = (segment_tissue_pixels / total_tissue_pixels) * 100
            return percentage

    except Exception as e:
        print(f"Error processing image {segment_path}: {str(e)}")
        return np.nan

def get_valid_segments_for_staining(metadata_df, staining):
    """
    Returns list of segment columns that exist for a specific staining type.
    """
    staining_mask = metadata_df['Staining'] == staining
    segment_columns = [col for col in metadata_df.columns
                      if col.startswith('Staining_Segment_') and col.endswith('_Path')]

    # Check which segments actually exist for this staining type
    valid_segments = []
    for col in segment_columns:
        if not metadata_df.loc[staining_mask, col].isna().all():
            valid_segments.append(col)

    return valid_segments

def create_stain_consolidated_plots(metadata_df, output_dir):
    """Creates consolidated plots for each staining type, showing all segments with enhanced visibility"""

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

    for staining in metadata_df['Staining'].unique():
        print(f"\nCreating consolidated plot for {staining} staining...")

        # Filter data for this staining type
        staining_mask = metadata_df['Staining'] == staining
        staining_df = metadata_df[staining_mask].copy()

        # Get valid segments for this staining type
        valid_segments = get_valid_segments_for_staining(metadata_df, staining)

        if not valid_segments:
            print(f"No valid segments found for {staining}")
            continue

        # Create plot data
        plot_data = []
        for segment_path in valid_segments:
            segment_name = segment_path.split('Staining_Segment_')[1].replace('_Path', '')
            percentage_column = f'{segment_name}_NonWhite_Percentage'

            if percentage_column not in staining_df.columns:
                print(f"Warning: {percentage_column} not found in data. Skipping.")
                continue

            temp_df = staining_df[['Condition', percentage_column]].copy()
            temp_df['Segment'] = segment_name
            temp_df.rename(columns={percentage_column: 'Percentage'}, inplace=True)
            plot_data.append(temp_df)

        if not plot_data:
            print(f"No valid percentage data found for {staining}")
            continue

        plot_df = pd.concat(plot_data, ignore_index=True)
        plot_df = plot_df.dropna()

        if plot_df.empty:
            print(f"No valid data for {staining}")
            continue

        # Set figure size based on number of segments
        num_segments = len(plot_data)
        plt.figure(figsize=(max(12, num_segments * 2), 8))

        # Add horizontal gridlines with enhanced visibility
        plt.grid(axis='y',
                linestyle=GRID_PARAMS['linestyle'],
                linewidth=GRID_PARAMS['linewidth'],
                alpha=GRID_PARAMS['alpha'],
                zorder=0)

        # Sort segments: Nucleus first, Other last, rest in alphabetical order
        unique_segments = plot_df['Segment'].unique()
        sorted_segments = sorted(unique_segments,
                               key=lambda x: (
                                   0 if 'Nuclei' in x or 'Nucleus' in x
                                   else 2 if 'Other' in x
                                   else 1,
                                   x
                               ))

        # Create color palettes for conditions
        conditions = sorted(plot_df['Condition'].unique())
        base_colors = {'DD': '#e74c3c', 'HC': '#2ecc71', 'MD': '#3498db'}
        darker_colors = {'DD': '#c0392b', 'HC': '#27ae60', 'MD': '#2980b9'}

        # Create box plot with segments grouped together
        ax = sns.boxplot(x='Segment', y='Percentage', hue='Condition',
                        data=plot_df, width=0.7, fliersize=0,
                        palette=base_colors,
                        order=sorted_segments)

        # Add strip plot
        sns.stripplot(x='Segment', y='Percentage', hue='Condition',
                     data=plot_df, size=5, alpha=0.8, dodge=True,
                     edgecolor='black', linewidth=1,
                     palette=darker_colors,
                     order=sorted_segments)

        # Add vertical separation lines with enhanced visibility
        for x in range(len(sorted_segments) - 1):
            plt.axvline(x=x + 0.5,
                       color=SEPARATOR_PARAMS['color'],
                       linestyle=SEPARATOR_PARAMS['linestyle'],
                       linewidth=SEPARATOR_PARAMS['linewidth'],
                       alpha=SEPARATOR_PARAMS['alpha'])

        # Set font sizes
        plt.title(f'Segment Analysis for {staining} Staining',
                 fontsize=FONT_SIZE['title'])
        plt.xlabel('Segment Type',
                  fontsize=FONT_SIZE['axes_labels'])
        plt.ylabel('Non-White Percentage',
                  fontsize=FONT_SIZE['axes_labels'])

        # Adjust tick label sizes
        plt.xticks(rotation=45, ha='right',
                  fontsize=FONT_SIZE['tick_labels'])
        plt.yticks(fontsize=FONT_SIZE['tick_labels'])

        # Adjust legend with new font size
        handles, labels = ax.get_legend_handles_labels()
        unique_conditions = plot_df['Condition'].unique()
        ax.legend(handles[:len(unique_conditions)],
                 labels[:len(unique_conditions)],
                 title='Condition',
                 bbox_to_anchor=(1.05, 1),
                 loc='upper left',
                 fontsize=FONT_SIZE['legend'],
                 title_fontsize=FONT_SIZE['legend'])

        plt.tight_layout()

        # Save plot
        plt.savefig(os.path.join(output_dir, f'{staining}_consolidated_segments.svg'),
                    format='svg', bbox_inches='tight')
        plt.savefig(os.path.join(output_dir, f'{staining}_consolidated_segments.png'),
                    format='png', dpi=300, bbox_inches='tight')
        plt.show()


def perform_statistical_analysis(metadata_df, output_dir):
    """Performs ANOVA and Tukey's HSD test for each staining group and segment."""
    all_results = {}

    for staining in metadata_df['Staining'].unique():
        staining_mask = metadata_df['Staining'] == staining
        staining_indices = metadata_df.index[staining_mask]

        # Get valid segments for this staining type
        valid_segment_columns = get_valid_segments_for_staining(metadata_df, staining)

        for segment_column in valid_segment_columns:
            segment_name = segment_column.split('Staining_Segment_')[1].replace('_Path', '')
            percentage_column = f'{segment_name}_NonWhite_Percentage'

            if percentage_column not in metadata_df.columns:
                continue

            analysis_data = metadata_df.loc[staining_indices,
                                          [percentage_column, 'Condition']].dropna()

            if analysis_data.empty:
                continue

            # Perform one-way ANOVA
            conditions = [group for name, group in analysis_data.groupby('Condition')[percentage_column]]
            f_val, p_val = stats.f_oneway(*conditions)
            anova_result = f"One-way ANOVA p-value: {p_val:.5f}"

            # Perform Tukey's HSD test
            tukey = pairwise_tukeyhsd(analysis_data[percentage_column],
                                    analysis_data['Condition'])

            # Create p-value matrix for heatmap
            conditions = sorted(analysis_data['Condition'].unique())
            p_value_matrix = pd.DataFrame(1.0, index=conditions, columns=conditions)

            # Fill the p-value matrix
            for row in tukey.summary().data[1:]:
                group1, group2, _, p_value = row[0], row[1], row[2], row[3]
                p_value_matrix.loc[group1, group2] = p_value
                p_value_matrix.loc[group2, group1] = p_value

            # Create heatmap
            plt.figure(figsize=(10, 8))
            mask = np.triu(np.ones_like(p_value_matrix, dtype=bool), k=1)
            sns.heatmap(p_value_matrix, mask=mask,
                       annot=True, cmap='coolwarm_r',
                       vmin=0, vmax=1,
                       fmt='.5f', linewidths=0.5,
                       square=True)
            plt.title(f'P-value Heatmap for {staining} ({segment_name})')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir,
                       f'{staining}_{segment_name}_pvalue_heatmap.svg'),
                       format='svg')
            plt.savefig(os.path.join(output_dir,
                       f'{staining}_{segment_name}_pvalue_heatmap.png'),
                       format='png', dpi=300)
            plt.show()

            # Calculate descriptive statistics
            desc_stats = analysis_data.groupby('Condition')[percentage_column].agg([
                'count', 'mean', 'std', 'sem'
            ])

            # Store results
            all_results[(staining, segment_name)] = {
                'anova_result': anova_result,
                'tukey_summary': str(tukey.summary()),
                'descriptive_stats': desc_stats,
                'analysis_data': analysis_data
            }

            # Save results to file
            with open(os.path.join(output_dir,
                     f'{staining}_{segment_name}_statistical_results.txt'), 'w') as f:
                f.write(f"Statistical Analysis Results for {staining} ({segment_name})\n\n")
                f.write(f"{anova_result}\n\n")
                f.write("Tukey's HSD Test Results:\n")
                f.write(str(tukey.summary()))
                f.write("\n\nDescriptive Statistics:\n")
                f.write(str(desc_stats))

    return all_results

def create_non_white_percentage_plots(metadata_df, output_dir):
    """Creates plots showing non-white percentages for each segment"""
    updated_df = metadata_df.copy()

    for idx, row in metadata_df.iterrows():
        # Get original image path
        image_path = row['FilePath']
        if not os.path.exists(image_path):
            continue

        # Create combined mask (sample region AND non-white pixels)
        tissue_mask = create_original_mask(image_path)

        # Process each segment
        for col in metadata_df.columns:
            if col.startswith('Staining_Segment_') and col.endswith('_Path'):
                segment_path = row[col]
                if pd.isna(segment_path) or not os.path.exists(segment_path):
                    continue

                # Calculate percentage using improved masking
                segment_name = col.split('Staining_Segment_')[1].replace('_Path', '')
                percentage = calculate_non_white_percentage(segment_path, tissue_mask)

                # Add percentage to dataframe
                percentage_column = f'{segment_name}_NonWhite_Percentage'
                updated_df.at[idx, percentage_column] = percentage

    return updated_df

# Main execution
if __name__ == "__main__":
    metadata_path = 'metadata.csv'
    output_dir = 'Statistical-Analysis'  # Changed from 'Staining-Seg' to 'Statistical-Analysis'

    try:
        print("Starting analysis...")
        os.makedirs(output_dir, exist_ok=True)

        print("Loading metadata...")
        metadata_df = pd.read_csv(metadata_path)

        print("Creating non-white percentage plots...")
        updated_metadata_df = create_non_white_percentage_plots(metadata_df, output_dir)

        print("Creating stain-specific consolidated plots...")
        create_stain_consolidated_plots(updated_metadata_df, output_dir)

        print("Performing statistical analysis...")
        statistical_results = perform_statistical_analysis(updated_metadata_df, output_dir)

        print("\nDetailed statistical results:")
        for (staining, segment_name), results in statistical_results.items():
            print(f"\nResults for {staining} - {segment_name}:")
            print(results['anova_result'])
            print("\nTukey HSD results:")
            print(results['tukey_summary'])
            print("\nDescriptive Statistics:")
            print(results['descriptive_stats'])
            print("\n" + "="*50 + "\n")

        print(f"Analysis complete. Results saved in the {output_dir} folder.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
