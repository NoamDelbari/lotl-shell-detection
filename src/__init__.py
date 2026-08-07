"""
src -- modular detection pipeline for the final project (Ch7 skeleton).

Strict module sequence, mirroring the assignment:

    ingestion -> features -> preprocessing -> training -> evaluation

Dataset Dependency Rule: `ingestion` is the ONLY module allowed to know which
dataset it is reading. Everything downstream consumes the standard frame it
returns (columns: command, label, source) and must run unchanged when the
dataset is swapped. Grading depends on this; do not add dataset names anywhere
else.

Owners (docs/WORK_DIVISION.md): skeleton + XGBoost + 1D-CNN -- Ben;
featurize() + Random Forest + Isolation Forest -- Noam.
"""
SEED = 42


def _ensure_openmp():
    """XGBoost needs an OpenMP runtime (libomp) that Apple's system Python does
    not ship. On a Mac without Homebrew we borrow the copy that PyTorch bundles,
    so `import xgboost` works out of the box. No-op everywhere else. Harmless if
    libomp is already resolvable (the normal Linux / `brew install libomp` case).
    """
    import platform
    if platform.system() != "Darwin":
        return
    import ctypes
    import glob
    import os
    for base in (os.path.expanduser("~/Library/Python"), "/usr/local/lib",
                 "/opt/homebrew/lib"):
        for path in glob.glob(os.path.join(base, "**", "libomp.dylib"),
                              recursive=True):
            try:
                ctypes.CDLL(path)
                return
            except OSError:
                continue


_ensure_openmp()
