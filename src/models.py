"""
models.py -- the four models, each as a self-contained sklearn-compatible
estimator that takes RAW command strings as X.

    XGBoost          traditional supervised   (Ben)
    1D-CNN           deep learning, char seq  (Ben)
    RandomForest     traditional supervised   (Noam)
    IsolationForest  unsupervised anomaly     (Noam)

Every model exposes fit(X, y) / predict(X) / predict_proba(X) where X is a 1-D
array of command strings, so `evaluation.py` treats them uniformly and the
cascading ensemble (Ch8.4) can chain them without special-casing.

Why raw strings in, features inside: putting EngineeredFeatures /
CharSequenceEncoder and the scaler *inside* each Pipeline means every transform
that learns anything (scaler stats, char vocabulary, a SMOTE sampler) is fit on
the training fold only during cross-validation. That is the no-leakage
guarantee, enforced structurally rather than by convention.

Explicit hyperparameters only -- no library defaults are relied upon
(assignment Step 7). Each builder takes keyword hyperparameters so the
sensitivity sweeps in Ch7 can vary one axis at a time.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# imblearn's Pipeline is a drop-in for sklearn's that also runs samplers only on
# the training fold. We use it everywhere so switching a model to SMOTE is a
# one-line change that stays leakage-safe.
from imblearn.pipeline import Pipeline as ImbPipeline

from . import SEED
from .preprocessing import (CharSequenceEncoder, EngineeredFeatures,
                            build_hybrid_features)


# --------------------------------------------------------------------------- #
# 1. XGBoost (Ben)                                                            #
# --------------------------------------------------------------------------- #
def build_xgboost(
    n_estimators: int = 400,
    max_depth: int = 6,
    learning_rate: float = 0.1,
    subsample: float = 0.9,
    colsample_bytree: float = 0.9,
    min_child_weight: float = 1.0,
    reg_lambda: float = 1.0,
    reg_alpha: float = 0.0,
    scale_pos_weight: float = 3.0,   # ~ n_neg/n_pos at the 1:3 ratio
) -> ImbPipeline:
    """Gradient-boosted trees on engineered features.

    scale_pos_weight is the cost-sensitive imbalance remedy: it multiplies the
    gradient of the positive (malicious) class so the 1:3 prevalence does not
    push the model toward the benign majority.
    """
    from xgboost import XGBClassifier

    clf = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        min_child_weight=min_child_weight,
        reg_lambda=reg_lambda,
        reg_alpha=reg_alpha,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=0,
        random_state=SEED,
    )
    return ImbPipeline([
        ("features", EngineeredFeatures()),
        ("scale", StandardScaler()),
        ("clf", clf),
    ])


def build_xgboost_hybrid(
    n_estimators: int = 500,
    max_depth: int = 7,
    learning_rate: float = 0.1,
    subsample: float = 0.9,
    colsample_bytree: float = 0.7,
    min_child_weight: float = 1.0,
    reg_lambda: float = 1.0,
    reg_alpha: float = 0.0,
    scale_pos_weight: float = 3.0,
    ngram_range=(3, 5),
    max_features: int = 3000,
) -> ImbPipeline:
    """XGBoost on engineered features UNION char n-gram TF-IDF.

    This is the strong headline traditional-supervised model: the char n-grams
    (Ch2/ShellCore) add the lexical coverage the engineered block lacks, lifting
    F1 from ~0.76 to ~0.86 on both datasets. No scaler: trees are scale-invariant
    and the char block is sparse. Everything is fit in-fold => leakage-safe.
    """
    from xgboost import XGBClassifier

    clf = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        min_child_weight=min_child_weight,
        reg_lambda=reg_lambda,
        reg_alpha=reg_alpha,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=0,
        random_state=SEED,
    )
    return ImbPipeline([
        ("features", build_hybrid_features(ngram_range=ngram_range,
                                           max_features=max_features)),
        ("clf", clf),
    ])


# --------------------------------------------------------------------------- #
# 2. Random Forest (Noam) -- built here so the skeleton runs before hand-off  #
# --------------------------------------------------------------------------- #
def build_random_forest(
    n_estimators: int = 400,
    max_depth: int = 24,
    min_samples_leaf: int = 1,
    max_features: str = "sqrt",
    class_weight: str = "balanced_subsample",
) -> ImbPipeline:
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        class_weight=class_weight,
        n_jobs=-1,
        random_state=SEED,
    )
    return ImbPipeline([
        ("features", EngineeredFeatures()),
        ("scale", StandardScaler()),
        ("clf", clf),
    ])


# --------------------------------------------------------------------------- #
# 3. Isolation Forest (Noam) -- unsupervised, trained on benign only          #
# --------------------------------------------------------------------------- #
class IsolationForestDetector(BaseEstimator, ClassifierMixin):
    """Anomaly detector wrapped to look like a binary classifier.

    Fit on the BENIGN training rows only (unsupervised: it never sees malicious
    labels), then score every command. Higher anomaly score -> more malicious.
    predict_proba returns a min-max-normalised anomaly score in [0, 1] so it
    plugs into the same evaluation and the cascade's first stage.
    """

    def __init__(self, n_estimators: int = 300, max_samples: float = 0.8,
                 contamination: float = 0.25, max_features: float = 1.0):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.max_features = max_features

    def fit(self, X, y=None):
        self.pipeline_ = ImbPipeline([
            ("features", EngineeredFeatures()),
            ("scale", StandardScaler()),
        ])
        Xt = self.pipeline_.fit_transform(X)
        if y is not None:
            Xt = Xt[np.asarray(y) == 0]          # fit on benign only
        self.iso_ = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            max_features=self.max_features,
            n_jobs=-1,
            random_state=SEED,
        ).fit(Xt)
        raw = -self.iso_.score_samples(self.pipeline_.transform(X))
        self._lo, self._hi = float(raw.min()), float(raw.max())
        self.classes_ = np.array([0, 1])
        return self

    def decision_scores(self, X):
        raw = -self.iso_.score_samples(self.pipeline_.transform(X))
        span = self._hi - self._lo or 1.0
        return np.clip((raw - self._lo) / span, 0.0, 1.0)

    def predict_proba(self, X):
        p = self.decision_scores(X)
        return np.column_stack([1.0 - p, p])

    def predict(self, X):
        return (self.decision_scores(X) >= 0.5).astype(int)


def build_isolation_forest(**kw) -> IsolationForestDetector:
    return IsolationForestDetector(**kw)


# --------------------------------------------------------------------------- #
# 4. 1D-CNN over character sequences (Ben)                                     #
# --------------------------------------------------------------------------- #
class CNN1DClassifier(BaseEstimator, ClassifierMixin):
    """Character-level 1D convolutional net, sklearn-wrapped around PyTorch.

    Rationale (Ch6): a command line is a short 1-D signal of characters; the
    malicious signature is local n-gram structure ("|sh", "/dev/tcp",
    "base64 -d", "-i "). Stacked 1-D convolutions are translation-invariant
    local pattern detectors -- they fire on those motifs wherever they appear in
    the line, which is exactly the inductive bias this task wants.

    Imbalance is handled with a class-weighted cross-entropy (cost-sensitive),
    the sequence analogue of XGBoost's scale_pos_weight.
    """

    def __init__(self, max_len: int = 256, embed_dim: int = 32,
                 n_filters: int = 128, kernel_sizes=(3, 5, 7), dropout: float = 0.3,
                 lr: float = 1e-3, epochs: int = 8, batch_size: int = 256,
                 weight_decay: float = 1e-5, pos_weight: float = 3.0):
        self.max_len = max_len
        self.embed_dim = embed_dim
        self.n_filters = n_filters
        self.kernel_sizes = kernel_sizes
        self.dropout = dropout
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.weight_decay = weight_decay
        self.pos_weight = pos_weight

    # -- torch module built lazily so importing this file needs no GPU/torch -- #
    def _build_net(self, vocab_size):
        import torch.nn as nn

        class _Net(nn.Module):
            def __init__(self, vocab, embed_dim, n_filters, ks, dropout):
                super().__init__()
                self.embed = nn.Embedding(vocab, embed_dim, padding_idx=0)
                self.convs = nn.ModuleList([
                    nn.Conv1d(embed_dim, n_filters, k, padding=k // 2)
                    for k in ks
                ])
                self.dropout = nn.Dropout(dropout)
                self.fc = nn.Linear(n_filters * len(ks), 2)

            def forward(self, x):
                import torch
                e = self.embed(x).transpose(1, 2)            # (B, embed, L)
                feats = [torch.relu(c(e)).max(dim=2).values   # global max pool
                         for c in self.convs]
                h = self.dropout(torch.cat(feats, dim=1))
                return self.fc(h)

        return _Net(vocab_size, self.embed_dim, self.n_filters,
                    tuple(self.kernel_sizes), self.dropout)

    def fit(self, X, y):
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        torch.manual_seed(SEED)
        self.encoder_ = CharSequenceEncoder(max_len=self.max_len)
        Xt = self.encoder_.fit_transform(X)
        y = np.asarray(y).astype(np.int64)

        self.device_ = torch.device("cpu")
        self.net_ = self._build_net(self.encoder_.vocab_size_).to(self.device_)
        opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr,
                               weight_decay=self.weight_decay)
        w = torch.tensor([1.0, float(self.pos_weight)], dtype=torch.float32)
        loss_fn = torch.nn.CrossEntropyLoss(weight=w)

        ds = TensorDataset(torch.from_numpy(Xt), torch.from_numpy(y))
        dl = DataLoader(ds, batch_size=self.batch_size, shuffle=True)
        self.net_.train()
        for _ in range(self.epochs):
            for xb, yb in dl:
                opt.zero_grad()
                loss = loss_fn(self.net_(xb), yb)
                loss.backward()
                opt.step()
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        import torch
        self.net_.eval()
        Xt = torch.from_numpy(self.encoder_.transform(X))
        probs = []
        with torch.no_grad():
            for i in range(0, len(Xt), 1024):
                logits = self.net_(Xt[i:i + 1024])
                probs.append(torch.softmax(logits, dim=1).cpu().numpy())
        return np.vstack(probs)

    def predict(self, X):
        return self.predict_proba(X)[:, 1] >= 0.5


def build_cnn1d(**kw) -> CNN1DClassifier:
    return CNN1DClassifier(**kw)


# --------------------------------------------------------------------------- #
# registry -- the pipeline and CLI resolve models by name through this map     #
# --------------------------------------------------------------------------- #
MODEL_BUILDERS = {
    "xgboost": build_xgboost,
    "xgboost_hybrid": build_xgboost_hybrid,
    "cnn1d": build_cnn1d,
    "random_forest": build_random_forest,
    "isolation_forest": build_isolation_forest,
}

# owner tags (docs/WORK_DIVISION.md) -- used only for report bookkeeping
MODEL_OWNER = {
    "xgboost": "Ben", "xgboost_hybrid": "Ben", "cnn1d": "Ben",
    "random_forest": "Noam", "isolation_forest": "Noam",
}


def build_model(name: str, **hyperparams):
    if name not in MODEL_BUILDERS:
        raise KeyError(f"unknown model {name!r}; known: {sorted(MODEL_BUILDERS)}")
    return MODEL_BUILDERS[name](**hyperparams)
