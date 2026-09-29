"""Flood probability: RandomForest (ML) + rule-based fallback.

The current model is trained on *synthetic* rainfall labels, so its output is
an estimated rainfall-driven risk score, not a validated real-world flood
probability. Real calibrated probability would require historical flood labels
plus location-specific features such as elevation, drainage, soil moisture,
river levels, land cover and local flood reports.
"""

from __future__ import annotations

from pathlib import Path

LEVELS = ("LOW", "MODERATE", "HIGH", "SEVERE")
LEVEL_TO_INT = {name: i for i, name in enumerate(LEVELS)}

_MODEL = None
_MODEL_TRIED = False
_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "model.joblib"

MODEL_LIMITATIONS = (
    "Model trained from synthetic rainfall labels only. Output is an estimated "
    "rainfall-driven risk score, not a validated real-world flood probability. "
    "Real calibration requires historical flood observations plus location "
    "features such as elevation, drainage, soil moisture, river levels, land "
    "cover and local flood reports."
)


def _band_for_probability(prob: float) -> str:
    if prob >= 75.0:
        return "SEVERE"
    if prob >= 50.0:
        return "HIGH"
    if prob >= 25.0:
        return "MODERATE"
    return "LOW"


def _heuristic_probability(rain_1h: float, rain_6h: float, rain_24h: float) -> float:
    """Rule-based 0-100 score used only when the ML model is unavailable.

    This is explicitly NOT machine learning.
    """
    p = 0.0
    p += min(40.0, rain_6h * 1.6)  # 6h accumulation dominates
    p += min(25.0, rain_1h * 1.2)  # short-intensity spike
    p += min(35.0, rain_24h * 0.35)  # long accumulation
    return round(max(0.0, min(100.0, p)), 1)


def label_from_rules(rain_1h: float, rain_6h: float, rain_24h: float) -> str:
    """Simple mm thresholds used to label synthetic training rows (and fallback)."""
    if rain_6h < 10:
        cls = 0
    elif rain_6h < 25:
        cls = 1
    elif rain_6h < 50:
        cls = 2
    else:
        cls = 3
    if rain_1h >= 25:
        cls = min(3, cls + 1)
    if rain_24h >= 120:
        cls = min(3, cls + 1)
    return LEVELS[cls]


def _load_model():
    global _MODEL, _MODEL_TRIED
    if _MODEL_TRIED:
        return _MODEL
    _MODEL_TRIED = True
    try:
        import joblib

        if _MODEL_PATH.exists():
            _MODEL = joblib.load(_MODEL_PATH)
    except Exception:
        _MODEL = None
    return _MODEL


def _model_probability(
    rain_1h: float,
    rain_6h: float,
    rain_24h: float,
    elevation_m: float = 0.0,
    soil_moisture: float = 0.0,
) -> float | None:
    """Return P(HIGH) + P(SEVERE) * 100 from the RandomForest, or None."""
    model = _load_model()
    if model is None:
        return None
    try:
        proba = model.predict_proba(
            [[float(rain_1h), float(rain_6h), float(rain_24h), float(elevation_m), float(soil_moisture)]]
        )[0]
    except Exception:
        return None

    classes = list(getattr(model, "classes_", []))
    prob_by_class = {int(c): float(p) for c, p in zip(classes, proba)}
    high = prob_by_class.get(LEVEL_TO_INT["HIGH"], 0.0)
    severe = prob_by_class.get(LEVEL_TO_INT["SEVERE"], 0.0)
    return round((high + severe) * 100.0, 1)


def predict_flood_probability(
    rain_1h: float,
    rain_6h: float,
    rain_24h: float,
    elevation_m: float = 0.0,
    soil_moisture: float = 0.0,
) -> dict:
    """Return flood probability, band, class probabilities, method and caveats."""
    ml_prob = _model_probability(rain_1h, rain_6h, rain_24h, elevation_m, soil_moisture)
    if ml_prob is not None:
        method = "random_forest"
        flood_probability = ml_prob
    else:
        method = "heuristic_rules"
        flood_probability = _heuristic_probability(rain_1h, rain_6h, rain_24h)

    # Derive per-class probabilities for display. When the ML model is used we
    # report its own distribution; otherwise we spread the heuristic score.
    if method == "random_forest":
        model = _load_model()
        try:
            proba = model.predict_proba(
                [[float(rain_1h), float(rain_6h), float(rain_24h), float(elevation_m), float(soil_moisture)]]
            )[0]
            classes = list(getattr(model, "classes_", []))
            class_probabilities = {
                LEVELS[int(c)]: round(float(p) * 100.0, 1)
                for c, p in zip(classes, proba)
            }
            for level in LEVELS:
                class_probabilities.setdefault(level, 0.0)
        except Exception:
            class_probabilities = _heuristic_class_probabilities(flood_probability)
    else:
        class_probabilities = _heuristic_class_probabilities(flood_probability)

    return {
        "flood_probability": flood_probability,
        "risk_band": _band_for_probability(flood_probability),
        "class_probabilities": class_probabilities,
        "method": method,
        "model_limitations": MODEL_LIMITATIONS,
    }


def _heuristic_class_probabilities(prob: float) -> dict[str, float]:
    """Spread a heuristic 0-100 score into the four class buckets."""
    remaining = prob
    severe = min(remaining, 25.0)
    remaining -= severe
    high = min(remaining, 25.0)
    remaining -= high
    moderate = min(remaining, 25.0)
    remaining -= moderate
    low = max(0.0, 100.0 - prob)
    return {
        "LOW": round(low, 1),
        "MODERATE": round(moderate, 1),
        "HIGH": round(high, 1),
        "SEVERE": round(severe, 1),
    }