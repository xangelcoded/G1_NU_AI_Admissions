🧠 G1 NU AI Admissions — Enrollment & Re-Enrollment Prediction

A Flask web app for school admissions that predicts a student’s likelihood to enroll or re-enroll using a stacked ML pipeline (Random Forest, Logistic Regression, XGBoost → Meta-model).
Large ML artifacts are not committed to Git; they’re fetched from Google Drive into app/AIMODEL/ during setup.

A great README is part of your grade: GitHub itself recommends every repo ship with one, describing what the project does, how to run it, how to contribute, and how to stay secure. 
GitHub Docs

Table of Contents

Features

Architecture

Tech Stack

Project Structure

Prerequisites

Quickstart

1) Clone

2) Virtual environment

3) Install dependencies

4) Configure environment

5) Get the ML models (Google Drive)

6) (Optional) Enable Ollama

7) Run the app

API Reference

Data Dictionary (Key Fields)

Reproducibility & Model Compatibility

Troubleshooting

Development Tips

Security

License

Credits

Features

🔐 Authentication & sessions (register, login, logout)

🧑‍🎓 Student records persisted to SQLite by default

🤖 Stacked ML prediction (RF + LR + XGBoost → meta-model), with saved artifact loading via joblib

💬 Optional LLM explanation of predictions via Ollama (local LLM)

📧 Welcome email via Gmail SMTP (use an App Password, not your main password) 
GitHub

⚙️ Clean .env-driven configuration using python-dotenv (12-factor style) 
PyPI
+1

Architecture

Backend: Flask app with blueprints (auth, views), SQLAlchemy models (User, Record)

ML layer: Pretrained sklearn/xgboost models serialized to .pkl and loaded at runtime

Storage: SQLite (local dev) — configurable through DATABASE_URL

Secrets & config: .env loaded at startup with python-dotenv (keep your real .env out of Git) 
PyPI

Tech Stack

Frameworks: Flask, Flask-SQLAlchemy, Flask-WTF, Flask-CORS

ML: scikit-learn, XGBoost, joblib (+ optional LIME if included in requirements)

LLM (optional): Ollama local model for natural-language explanations

Env & tooling: python-dotenv, pip, virtualenv

Project Structure
G1_NU_AI_Admissions/
├─ app.py                       # entry point (run with: python app.py)
├─ app/
│  ├─ __init__.py               # Flask app factory & config
│  ├─ auth.py                   # auth routes + ML prediction & LLM explanation
│  ├─ view.py                   # additional views
│  └─ model/
│     ├─ __init__.py
│     └─ user.py                # SQLAlchemy models: User, Record
│  └─ AIMODEL/                  # <— ML artifacts (downloaded from Drive)
├─ requirements.txt
├─ .env.example                 # sample configuration (copy to .env)
├─ .gitignore                   # ignore venv, .env, models, caches, etc.
└─ README.md


For .gitignore, use the official Python template from GitHub’s maintained collection so you don’t accidentally commit caches, venvs, or secrets. 
GitHub
+1

Prerequisites

Python 3.10+

Git

(Optional) Ollama installed if you want LLM explanations

Quickstart
1) Clone
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

2) Virtual environment
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate

3) Install dependencies
pip install -r requirements.txt


We pin scikit-learn to a compatible version because cross-version loading of pickled models is unsupported and risky; use the same versions used during training. 
scikit-learn.org
+1

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

# LLM (optional)
OLLAMA_MODEL=gemma:1b


python-dotenv reads .env and exports variables for your app, keeping secrets out of code and version control. 
PyPI

For Gmail SMTP, generate an App Password (with 2-Step Verification) instead of using your main password. 
GitHub

5) Get the ML models (Google Drive)

Option A — One-command download (recommended):

pip install gdown
mkdir -p app/AIMODEL
gdown --folder "https://drive.google.com/drive/folders/1tWb2rTPgFtyRndK6hi2Rq4Px36sYHiLQ?usp=sharing" -O app/AIMODEL


gdown --folder "<share-url>" -O <output-dir> pulls the entire shared folder into app/AIMODEL. 
CommandMasters
+2
Stack Overflow
+2

Option B — Manual:

Open the Drive link in a browser

Download files and place them in app/AIMODEL/:

meta_model.pkl

rf.pkl

lr.pkl

xg.pkl

training_columns.pkl

X_train_encoded.pkl (if required by your code)

6) (Optional) Enable Ollama
# Install Ollama (see official site) and pull a local model
ollama pull gemma:1b


Update OLLAMA_MODEL in .env if you prefer another local model.

7) Run the app
python app.py


The app starts at http://127.0.0.1:5000/
 (or the host/port configured in your code).

API Reference

Below are the typical routes and fields used. If you’ve customized request bodies, adjust accordingly.

POST /register

Creates a user and a student Record, runs ML prediction, may send a welcome email.

Content-Type: application/x-www-form-urlencoded or multipart/form-data

Fields (common subset):

firstName, lastName, dateOfBirth (MM/DD/YYYY), sex, emailAddress, password

student_ID, campus, academic_year, academic_term

course_1st, course_2nd

curr_region, curr_province, curr_city

per_country, per_region, per_province, per_city

student_type (e.g., New/Old/Transferee), school_type (Public/Private)

last_school_attended

Response (example):

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

Deletes a user by numeric ID. (Use with caution in demos.)

Data Dictionary (Key Fields)

User: id, emailAddress, password_hash, created_at

Record: id, student_ID, demographics (age/sex/addresses), program choices, school history, likelihood (float), label (string), confidence (string), explanation (text), timestamps

Your exact columns may vary; check app/model/user.py in your repo for the source of truth.

Reproducibility & Model Compatibility

Pin versions of ML libraries used to train your models (e.g., scikit-learn, xgboost).

Important: Loading a pickled scikit-learn model trained under a different version is not supported and can fail silently or at load time. Keep runtime versions equal to training versions. 
scikit-learn.org

Troubleshooting

Models not found / load error

Confirm files exist in app/AIMODEL (or set MODELS_DIR in .env).

Ensure your scikit-learn version matches the training environment (we pin in requirements.txt). Cross-version pickle load is unsupported. 
scikit-learn.org

Gmail SMTP fails

Use a Gmail App Password (requires 2-Step Verification). Regular account passwords won’t work with modern SMTP auth. 
GitHub

Sessions not sticking in local dev

Keep DEBUG=True for local HTTP. In production, run under HTTPS and set secure cookie flags.

gdown --folder doesn’t fetch files

Make sure the Drive folder is shared as “Anyone with the link can view” and then rerun the command. gdown supports folder URLs/IDs for bulk download. 
CommandMasters

.env variables aren’t loading

Verify the file is named .env and located at the project root. python-dotenv reads key=value lines and exports them before Flask initializes. 
PyPI

Development Tips

Keep secrets in .env; never hardcode credentials. python-dotenv implements this cleanly and follows 12-factor practices. 
PyPI

Start your repo with a README and a proper .gitignore. Use GitHub’s official Python template so you don’t leak venvs or caches. 
GitHub Docs
+1

If you need to add screenshots, drop them in a docs/ folder and reference them with Markdown.

Security

Never commit .env, database files, or model binaries.

Prefer App Passwords + 2FA for Gmail SMTP. 
GitHub

License

Add a license (MIT is common for student projects). A license clarifies reuse for reviewers and classmates.

Credits

Project Team: Angel Malaluan, Marc Miranda, Ian Medina, Katrina Pasadilla, Kenneth Averion, Ameril Mampao
