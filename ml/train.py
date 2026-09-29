"""Generate a synthetic rainfall/elevation/soil CSV and train RandomForestClassifier once.

IMPORTANT: The training data is SYNTHETIC. Labels come from ``label_from_rules``,
a hand-written threshold function -- there are no real flood observations. The
resulting model therefore produces an estimated rainfall-driven risk score, NOT
a validated real-world flood probability. Training accuracy says nothing about
real-world performance.

The model is saved with ``joblib`` and exposes ``predict_proba()``, which the
backend uses to compute P(HIGH) + P(SEVERE).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from risk import LEVEL_TO_INT, label_from_rules  # noqa: E402

CSV_PATH = ROOT / "train.csv"
MODEL_PATH = ROOT / "model.joblib"


def generate_rows(n: int = 400, seed: int = 42) -> list[tuple]:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        kind = rng.choice(["dry", "moderate", "heavy", "extreme"], p=[0.35, 0.3, 0.22, 0.13])
        if kind == "dry":
            r1, r6, r24 = rng.uniform(0, 3), rng.uniform(0, 9), rng.uniform(0, 20)
            elev = float(rng.uniform(0, 50))
            soil = float(rng.uniform(0.1, 0.35))
        elif kind == "moderate":
            r1, r6, r24 = rng.uniform(2, 12), rng.uniform(10, 24), rng.uniform(20, 60)
            elev = float(rng.uniform(0, 100))
            soil = float(rng.uniform(0.2, 0.45))
        elif kind == "heavy":
            r1, r6, r24 = rng.uniform(8, 28), rng.uniform(25, 49), rng.uniform(50, 100)
            elev = float(rng.uniform(0, 150))
            soil = float(rng.uniform(0.3, 0.6))
        else:
            r1, r6, r24 = rng.uniform(20, 55), rng.uniform(50, 90), rng.uniform(90, 180)
            elev = float(rng.uniform(0, 200))
            soil = float(rng.uniform(0.4, 0.8))
        r1, r6, r24 = round(float(r1), 2), round(float(r6), 2), round(float(r24), 2)
        elev = round(elev, 1)
        soil = round(soil, 4)
        level = label_from_rules(r1, r6, r24)
        rows.append((r1, r6, r24, elev, soil, LEVEL_TO_INT[level], level))
    return rows


def main() -> None:
    rows = generate_rows()
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rain_1h", "rain_6h", "rain_24h", "elevation_m", "soil_moisture", "label_int", "label"])
        w.writerows(rows)

    X = np.array([[r[0], r[1], r[2], r[3], r[4]] for r in rows], dtype=float)
    y = np.array([r[5] for r in rows], dtype=int)
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
    )
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    # Training accuracy is computed on the same synthetic rows used to fit, so
    # it reflects label consistency, not real-world performance.
    acc = float((model.predict(X) == y).mean())
    print(f"Wrote {CSV_PATH} ({len(rows)} rows)")
    print(f"Wrote {MODEL_PATH} train_acc={acc:.3f}")


if __name__ == "__main__":
    main()