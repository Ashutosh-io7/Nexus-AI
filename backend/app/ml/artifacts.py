"""Save and load trained models. Only load files that Nexus itself saved."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import joblib

from app.ml.features import FeatureSpec
from app.ml.training import TrainingResult

# backend/models_store/churn  (ignored by Git)
DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "models_store" / "churn"


class ModelUnusableError(RuntimeError):
    """A saved model exists but cannot be used (for example, it is too old)."""


def save_model(result: TrainingResult, base_dir: Optional[Path] = None) -> Path:
    base_dir = Path(base_dir or DEFAULT_MODELS_DIR)
    version = result.metadata["version"]
    target = base_dir / version
    target.mkdir(parents=True, exist_ok=False)

    joblib.dump(
        {
            "pipeline": result.pipeline,
            "feature_spec": asdict(result.spec),
            "metadata": result.metadata,
            "training_customer_ids": result.training_customer_ids,
        },
        target / "model.joblib",
    )
    (target / "metadata.json").write_text(
        json.dumps(result.metadata, indent=2), encoding="utf-8"
    )
    (base_dir / "CURRENT").write_text(version, encoding="utf-8")
    return target


def current_model_version(base_dir: Optional[Path] = None) -> Optional[str]:
    """The current model's version, read without loading the model itself."""
    pointer = Path(base_dir or DEFAULT_MODELS_DIR) / "CURRENT"
    if not pointer.exists():
        return None
    return pointer.read_text(encoding="utf-8").strip() or None


def load_current_model(base_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Return the current model, or None when no model has been trained yet."""
    base_dir = Path(base_dir or DEFAULT_MODELS_DIR)
    version = current_model_version(base_dir)
    if version is None:
        return None

    model_file = base_dir / version / "model.joblib"
    if not model_file.exists():
        return None

    stored = joblib.load(model_file)
    if "training_customer_ids" not in stored:
        raise ModelUnusableError(
            "The saved model is from an older version of Nexus. "
            "Train it again with: python -m app.ml.train_cli"
        )
    return {
        "pipeline": stored["pipeline"],
        "feature_spec": FeatureSpec(**stored["feature_spec"]),
        "metadata": stored["metadata"],
        "training_customer_ids": set(stored["training_customer_ids"]),
    }