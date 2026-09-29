# Floodsense

Floodsense is a lightweight flood-risk dashboard that estimates rainfall-driven flood probability for a selected latitude and longitude. It is not a flood sensor, a weather warning service, or an emergency service.

## What the estimate means

The backend requests hourly precipitation from Open-Meteo and calculates these trailing inputs:

- `rain_1h`: precipitation in the most recent available hour
- `rain_6h`: precipitation accumulated over the trailing six-hour window
- `rain_24h`: precipitation accumulated over the trailing 24-hour window

Only past and current hourly observations are used. Forecast hours are never included in the totals. The API returns the rainfall values, the weather timestamp, the fetch timestamp, the data source, and a stale-data indicator.

The result is an **estimated rainfall-driven flood risk score from 0 to 100**, grouped as:

- `LOW`: 0-24.9
- `MODERATE`: 25-49.9
- `HIGH`: 50-74.9
- `SEVERE`: 75-100

When the bundled model is available, the score is `P(HIGH) + P(SEVERE)` from a scikit-learn `RandomForestClassifier`, multiplied by 100. If the model cannot be loaded, the backend clearly labels a rule-based heuristic fallback as non-ML.

The bundled model and `ml/train.csv` are generated from synthetic rainfall labels. Training accuracy does not demonstrate real-world performance. A calibrated flood probability requires historical flood observations and location-specific features such as elevation, drainage, soil moisture, river levels, land cover, and local flood reports. Open-Meteo precipitation is also not a confirmed real-time flooding observation.

## Run locally

Use two terminals from the repository root.

### Backend

```bash
cd /home/hasan/Documents/Floodsense
source .venv/bin/activate
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The API provides:

- `GET /health`
- `GET /flood-probability?lat=13.0827&lon=80.2707&location_name=Chennai`

The frontend development server proxies these paths to the backend.

### Frontend

```bash
cd /home/hasan/Documents/Floodsense/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dashboard polls the selected location every 10 minutes and refreshes immediately when the location changes or the Refresh button is used. Browser geolocation is optional and only works when the browser and site permissions allow it.

## Retrain the synthetic model

Retraining is only needed after changing the training code or synthetic data:

```bash
cd /home/hasan/Documents/Floodsense
source .venv/bin/activate
python ml/train.py
```

This regenerates `ml/train.csv` and `ml/model.joblib`. The training script intentionally uses only `rain_1h`, `rain_6h`, and `rain_24h` and saves a classifier with `predict_proba()`.

## Tests and checks

```bash
cd /home/hasan/Documents/Floodsense
source .venv/bin/activate
cd backend
python -m pytest test_mvp.py -q
cd ../frontend
npm run lint
npm run build
```

Backend tests mock Open-Meteo and do not make live network requests.

## Safety notice

Follow official local warnings, evacuation orders, and emergency instructions. Do not use Floodsense as the sole basis for safety decisions.
