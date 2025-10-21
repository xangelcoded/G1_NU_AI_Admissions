# NU Quest – Enrollment Prediction System (Production-Ready)

An NU–themed, production-ready enrollment system for **National University – Lipa** that predicts an applicant’s **Likelihood to Enroll** using only your **trained models** (no LLM).

- ✅ No LLMs; pure model outputs
- ✅ Exact one‑hot alignment to `training_columns.pkl`
- ✅ PSGC address cascade with offline bundle
- ✅ Admin seeding via env
- ✅ Deterministic startup smoke test

## Artifacts Required

Place these in `app/AIMODEL/`:

- `meta_model.pkl`
- `rf.pkl`
- `lr.pkl`
- `xg.pkl`
- `training_columns.pkl`
- `X_train_encoded.pkl`

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your trained models to app/AIMODEL/
flask --app app:create_app run -h 127.0.0.1 -p 5000
```

Open `/`, `/apply`, `/login`, `/admin`, `/health`.

## API (Contract)

- `GET /api/options` → lowercase tokens aligned to training
- `POST /api/predict` → body matches the spec; returns `{ "prob_enroll_pct": 0..1, "confidence": 0..1 }`
- `POST /login`, `GET /logout`, `GET /health`

**/api/predict sample request**

```json
{
  "first program": "bsit",
  "second program": "",
  "current region": "national capital region",
  "current province": "metro manila",
  "current city/municipality": "quezon city",
  "permanent country": "philippines",
  "permanent region": "national capital region",
  "permanent province": "metro manila",
  "permanent city/municipality": "quezon city",
  "student type": "full time",
  "school type": "public",
  "dateofbirth": "2005-01-01"
}
```

**Response**

```json
{"prob_enroll_pct": 0.73, "confidence": 0.91}
```

## Address Data (PSGC)

- Bundled offline JSONs live under `app/data/` and are mirrored to `/static/psgc/` for the frontend.
- Includes NIR, Maguindanao split, Davao de Oro rename.
- For **complete** nationwide coverage, replace these JSON files with the full PSGC dumps (from PSA/psgc.cloud) — the app will use them automatically.

## Deploy

```bash
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app
```

Put Nginx in front (TLS, static caching).

## Troubleshooting

- Models missing → place the 6 `.pkl` files in `app/AIMODEL/`
- Token mismatch → use `/api/options` tokens; the backend suggests nearest tokens on error
- Date format → `yyyy-mm-dd`


**Note:** The API accepts aliases like `full-time`/`part-time` but will normalize to the training tokens `full time`/`part time`.
