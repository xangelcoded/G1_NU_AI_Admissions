# 🧠 G1 NU AI Admissions — Enrollment & Re-Enrollment Prediction

A **Flask** web app for school admissions that predicts a student’s likelihood to enroll or re-enroll using a stacked ML pipeline (Random Forest, Logistic Regression, XGBoost → Meta-model).  
Large ML artifacts are **not committed** to Git; they’re fetched from **Google Drive** into `app/AIMODEL/` during setup.

---

## Table of Contents

- [Features](#features)  
- [Architecture](#architecture)  
- [Tech Stack](#tech-stack)  
- [Project Structure](#project-structure)  
- [Prerequisites](#prerequisites)  
- [Quickstart](#quickstart)  
  - [1) Clone](#1-clone)  
  - [2) Virtual environment](#2-virtual-environment)  
  - [3) Install dependencies](#3-install-dependencies)  
  - [4) Configure environment](#4-configure-environment)  
  - [5) Get the ML models (Google Drive)](#5-get-the-ml-models-google-drive)  
  - [6) (Optional) Enable Ollama](#6-optional-enable-ollama)  
  - [7) Run the app](#7-run-the-app)  
- [API Reference](#api-reference)  
- [Data Dictionary (Key Fields)](#data-dictionary-key-fields)  
- [Reproducibility & Model Compatibility](#reproducibility--model-compatibility)  
- [Troubleshooting](#troubleshooting)  
- [Development Tips](#development-tips)  
- [Security](#security)  
- [License](#license)  
- [Credits](#credits)

---

## Features

- 🔐 Authentication & sessions (register, login, logout)  
- 🧑‍🎓 Student records persisted to SQLite by default  
- 🤖 Stacked ML prediction (RF + LR + XGBoost → meta-model), with artifacts loaded via `joblib`  
- 💬 Optional LLM explanation of predictions via **Ollama** (local LLM)  
- 📧 Welcome email via **Gmail SMTP** (use an **App Password**, not your main password). :contentReference[oaicite:1]{index=1}  
- ⚙️ Clean **.env-driven configuration** using `python-dotenv` (12-factor style). :contentReference[oaicite:2]{index=2}

---

## Architecture

- **Backend:** Flask app with blueprints (auth, views), SQLAlchemy models (`User`, `Record`)  
- **ML layer:** Pretrained scikit-learn / XGBoost models serialized to `.pkl` and loaded at runtime  
- **Storage:** SQLite (local dev) — configurable via `DATABASE_URL`  
- **Secrets & config:** `.env` loaded at startup with `python-dotenv` (keep your real `.env` out of Git). :contentReference[oaicite:3]{index=3}

---

## Tech Stack

- **Frameworks:** Flask, Flask-SQLAlchemy, Flask-WTF, Flask-CORS  
- **ML:** scikit-learn, XGBoost, joblib  
- **LLM (optional):** Ollama local model for natural-language explanations  
- **Env & tooling:** `python-dotenv`, `pip`, `venv`

---

## Project Structure

G1_NU_AI_Admissions/
├─ app.py # entry point (run with: python app.py)
├─ app/
│ ├─ init.py # Flask app factory & config
│ ├─ auth.py # auth routes + ML prediction & LLM explanation
│ ├─ view.py # additional views
│ └─ model/
│ ├─ init.py
│ └─ user.py # SQLAlchemy models: User, Record
│ └─ AIMODEL/ # <— ML artifacts (downloaded from Drive)
├─ requirements.txt
├─ .env.example # sample configuration (copy to .env)
├─ .gitignore # ignore venv, .env, models, caches, etc.
└─ README.md


---

## Prerequisites

- **Python 3.10+**  
- **Git**

---

## Quickstart

### 1) Clone

git clone https://github.com/xangelcoded/G1_NU_AI_Admissions.git

cd G1_NU_AI_Admissions

2) Virtual environment

# Windows (PowerShell)
python -m venv .venv

.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv

source .venv/bin/activate

3) Install dependencies

pip install -r requirements.txt


4) Configure environment

Create your local config file:

cp .env.example .env

Open .env and set values:

# Flask / DB
SECRET_KEY=change-me
DATABASE_URL=sqlite:///school.db
DATABASE_NAME=school.db
DEBUG=True

# Email (Gmail): use an App Password (with 2-Step Verification)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-16-digit-app-password

# ML
MODELS_DIR=app/AIMODEL



5) Get the ML models (Google Drive)
Option A — One-command download (recommended):

pip install gdown
mkdir -p app/AIMODEL
gdown --folder "https://drive.google.com/drive/folders/1X5nFcDVU13zL3IEAyV3XM2fI7p3wnNDe?usp=sharing" -O app/AIMODEL
gdown supports recursive folder downloads from Google Drive and bypasses common warning prompts. 


Option B — Manual:

Open the Drive link in a browser
Link: https://drive.google.com/drive/folders/1X5nFcDVU13zL3IEAyV3XM2fI7p3wnNDe?usp=sharing

Download files and place them in app/AIMODEL/:

meta_model.pkl

rf.pkl

lr.pkl

xg.pkl

training_columns.pkl

X_train_encoded.pkl (if required by your code)

6) Run the app

python app.py
The app starts at http://127.0.0.1:5000/ (or the host/port configured in your code).

API Reference
Typical routes & fields. If you customized payloads, adjust accordingly.

POST /register
Creates a user and a student Record, runs ML prediction, may send a welcome email.

Content-Type: application/x-www-form-urlencoded or multipart/form-data

Fields (common subset):
firstName, lastName, dateOfBirth (MM/DD/YYYY), sex, emailAddress, password,
student_ID, campus, academic_year, academic_term,
course_1st, course_2nd,
curr_region, curr_province, curr_city,
per_country, per_region, per_province, per_city,
student_type (New/Old/Transferee), school_type (Public/Private),
last_school_attended

Response (example):

json
Copy code
{
  "success": true,
  "prediction": {
    "label": "Will Re-enroll",
    "probability": 0.86,
    "confidence": "high"
  },
  "explanation": "Top factors: course_1st, campus, last_school_attended ..."
}
cURL example

bash
Copy code
curl -X POST http://127.0.0.1:5000/register \
  -F firstName=Juan -F lastName=DelaCruz -F dateOfBirth=01/15/2005 \
  -F sex=Male -F emailAddress=juan@example.com -F password=pass123 \
  -F student_ID=2025-0001 -F campus=Main -F academic_year=2025-2026 \
  -F academic_term=1 -F course_1st=BSCS -F course_2nd=BSIT \
  -F curr_region=Region4A -F curr_province=Laguna -F curr_city=Calamba \
  -F per_country=Philippines -F per_region=Region4A \
  -F per_province=Laguna -F per_city=Calamba \
  -F student_type=New -F school_type=Public \
  -F last_school_attended="Calamba Sci HS"
POST /login
Fields: emailAddress, password

Response: session cookie is set if successful.

GET /delete/<id>
Deletes a user by numeric ID (demo utility).

Data Dictionary (Key Fields)
User: id, emailAddress, password_hash, created_at

Record: id, student_ID, demographics (age/sex/addresses), program choices, school history,
likelihood (float), label (string), confidence (string), explanation (text), timestamps

Exact columns may vary — see app/model/user.py for the source of truth.

Reproducibility & Model Compatibility
Pin ML library versions used during training (e.g., scikit-learn, xgboost).

Loading pickled scikit-learn models across different versions is not supported/reliable — keep runtime equal to the training version. 

Troubleshooting
Models not found / load error

Ensure files exist in app/AIMODEL (or set MODELS_DIR in .env).

Verify scikit-learn version matches the training environment. 
scikit-learn.org

Gmail SMTP fails

Use a Gmail App Password (requires 2-Step Verification). Don’t use your normal password. 
Google Help

Sessions not sticking in local dev

Keep DEBUG=True for local HTTP; use HTTPS and stricter cookies in production.

gdown --folder doesn’t fetch files

Credits
Project Team: Angel Malaluan, Marc Miranda, Ian Medina, Katrina Pasadilla, Kenneth Averion, Ameril Mampao
