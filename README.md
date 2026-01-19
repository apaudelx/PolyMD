# PolyMD Database

This repository contains the code for PolyMD, an automated pipeline for extracting polymer property data from the literature using DOI retrieval, metadata collection, abstract classification, and LLM-based extraction.

## Overview

The codebase implements a multi-stage pipeline:

1. **DOI Extraction** (`extract_doi_from_keywords.py`): Extracts relevant DOIs from external APIs using keyword queries
2. **Metadata Retrieval** (`fetch_metadata_from_doi.py`): Fetches abstracts and other metadata from DOIs
3. **Abstract Classification** (`one_shot_classifier.py`): Classifies abstracts to identify papers relevant to MD simulation of polymers
4. **Information Extraction** (`prompt_based_extraction.py`): Uses LLM-based extraction to extract numerical simulation data from articles

## Prerequisites

### Python Version

- Python 3.10+

### Python Requirements
 - All the requirements are contained in "requirements.txt"

### R Dependencies (for analysis scripts)

- `readxl` - For reading Excel files
- `dplyr` - For data manipulation
- `ggplot2` - For plotting
- `grid` - For layout
- `tidyr` - For data reshaping
- `scales` - For axis formatting
- `showtext` - For fonts
- `patchwork` - For plot arrangement

### External Tools

- `marker` - For PDF to markdown conversion (used in `convert_pdf_to_markdown.sh`)
- `pymupdf` (fitz) - For PDF processing in helper scripts

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd code
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install requests pandas transformers torch openai pymupdf
```

4. Install R packages (if using analysis scripts):
```r
install.packages(c("readxl", "dplyr", "ggplot2", "grid", "tidyr", "scales", "showtext", "patchwork"))
```

5. Set up API keys:
```bash
export PAPI_KEY="your_perplexity_api_key_here"
```

## Usage

### Step 1: Extract DOIs from Keywords

This script uses the Crossref API to extract DOIs relevant to a given keyword query.

```bash
python extract_doi_from_keywords.py
```

### Step 2: Fetch Metadata from DOIs

This script retrieves abstracts, titles, authors, and other metadata from DOIs using multiple sources (Semantic Scholar, Crossref, OpenAlex).

```bash
python fetch_metadata_from_doi.py <input_file> <output_file>
```

**Example:**
```bash
python fetch_metadata_from_doi.py dois_journal_1995_1999.txt metadata_output.csv
```

### Step 3: Classify Relevant Abstracts

This script uses a zero-shot classifier to identify abstracts relevant to polymer MD simulations.

**Before running:** Prepare an `abstract` folder containing text files with abstracts (one per file, named `abstract1.txt`, `abstract2.txt`, etc.).

```bash
python one_shot_classifier.py
```


### Step 4: LLM-based Information Extraction

This script uses the Perplexity API to extract numerical simulation data from markdown-formatted articles.

**Before running:**
1. Set the `PAPI_KEY` environment variable with your Perplexity API key
2. Prepare a directory containing markdown files (e.g., "input_md")
3. Update the `input_dir` and `output_dir` variables in the script

```bash
export PAPI_KEY="your_api_key"
python prompt_based_extraction.py
```

**Configuration:**

Edit the script to modify:
- `input_dir`: Directory containing markdown files (default: "ground_truth_627")
- `output_dir`: Output directory for JSON results (default: "predicted_627")
- API model: Uses "sonar" model from Perplexity

**Output:**
- `{filename}.json`: Parsed extraction results in JSON format
- `{filename}_raw.txt`: Raw API responses (if JSON parsing fails)

**Extracted Properties:**
- Polymer system
- Force field
- Density (g/cm³)
- Glass Transition Temperature (K)
- Radius of Gyration (nm)
- Young's Modulus (GPa)
- Diffusion Coefficient (m²/s)
- Viscosity (Pa s)

## Helper Scripts

### Extract DOI and Title from PDFs

Extracts DOI and title information from PDF files in a folder.

```bash
python helpers/get_doi_title_from_pdf.py --folder <pdf_folder> [--out-csv <output.csv>] [--mailto <email>]
```

**Example:**
```bash
python helpers/get_doi_title_from_pdf.py --folder pdfs/ --out-csv pdf_metadata.csv --mailto your_email@example.com
```

### Convert PDFs to Markdown

Converts PDF files to markdown format using the `marker` tool. Designed for SLURM cluster execution.

**Configuration:**

Edit `helpers/convert_pdf_to_markdown.sh` to set:
- SLURM resource allocation parameters
- CUDA module path
- Virtual environment path
- Input and output directory arrays

**Usage:**
```bash
sbatch helpers/convert_pdf_to_markdown.sh
```

**Note:** Requires the `marker` tool to be installed and configured.


### Analysis

The folder contains scripts to generate analysis plots for publication.
