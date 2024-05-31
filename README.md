# _in vivo_-like scaffold-free 3D _in vitro_ Models of Muscular Dystrophies: The Case for Anchored Cell Sheet Engineering in Personalized Medicine

**Overview:**

Progress in understanding and treating muscle dystrophies, such as Duchenne and Myotonic dystrophies, has been limited by the lack of _in vitro_ models that accurately mimic physiological and pathological conditions. This study introduces a novel platform using a scaffold- and biomaterial-free cell sheet engineering method to create _in vitro_ models with patient-specific cells. Known as anchored cell sheet engineering, this approach successfully replicates mature cell phenotypes and disease-specific extracellular matrix (ECM) produced by the cells. By developing robust 3D muscle fibers from primary cells of healthy individuals and patients with Duchenne dystrophy and Myotonic dystrophy type 1, proteomics analysis confirmed that these models closely resemble _in vivo_ conditions. Custom Python scripts were employed to analyze the proteomics data, revealing that the models accurately reflect key disease phenotypes through various analyses, including differential expression analysis and various statistical analyses. Additionally, treating these models with therapeutically beneficial drugs demonstrated significant changes in their proteomic profiles, some toward healthier phenotypes. This innovative _in vitro_ modeling approach, combined with proteomics analysis and custom Python scripts for extracting novel insights, offers a promising platform for advancing muscle dystrophy research, among other diseases, and improving drug screening for new therapeutic strategies.

**Contents:**

<ins>Code1_Volcano_Plot.py</ins>: This code uses the output of multiple-sample tests from Perseus software to generate volcano plots and create lists of up- and down-regulated proteins for each comparison. The Perseus workflow includes adding a value of 1 to all data (original proteomics data in the form of normalized total precursor intensity) to avoid generating NaN values in the subsequent log2 transformation step. Then, multiple-sample tests are performed using ANOVA with an FDR of 0.05 and an S0 of 0. The results of these steps are used to generate multiple CSV files, one for each comparison between two groups/conditions. Each CSV file contains three columns: Accession_Number, -Log(Pvalue), and Difference, and is used as input for this script that generates the volcano plots.

<ins>Code2_Scatter_Plot.py</ins>: This code uses a CSV file containing the log2-transformed version of proteomics data in the form of normalized total precursor intensity. The first three columns are protein identifiers: Accession_Number, Alternate_ID, and Identified_Proteins, followed by different conditions and their replicates. The code prompts for the desired comparisons and generates scatter plots for each comparison.

<ins>Code3_UpSet_Plot.py</ins>: This code uses a CSV file containing the original proteomics data in the form of normalized total precursor intensity. The first three columns are protein identifiers: Accession_Number, Alternate_ID, and Identified_Proteins, followed by different conditions and their replicates. The code uses the healthy samples (HC group) as the control and calculates z-scores for proteins in other conditions relative to the control. A threshold z-score of ±1 is considered to capture a broad range of expression changes, facilitating the identification of proteins with generally higher or lower expressions relative to the control. The results are displayed as one UpSet plot.

<ins>Code4_RankAbundance_Plot.py</ins>: This code takes multiple CSV files, each containing the original proteomics data in the form of normalized total precursor intensity for the groups/conditions being compared. The first column is the protein identifier, Accession_Number, followed by conditions/groups and their replicates. The code first log10 transforms the data and then calculates the mean for the replicates of each condition. Finally, it generates a separate rank-abundance plot for each CSV file. The code also calculates Shannon Diversity Index shown as a heatmap juxtaposed to the Rank-abundance plot.

<ins>Code5_Violin_Plot.py</ins>: This code takes multiple CSV files, each containing the output of multiple-sample test analysis from Perseus. Each CSV file contains a comparison of two specific conditions and includes three columns: Accession_Number, -Log(Pvalue), and Difference. The code uses the Difference column from each CSV file to generate a violin plot that visualizes the distribution and overlap of protein expression changes (fold changes of protein expressions in each comparison) across the different comparisons. I also conducts a a rigorous statistical analysis including the Shapiro-Wilk test for normality and the Levene’s test for variance equality. Based on these results, an independent t-test, Welch’s t-test, or Mann-Whitney U test is applied as appropriate. The Benjamini-Hochberg procedure calculates adjusted p-values to control the false discovery rate (FDR). A csv file is generated that includes the analysis results, including test types, statistics, and adjusted p-values. This is also visualized using a dot plot.

**Dependencies:**
Google Colab environment, multiple Python libraries

**Contributions:**
We welcome contributions to enhance this research. Please open issues for discussions or submit pull requests for code improvements.

**Credits:**
This project aligns with Evolved.Bio's mission to advance regenerative medicine through anchored cell sheet engineering, machine learning, and biomanufacturing. As a Canadian biotechnology startup, Evolved.Bio pioneers innovative approaches to create a world-leading tissue foundry.

**License:**
This work is published under [insert license details] as part of an open access publication [insert DOI].

**Contact:**
For questions or collaborations, please reach out to Alireza Shahin (alireza@itsevolved.com).
