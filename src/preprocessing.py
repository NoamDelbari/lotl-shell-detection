"""
preprocessing.py -- dataset-agnostic transforms, all leakage-safe by design.

Nothing here knows which dataset it is fed. The two representations the pipeline
supports are both built as sklearn transformers so they can live *inside* a
Pipeline and therefore be fit strictly on the training fold of each CV split
(assignment: "any sampling or scaling must be fit strictly on the training
fold"). We never fit a scaler on the full data and slice afterwards.

    EngineeredFeatures : raw command strings -> featurize() numeric matrix
                         (feeds XGBoost / Random Forest / Isolation Forest)
    CharSequenceEncoder: raw command strings -> fixed-length char-index matrix
                         (feeds the 1D-CNN)

Both expose the sklearn fit/transform API. EngineeredFeatures is stateless at
fit time (the feature definition is fixed), but is still a transformer so a
downstream StandardScaler inside the same Pipeline is the thing that learns
fold-local statistics.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from .features import FEATURE_NAMES, featurize


def _as_str_array(X):
    return np.asarray(X, dtype=object).ravel()


class EngineeredFeatures(BaseEstimator, TransformerMixin):
    """Raw commands -> engineered numeric matrix (order == FEATURE_NAMES)."""

    def fit(self, X, y=None):
        self.feature_names_ = list(FEATURE_NAMES)
        return self

    def transform(self, X):
        return featurize(_as_str_array(X)).to_numpy(dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FEATURE_NAMES, dtype=object)


class CharNgramFeatures(BaseEstimator, TransformerMixin):
    """Raw commands -> character n-gram TF-IDF sparse matrix.

    Motivated directly by Ch2: ShellCore shows character-level n-grams carry the
    short, symbol-dense signal (`||`, `>&`, `/dev/tcp`, base64 runs) that whole-
    token features miss. The vocabulary is learned on the training fold only
    (TfidfVectorizer is fit inside the model Pipeline), so this stays leakage-
    safe under cross-validation.
    """

    def __init__(self, ngram_range=(3, 5), min_df: int = 3,
                 max_features: int = 3000):
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_features = max_features

    def fit(self, X, y=None):
        self.vectorizer_ = TfidfVectorizer(
            analyzer="char_wb", ngram_range=self.ngram_range,
            min_df=self.min_df, max_features=self.max_features)
        self.vectorizer_.fit(_as_str_array(X))
        return self

    def transform(self, X):
        return self.vectorizer_.transform(_as_str_array(X))


def build_hybrid_features(ngram_range=(3, 5), min_df: int = 3,
                          max_features: int = 3000) -> FeatureUnion:
    """Engineered features (interpretable) UNION char n-gram TF-IDF (coverage).

    The combination is what lifts the tree models from the engineered-only F1
    (~0.76) to ~0.86 while keeping the engineered block available for the Ch4
    importance story. Fit inside the model Pipeline => fold-local, no leakage.
    """
    return FeatureUnion([
        ("engineered", EngineeredFeatures()),
        ("char_ngram", CharNgramFeatures(ngram_range=ngram_range,
                                         min_df=min_df,
                                         max_features=max_features)),
    ])


class CharSequenceEncoder(BaseEstimator, TransformerMixin):
    """Raw commands -> (n, max_len) int matrix of char indices.

    Vocabulary is learned on the training fold only (index 0 = pad,
    1 = out-of-vocabulary). max_len is a fixed hyperparameter so the tensor
    shape is dataset-independent.
    """

    def __init__(self, max_len: int = 256, max_vocab: int = 128):
        self.max_len = max_len
        self.max_vocab = max_vocab

    def fit(self, X, y=None):
        from collections import Counter
        counts = Counter()
        for s in _as_str_array(X):
            counts.update(str(s))
        vocab = [c for c, _ in counts.most_common(self.max_vocab - 2)]
        # 0 = pad, 1 = OOV, then most-common chars
        self.char_to_idx_ = {c: i + 2 for i, c in enumerate(vocab)}
        self.vocab_size_ = len(self.char_to_idx_) + 2
        return self

    def transform(self, X):
        out = np.zeros((len(_as_str_array(X)), self.max_len), dtype=np.int64)
        for row, s in enumerate(_as_str_array(X)):
            s = str(s)[: self.max_len]
            for col, ch in enumerate(s):
                out[row, col] = self.char_to_idx_.get(ch, 1)
        return out
