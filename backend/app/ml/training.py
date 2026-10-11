"""Train, compare and evaluate churn models. No database code lives here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from app.ml.features import FeatureSpec, infer_feature_spec, prepare_matrix

MIN_LABELED_ROWS = 200
MIN_PER_CLASS = 30
TEST_SIZE = 0.2
CV_FOLDS = 5
THRESHOLD = 0.5
# XGBoost must beat the simpler baseline by this much (PR-AUC) to be chosen.
MIN_GAIN_OVER_BASELINE = 0.005
BASELINE = "logistic_regression"


class TrainingDataError(ValueError):
    """The data is not enough to train an honest model."""


@dataclass
class TrainingResult:
    pipeline: Pipeline
    spec: FeatureSpec
    metadata: dict[str, Any]


def build_preprocessor(spec: FeatureSpec) -> ColumnTransformer:
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer(
        [("num", numeric, spec.numeric), ("cat", categorical, spec.categorical)],
        sparse_threshold=0,
    )


def candidate_models(random_state: int) -> dict[str, Any]:
    return {
        BASELINE: LogisticRegression(max_iter=1000),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=1,
        ),
    }


def evaluate(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
    proba = pipeline.predict_proba(X)[:, 1]
    pred = (proba >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()

    trade_off = []
    for t in (0.2, 0.3, 0.4, 0.5):
        flagged = (proba >= t).astype(int)
        trade_off.append({
            "threshold": t,
            "precision": float(precision_score(y, flagged, zero_division=0)),
            "recall": float(recall_score(y, flagged, zero_division=0)),
            "share_flagged": float(flagged.mean()),
        })

    return {
        "threshold": THRESHOLD,
        "roc_auc": float(roc_auc_score(y, proba)),
        "pr_auc": float(average_precision_score(y, proba)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, proba)),
        "churn_rate_in_test": float(np.mean(y)),  # a model with no skill gets this PR-AUC
        "confusion": {
            "true_negative": int(tn), "false_positive": int(fp),
            "false_negative": int(fn), "true_positive": int(tp),
        },
        "trade_off": trade_off,
    }


def train_churn_model(
    frame: pd.DataFrame, labels: pd.Series, random_state: int = 42
) -> TrainingResult:
    labels = pd.Series(labels).astype(int).reset_index(drop=True)
    frame = frame.reset_index(drop=True)

    if len(frame) != len(labels):
        raise TrainingDataError("Features and labels have different lengths.")
    if not set(labels.unique()) <= {0, 1}:
        raise TrainingDataError("Labels must be 0 (stayed) or 1 (left).")
    if len(labels) < MIN_LABELED_ROWS:
        raise TrainingDataError(
            f"Only {len(labels)} customers have a known outcome. "
            f"At least {MIN_LABELED_ROWS} are needed to train a model."
        )
    counts = labels.value_counts()
    if counts.get(0, 0) < MIN_PER_CLASS or counts.get(1, 0) < MIN_PER_CLASS:
        raise TrainingDataError(
            f"Need at least {MIN_PER_CLASS} customers who stayed and {MIN_PER_CLASS} "
            f"who left. Found {counts.get(0, 0)} stayed and {counts.get(1, 0)} left."
        )

    frame_train, frame_test, y_train, y_test = train_test_split(
        frame, labels, test_size=TEST_SIZE, stratify=labels, random_state=random_state
    )

    spec = infer_feature_spec(frame_train)  # learned from training rows only
    if not spec.columns:
        raise TrainingDataError("No usable feature columns were found.")

    X_train = prepare_matrix(frame_train, spec)
    X_test = prepare_matrix(frame_test, spec)

    pipelines = {
        name: Pipeline([("prep", build_preprocessor(spec)), ("model", model)])
        for name, model in candidate_models(random_state).items()
    }

    # Choose between models using cross-validation on the TRAINING rows only,
    # so the held-out test rows stay untouched until the final report.
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=random_state)
    cv_scores: dict[str, dict[str, float]] = {}
    for name, pipeline in pipelines.items():
        scores = cross_validate(
            clone(pipeline), X_train, y_train, cv=cv,
            scoring={"roc_auc": "roc_auc", "pr_auc": "average_precision"},
            error_score="raise",  # a failing model must stop training, never be skipped silently
        )
        cv_scores[name] = {
            "roc_auc_mean": float(scores["test_roc_auc"].mean()),
            "roc_auc_std": float(scores["test_roc_auc"].std()),
            "pr_auc_mean": float(scores["test_pr_auc"].mean()),
            "pr_auc_std": float(scores["test_pr_auc"].std()),
        }

    selected = BASELINE
    best_challenger = max(
        (n for n in pipelines if n != BASELINE), key=lambda n: cv_scores[n]["pr_auc_mean"]
    )
    if cv_scores[best_challenger]["pr_auc_mean"] >= cv_scores[BASELINE]["pr_auc_mean"] + MIN_GAIN_OVER_BASELINE:
        selected = best_challenger

    test_metrics: dict[str, Any] = {}
    for name, pipeline in pipelines.items():
        pipeline.fit(X_train, y_train)
        test_metrics[name] = evaluate(pipeline, X_test, y_test)

    now = datetime.now(timezone.utc)
    metadata = {
        "version": now.strftime("%Y%m%dT%H%M%SZ"),
        "trained_at": now.isoformat(),
        "algorithm": selected,
        "selected_by": (
            f"highest cross-validated PR-AUC on the training rows; "
            f"{best_challenger} must beat {BASELINE} by {MIN_GAIN_OVER_BASELINE} to be chosen"
        ),
        "data": {
            "labeled_customers": int(len(labels)),
            "churn_rate": float(labels.mean()),
            "train_rows": int(len(y_train)),
            "test_rows": int(len(y_test)),
            "test_size": TEST_SIZE,
            "random_state": random_state,
        },
        "features": {
            "numeric": spec.numeric,
            "categorical": spec.categorical,
            "dropped": spec.dropped,
        },
        "cross_validation": cv_scores,
        "test_metrics": test_metrics,
        "library_versions": {
            "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    return TrainingResult(pipeline=pipelines[selected], spec=spec, metadata=metadata)