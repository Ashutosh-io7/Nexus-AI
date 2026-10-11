"""Turn stored customers into a table a model can learn from.

Nexus works with many kinds of businesses, so the model cannot rely on a fixed
list of columns. It learns from the typed columns Nexus knows about AND from
the "extra data" that came with each customer's file.

Rules that keep this honest:
- Names, emails and company names are never used (they identify, not predict).
- A missing value stays missing. It is never turned into 0 by this module.
- The same rules are used when training and when predicting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

ID_COLUMN = "customer_id"
EXTRA_PREFIX = "extra__"

TYPED_NUMERIC = (
    "tenure_months",
    "monthly_revenue",
    "usage_minutes_last_30d",
    "logins_last_30d",
    "active_days_last_30d",
    "support_ticket_count",
    "unresolved_ticket_count",
    "payment_failures",
)
TYPED_CATEGORICAL = ("subscription_plan",)

# last_active_at is left out on purpose: how long ago it was depends on the day
# the model runs, so it would mean different things in training and later use.

MAX_CATEGORIES = 30        # more distinct values than this: looks like an ID or free text
MIN_FILLED_SHARE = 0.5     # a column that is mostly empty is not used
NUMERIC_PARSE_SHARE = 0.95  # share of values that must look like numbers


@dataclass
class FeatureSpec:
    """Which columns the model uses. Saved with the model."""

    numeric: list[str] = field(default_factory=list)
    categorical: list[str] = field(default_factory=list)
    dropped: dict[str, str] = field(default_factory=dict)

    @property
    def columns(self) -> list[str]:
        return self.numeric + self.categorical


def customers_to_frame(customers: Iterable[Any]) -> pd.DataFrame:
    """One row per customer. Extra data columns get an 'extra__' prefix."""
    rows = []
    for customer in customers:
        row: dict[str, Any] = {ID_COLUMN: customer.id}
        for name in TYPED_NUMERIC:
            value = getattr(customer, name)
            row[name] = float(value) if value is not None else np.nan
        for name in TYPED_CATEGORICAL:
            row[name] = getattr(customer, name)
        for key, value in (customer.source_attributes or {}).items():
            row[f"{EXTRA_PREFIX}{key}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def infer_feature_spec(frame: pd.DataFrame) -> FeatureSpec:
    """Decide which columns are usable. Call this on TRAINING rows only."""
    spec = FeatureSpec()
    n_rows = len(frame)

    for column in frame.columns:
        if column == ID_COLUMN:
            continue

        filled = frame[column].dropna()
        if n_rows == 0 or len(filled) / n_rows < MIN_FILLED_SHARE:
            spec.dropped[column] = "mostly empty"
            continue

        text = filled.astype(str).str.strip()
        distinct = text.nunique()
        if distinct <= 1:
            spec.dropped[column] = "same value for every customer"
            continue

        if column in TYPED_NUMERIC:
            spec.numeric.append(column)
            continue

        looks_numeric = pd.to_numeric(filled, errors="coerce").notna().mean() >= NUMERIC_PARSE_SHARE
        if looks_numeric and column not in TYPED_CATEGORICAL:
            spec.numeric.append(column)
        elif distinct <= MAX_CATEGORIES and distinct / len(filled) < 0.5:
            spec.categorical.append(column)
        else:
            spec.dropped[column] = "too many distinct values (looks like an ID or free text)"

    return spec


def _clean_text(value: Any) -> Any:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    return text if text else np.nan


def prepare_matrix(frame: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame:
    """Build exactly the columns the model expects. Missing stays missing (NaN)."""
    out = pd.DataFrame(index=frame.index)

    for column in spec.numeric:
        values = frame[column] if column in frame.columns else pd.Series(np.nan, index=frame.index)
        out[column] = pd.to_numeric(values, errors="coerce").astype(float)

    for column in spec.categorical:
        values = frame[column] if column in frame.columns else pd.Series(np.nan, index=frame.index)
        out[column] = values.astype(object).map(_clean_text).astype(object)

    return out