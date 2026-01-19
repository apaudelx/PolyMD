#!/bin/bash
#SBATCH -N  (number_of_gpus_nodes)                   
#SBATCH -t 72:00:00
#SBATCH -p gpu2
#SBATCH -A your_allocation_name
#SBATCH -o  gb.out
#SBATCH -e  err.out
#SBATCH --array=1-3 

# ====== Set up environment ======
module load cuda/12.1   # or your cluster's CUDA module

source /path/to/venv/activate

# ====== Define arrays ======

INPUT_DIRS=(input_folder)
OUTPUT_DIRS=(output_folder)

IDX=$((SLURM_ARRAY_TASK_ID-1))
INPUT=${INPUT_DIRS[$IDX]}
OUTPUT=${OUTPUT_DIRS[$IDX]}

# ====== Assign GPU ======
export CUDA_VISIBLE_DEVICES=$IDX

echo "Running on GPU $CUDA_VISIBLE_DEVICES for input: $INPUT"
echo "Output directory: $OUTPUT"

marker "$INPUT" \
    --output_dir "$OUTPUT" \
    --output_format markdown \
    --extract_images true \
    --workers 5

echo "Completed $INPUT → $OUTPUT"