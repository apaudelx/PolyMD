import re
from transformers import pipeline

# 1) Build once
clf = pipeline("zero-shot-classification",
               model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")

# 2) Labels
POSITIVE_LABELS = [
    "polymer molecular dynamics with force fields",
    "all-atom polymer molecular dynamics",
    "united-atom polymer molecular dynamics",
    "coarse-grained polymer MD (MARTINI)",
    "reactive polymer MD (ReaxFF)",
    "polymer melt or solution MD",
    "MD of polymer blends or copolymers",
    "polymer MD using LAMMPS or GROMACS",
    "polymer MD with OPLS/AMBER/CHARMM/COMPASS/DREIDING/PCFF/GROMOS/TraPPE",
]
# Property-focused positives (strong signal for prioritization)
PROPERTY_LABELS = [
    "polymer properties from MD (viscosity, diffusion, Tg)",
    "MD evaluation of polymer viscosity (rheology)",
    "MD estimation of polymer glass transition temperature (Tg)",
    "MD calculation of polymer diffusion or self-diffusion",
    "MD calculation of polymer mechanical properties (Young's modulus, stress–strain)",
    "MD prediction of polymer density or radius of gyration",
    "MD calculation of polymer transport or permeability",
]

NEGATIVE_LABELS = [
    "experimental polymer rheology (no simulation)",
    "polymer synthesis or characterization (no simulation)",
    "quantum chemistry or DFT (no MD)",
    "Monte Carlo simulations (not MD)",
    "dissipative particle dynamics (DPD) without atomistic force fields",
    "continuum modeling or FEM/CFD (no MD)",
    "biomolecular MD (proteins/DNA, not polymers)",
    "materials science unrelated to polymers",
    "machine learning predictions without MD simulation",
    "review article (survey)"
]

LABELS = POSITIVE_LABELS + PROPERTY_LABELS + NEGATIVE_LABELS

# 3) Keyword prefilters
MD_TERMS = [
    r"\bmolecular dynamics\b", r"\bMD\b", r"\bMD simulation(s)?\b",
    r"\bLAMMPS\b", r"\bGROMACS\b", r"\bNAMD\b"
]
FF_TERMS = [
    r"\bforce[- ]field\b", r"\bOPLS\b", r"\bAMBER\b", r"\bCHARMM\b", r"\bCOMPASS\b",
    r"\bDREIDING\b", r"\bPCFF\b", r"\bGROMOS\b", r"\bTraPPE\b", r"\bMARTINI\b", r"\bReaxFF\b",
    r"\bcoarse[- ]grained\b", r"\bunited[- ]atom\b", r"\ball[- ]atom\b"
]
PROPERTY_TERMS = [
    r"\bviscosit(y|ies)\b", r"\brheolog(y|ical)\b",
    r"\bglass transition\b", r"\bTg\b",
    r"\bdiffus(ion|ivity)\b", r"\bself[- ]diffus(ion|ivity)\b",
    r"\bYoung'?s modulus\b", r"\belastic modulus\b", r"\bstress[-–]strain\b",
    r"\bdensity\b", r"\bradius of gyration\b", r"\bR[gG]\b",
    r"\bpermeabilit(y|ies)\b", r"\btransport\b", r"\bthermal conductivity\b",
    r"\bdielectric (constant|permittivity)\b", r"\bconductivity\b"
]

def prefilter(text: str) -> bool:
    t = text.lower()
    has_poly = ("polymer" in t) or ("polymeric" in t)
    md_hit  = any(re.search(p, text, re.I) for p in MD_TERMS)
    ff_hit  = any(re.search(p, text, re.I) for p in FF_TERMS)
    return has_poly and (md_hit or ff_hit)

def decide(abstract_text: str,
           accept_threshold=0.70, accept_margin=0.15,
           priority_threshold=0.65, priority_margin=0.10):
    """
    Returns dict with:
      accept: bool  -> keep as polymer MD paper
      priority: bool -> prioritize (likely evaluates properties via MD)
      score_pos, score_neg, score_prop, priority_score, top: diagnostics
    """
    if not prefilter(abstract_text):
        return {"accept": False, "priority": False, "reason": "fails keyword prefilter",
                "score_pos": 0.0, "score_neg": 0.0, "score_prop": 0.0,
                "priority_score": 0.0, "top": []}

    res = clf(
        abstract_text,
        candidate_labels=LABELS,
        hypothesis_template="This abstract is about {}.",
        multi_label=True
    )
    score_map = dict(zip(res["labels"], res["scores"]))

    score_pos  = max(score_map.get(k, 0.0) for k in POSITIVE_LABELS)
    score_neg  = max(score_map.get(k, 0.0) for k in NEGATIVE_LABELS)
    score_prop = max(score_map.get(k, 0.0) for k in PROPERTY_LABELS)

    # property keyword boost
    prop_kw = any(re.search(p, abstract_text, re.I) for p in PROPERTY_TERMS)
    kw_boost = 0.05 if prop_kw else 0.0

    # composite priority score: emphasize property evidence
    priority_score = 0.7*score_prop + 0.3*score_pos + kw_boost

    top = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:6]

    accept = (score_pos >= accept_threshold) and ((score_pos - score_neg) >= accept_margin)
    priority = (priority_score >= priority_threshold) and ((score_prop - score_neg) >= priority_margin)

    return {
        "accept": bool(accept),
        "priority": bool(priority),
        "reason": ("pos high & margin over neg" if accept else "pos low or margin small"),
        "score_pos": float(score_pos),
        "score_neg": float(score_neg),
        "score_prop": float(score_prop),
        "priority_score": float(priority_score),
        "prop_keywords": bool(prop_kw),
        "top": top
    }

