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
        },
        target / "model.joblib",
    )
    (target / "metadata.json").write_text(
        json.dumps(result.metadata, indent=2), encoding="utf-8"
    )
    (base_dir / "CURRENT").write_text(version, encoding="utf-8")
    return target


def load_current_model(base_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Return the current model, or None when no model has been trained yet."""
    base_dir = Path(base_dir or DEFAULT_MODELS_DIR)
    pointer = base_dir / "CURRENT"
    if not pointer.exists():
        return None

    model_file = base_dir / pointer.read_text(encoding="utf-8").strip() / "model.joblib"
    if not model_file.exists():
        return None

    stored = joblib.load(model_file)
    return {
        "pipeline": stored["pipeline"],
        "feature_spec": FeatureSpec(**stored["feature_spec"]),
        "metadata": stored["metadata"],
    }