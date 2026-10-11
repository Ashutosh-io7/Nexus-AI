"""Train a churn model from the customers stored in Nexus.

Run from the backend folder:  python -m app.ml.train_cli
"""

from __future__ import annotations

import sys

import pandas as pd
from sqlalchemy import select

from app.db.session import SessionLocal
from app.ml.artifacts import save_model
from app.ml.features import customers_to_frame
from app.ml.training import CV_FOLDS, TrainingDataError, train_churn_model
from app.models.customer import Customer


def format_report(metadata: dict) -> str:
    data = metadata["data"]
    feats = metadata["features"]
    selected = metadata["algorithm"]
    lines = [
        "NEXUS CHURN MODEL: TRAINING REPORT",
        "=" * 40,
        f"Customers with a known outcome: {data['labeled_customers']:,} "
        f"({data['churn_rate']:.1%} left)",
        f"Training rows: {data['train_rows']:,}   Held-out test rows: {data['test_rows']:,}",
        "",
        f"Features used: {len(feats['numeric'])} numeric, {len(feats['categorical'])} categorical",
        "  numeric:     " + (", ".join(feats["numeric"]) or "none"),
        "  categorical: " + (", ".join(feats["categorical"]) or "none"),
    ]
    if feats["dropped"]:
        lines.append("Left out:")
        for column, reason in feats["dropped"].items():
            lines.append(f"  {column}: {reason}")

    lines += ["", f"Model comparison ({CV_FOLDS}-fold cross-validation on training rows)"]
    for name, s in metadata["cross_validation"].items():
        lines.append(
            f"  {name:20} ROC-AUC {s['roc_auc_mean']:.3f} +/- {s['roc_auc_std']:.3f}"
            f"   PR-AUC {s['pr_auc_mean']:.3f} +/- {s['pr_auc_std']:.3f}"
        )
    lines.append(f"Selected: {selected}")

    lines += ["", "Held-out test results (threshold 0.5)"]
    for name, m in metadata["test_metrics"].items():
        marker = "  <- selected" if name == selected else ""
        lines.append(
            f"  {name:20} ROC-AUC {m['roc_auc']:.3f}  PR-AUC {m['pr_auc']:.3f}  "
            f"precision {m['precision']:.2f}  recall {m['recall']:.2f}  F1 {m['f1']:.2f}  "
            f"Brier {m['brier']:.3f}{marker}"
        )
    chosen = metadata["test_metrics"][selected]
    c = chosen["confusion"]
    lines += [
        f"  (PR-AUC of a model with no skill would be about {chosen['churn_rate_in_test']:.3f})",
        "",
        f"Selected model on the test rows ({sum(c.values()):,} customers):",
        f"  Correctly flagged as leaving: {c['true_positive']:,}",
        f"  Missed (left, but not flagged): {c['false_negative']:,}",
        f"  Flagged but stayed:            {c['false_positive']:,}",
        f"  Correctly not flagged:         {c['true_negative']:,}",
        "",
        "Flagging threshold trade-off (selected model)",
        "  threshold  precision  recall  share of customers flagged",
    ]
    for row in chosen["trade_off"]:
        lines.append(
            f"  {row['threshold']:<9.1f}  {row['precision']:<9.2f}  {row['recall']:<6.2f}  "
            f"{row['share_flagged']:.1%}"
        )
    return "\n".join(lines)


def main() -> int:
    with SessionLocal() as db:
        customers = db.scalars(
            select(Customer).where(Customer.churned.is_not(None))
        ).all()

    if not customers:
        print("No customers with a known outcome yet. Import data that has a churn column.")
        return 1

    frame = customers_to_frame(customers)
    labels = pd.Series([1 if c.churned else 0 for c in customers])

    try:
        result = train_churn_model(frame, labels)
    except TrainingDataError as error:
        print(f"Cannot train a model: {error}")
        return 1

    saved_to = save_model(result)
    print(format_report(result.metadata))
    print(f"\nModel saved to: {saved_to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())