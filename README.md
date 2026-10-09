# leaf_mlops

Explainable hierarchical classification of tree species (family, genus, species) from leaf
images using deep learning and computer vision. Final Degree Project (TFG), Universidad
Complutense de Madrid.

## Repository layout

```
src/leaf_mlops/   Python package (data, models, explain)
datasets/         One directory per dataset (documentation only; data is not versioned)
configs/          Experiment configuration files
docs/             Documentation, data, and surveys developed for this thesis
report/           LaTeX thesis (see report/README.md)
```

## Installation

### Linux / macOS

```bash
git clone https://github.com/KaTVasq/leaf_mlops.git
cd leaf_mlops
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Windows (PowerShell)

```powershell
git clone https://github.com/KaTVasq/leaf_mlops.git
cd leaf_mlops
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

If PowerShell blocks the activation script, run
`Set-ExecutionPolicy -Scope Process RemoteSigned` first.

## Thesis report
The LaTeX source is in `report/`.