# ==== DataLoader-based batching (no change to core logic) ====
import os
import csv
from glob import glob
import torch
from torch.utils.data import Dataset, DataLoader

INPUT_DIR = "abstract"                  # folder with abstract1.txt, abstract2.txt, ...
OUTPUT_CSV = "abstract_decisions.csv"   # writes: filename,accept
BATCH_SIZE = 16                         # tune for GPU RAM
NUM_WORKERS = 0                         # >0 to parallelize file I/O (set carefully on HPC)

if not os.path.isdir(INPUT_DIR):
    raise FileNotFoundError(f"Input folder '{INPUT_DIR}' not found.")

files = sorted(glob(os.path.join(INPUT_DIR, "*.txt")))
if not files:
    raise FileNotFoundError(f"No .txt files found in '{INPUT_DIR}'.")

class AbstractFolder(Dataset):
    def __init__(self, filepaths):
        self.filepaths = filepaths
    def __len__(self):
        return len(self.filepaths)
    def __getitem__(self, idx):
        path = self.filepaths[idx]
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read().strip()
        return {"filename": os.path.basename(path), "text": text}

def collate_fn(batch):
    # batch: list of dicts
    filenames = [b["filename"] for b in batch]
    texts     = [b["text"] for b in batch]
    return {"filename": filenames, "text": texts}

loader = DataLoader(
    AbstractFolder(files),
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    collate_fn=collate_fn,
    pin_memory=False
)

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["filename", "accept"])

    for batch in loader:
        filenames = batch["filename"]
        texts = batch["text"]

        # 1) Prefilter (cheap) — same as decide()
        mask = [prefilter(t) for t in texts]

        # Initialize all as False (fails prefilter => accept False)
        accepts = [False] * len(texts)

        # 2) Run pipeline ONLY on those passing prefilter, in one batched call
        to_run_indices = [i for i, m in enumerate(mask) if m]
        if to_run_indices:
            run_texts = [texts[i] for i in to_run_indices]
            outputs = clf(
                run_texts,
                candidate_labels=LABELS,
                hypothesis_template="This abstract is about {}.",
                multi_label=True,
                batch_size=BATCH_SIZE,
            )
            # Ensure list
            if isinstance(outputs, dict):
                outputs = [outputs]

            # 3) Compute accept using EXACT same math as decide()
            for local_idx, out in enumerate(outputs):
                score_map = dict(zip(out["labels"], out["scores"]))
                score_pos  = max(score_map.get(k, 0.0) for k in POSITIVE_LABELS)
                score_neg  = max(score_map.get(k, 0.0) for k in NEGATIVE_LABELS)
                score_prop = max(score_map.get(k, 0.0) for k in PROPERTY_LABELS)

                # property keyword boost present in decide(), but it only affects priority;
                # accept decision depends on score_pos and score_neg only.
                accept = (score_pos >= 0.70) and ((score_pos - score_neg) >= 0.15)

                global_idx = to_run_indices[local_idx]
                accepts[global_idx] = bool(accept)

        # 4) Emit rows for this batch
        for fn, acc in zip(filenames, accepts):
            writer.writerow([fn, acc])

print(f"Saved {len(files)} rows to {OUTPUT_CSV}")

