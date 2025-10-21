
import os
import json
import difflib
from datetime import datetime, date
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import joblib
import numpy as np
import pandas as pd

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime, timedelta
from sqlalchemy import func, desc



db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw, method='pbkdf2:sha256')
    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    first_program = db.Column(db.String(128))
    second_program = db.Column(db.String(128))
    curr_region = db.Column(db.String(128))
    curr_province = db.Column(db.String(128))
    curr_city = db.Column(db.String(128))
    per_country = db.Column(db.String(128))
    per_region = db.Column(db.String(128))
    per_province = db.Column(db.String(128))
    per_city = db.Column(db.String(128))
    student_type = db.Column(db.String(32))
    school_type = db.Column(db.String(32))
    date_of_birth = db.Column(db.String(16))
    age_years = db.Column(db.Integer)
    local_or_foreign = db.Column(db.String(16))
    same_region = db.Column(db.Integer)
    same_province = db.Column(db.Integer)
    same_city = db.Column(db.Integer)
    prob_enroll_pct = db.Column(db.Float)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



MODELS = {
    "meta": None,
    "rf": None,
    "lr": None,
    "xg": None,
    "training_columns": None,
    "X_train_encoded": None,
}
MODELS_LOADED = False

EXPECTED_INPUT_KEYS = [
    "first program",
    "second program",
    "current region",
    "current province",
    "current city/municipality",
    "permanent country",
    "permanent region",
    "permanent province",
    "permanent city/municipality",
    "student type",
    "school type",
    "dateofbirth",
]

ALIASES = {
    "full-time": "full time",
    "part-time": "part time",
    "ncr": "national capital region",
    "nir": "negros island region",
    "compostela valley": "davao de oro",
    "davao de oro": "davao de oro",
    "maguindanao del norte": "maguindanao del norte",
    "maguindanao del sur": "maguindanao del sur",
    "ph": "philippines",
}

CACHED_TOKEN_OPTIONS = {
    "first program": [],
    "second program": [],
    "current region": [],
    "current province": [],
    "current city/municipality": [],
    "permanent country": ["philippines"],
    "permanent region": [],
    "permanent province": [],
    "permanent city/municipality": [],
    "student type": ["full time", "part time"],
    "school type": ["public", "private"],
}

# ---------------- Helpers ----------------
def _lower(s): return str(s or "").strip().lower()
def tokenize(value): return ALIASES.get(_lower(value), _lower(value))

def normalize_student_type(val):
    v = _lower(val).replace('-', ' ').replace('_',' ')
    if 'part' in v: return 'part time'
    if 'full' in v: return 'full time'
    return v or 'full time'

def normalize_school_type(val):
    v = _lower(val).replace('-', ' ').replace('_',' ')
    if 'priv' in v: return 'private'
    if 'pub' in v: return 'public'
    return v or 'public'

def age_from_dob_iso(dob_str):
    try:
        y,m,d = map(int, str(dob_str).split("-"))
        b = date(y,m,d); t = date.today()
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    except: return None

def suggest_token(value, choices):
    value = _lower(value)
    if not choices: return []
    return difflib.get_close_matches(value, choices, n=3, cutoff=0.6)

def derive_engineered(ex):
    local_or_foreign = "local" if ex.get("permanent country") == "philippines" else "foreign"
    same_region = 1 if ex.get("current region") == ex.get("permanent region") else 0
    same_province = 1 if ex.get("current province") == ex.get("permanent province") else 0
    same_city = 1 if ex.get("current city/municipality") == ex.get("permanent city/municipality") else 0
    age = age_from_dob_iso(ex.get("dateofbirth",""))
    return local_or_foreign, same_region, same_province, same_city, age

def build_feature_row(payload):
    ex = {k: tokenize(payload.get(k, "")) for k in EXPECTED_INPUT_KEYS}
    # normalize tolerant fields
    ex["student type"] = normalize_student_type(ex.get("student type"))
    ex["school type"] = normalize_school_type(ex.get("school type"))

    # required fields check (allow empty second program)
    missing = [k for k in EXPECTED_INPUT_KEYS if (k != "second program" and not ex.get(k))]
    if missing:
        return None, {"error":"missing_fields","message":"Missing required fields.","fields":missing}

    local_or_foreign, same_region, same_province, same_city, age = derive_engineered(ex)
    if age is None:
        return None, {"error":"invalid_date","message":"dateOfBirth must be ISO yyyy-mm-dd"}

    row = {
        "Program (First Choice)": ex["first program"],
        "Program (Second Choice)": ex["second program"],
        "Current Region": ex["current region"],
        "Current Province": ex["current province"],
        "Current City": ex["current city/municipality"],
        "Permanent Country": ex["permanent country"],
        "Permanent Region": ex["permanent region"],
        "Permanent Province": ex["permanent province"],
        "Permanent City": ex["permanent city/municipality"],
        "Student Type": ex["student type"],
        "School Type": ex["school type"],
        "LocalOrForeign": local_or_foreign,
        "SameRegion": same_region,
        "SameProvince": same_province,
        "SameCity": same_city,
        "Age": age,
    }
    return row, None

def encode_row_to_training(df_one_row):
    dummies = pd.get_dummies(df_one_row)
    cols = MODELS["training_columns"]
    dummies = dummies.reindex(columns=cols, fill_value=0)
    assert dummies.shape[1] == len(cols)
    return dummies

def predict_with_stack(df_encoded):
    p1 = MODELS["rf"].predict_proba(df_encoded)[:,1]
    p2 = MODELS["lr"].predict_proba(df_encoded)[:,1]
    p3 = MODELS["xg"].predict_proba(df_encoded.to_numpy())[:,1]
    stacked = np.column_stack([p1,p2,p3])
    meta_probs = MODELS["meta"].predict_proba(stacked)[0]
    prob_pos = float(meta_probs[1])
    confidence = float(max(meta_probs))
    return prob_pos, confidence

def load_training_tokens_from_columns(cols):
    buckets = {k:set() for k in CACHED_TOKEN_OPTIONS.keys()}
    mapping = {
        "program (first choice)":"first program",
        "program (second choice)":"second program",
        "current region":"current region",
        "current province":"current province",
        "current city":"current city/municipality",
        "permanent country":"permanent country",
        "permanent region":"permanent region",
        "permanent province":"permanent province",
        "permanent city":"permanent city/municipality",
        "student type":"student type",
        "school type":"school type",
    }
    for c in cols:
        if "_" not in c: continue
        prefix, token = c.split("_",1)
        pref = prefix.strip().lower()
        if pref in mapping:
            buckets[mapping[pref]].add(token.lower())
    for k in buckets:
        if buckets[k]: CACHED_TOKEN_OPTIONS[k] = sorted(list(buckets[k]))

def _finalize_default_options():
    # Ensure non-empty defaults so the UI never shows empty dropdowns
    if not CACHED_TOKEN_OPTIONS.get('first program'):
        CACHED_TOKEN_OPTIONS['first program'] = ['bsit','bsba','bscs','bsis']
    if not CACHED_TOKEN_OPTIONS.get('second program'):
        CACHED_TOKEN_OPTIONS['second program'] = ['','bsit','bsba','bscs','bsis']
    if not CACHED_TOKEN_OPTIONS.get('permanent country'):
        CACHED_TOKEN_OPTIONS['permanent country'] = ['philippines','others']
    if not CACHED_TOKEN_OPTIONS.get('student type'):
        CACHED_TOKEN_OPTIONS['student type'] = ['full time','part time']
    if not CACHED_TOKEN_OPTIONS.get('school type'):
        CACHED_TOKEN_OPTIONS['school type'] = ['public','private']
    if not CACHED_TOKEN_OPTIONS.get('current region'):
        CACHED_TOKEN_OPTIONS['current region'] = ['national capital region','ilocos region','western visayas','negros island region','davao region','bangsamoro autonomous region in muslim mindanao']
    if not CACHED_TOKEN_OPTIONS.get('permanent region'):
        CACHED_TOKEN_OPTIONS['permanent region'] = CACHED_TOKEN_OPTIONS['current region']

# --------------- PSGC minimal (offline) ---------------
def ensure_psgc_data(app):
    data_dir = os.path.join(app.root_path,"data")
    os.makedirs(data_dir, exist_ok=True)
    required = ["psgc_regions.json","psgc_provinces.json","psgc_cities.json","psgc_barangays.json"]
    # If missing, write lightweight samples (frontend also has copies under static/psgc)
    missing = [f for f in required if not os.path.exists(os.path.join(data_dir,f))]
    if not missing:
        return
    sample_regions = [
        {"code":"130000000","name":"NCR - National Capital Region","token":"national capital region"},
        {"code":"140000000","name":"CAR - Cordillera Administrative Region","token":"cordillera administrative region"},

        {"code":"010000000","name":"Region I - Ilocos Region","token":"ilocos region"},
        {"code":"020000000","name":"Region II - Cagayan Valley","token":"cagayan valley"},
        {"code":"030000000","name":"Region III - Central Luzon","token":"central luzon"},
        {"code":"040000000","name":"Region IV-A - CALABARZON","token":"calabarzon"},
        {"code":"170000000","name":"Region IV-B - MIMAROPA Region","token":"mimaropa region"},
        {"code":"050000000","name":"Region V - Bicol Region","token":"bicol region"},

        {"code":"060000000","name":"Region VI - Western Visayas","token":"western visayas"},
        {"code":"070000000","name":"Region VII - Central Visayas","token":"central visayas"},
        {"code":"080000000","name":"Region VIII - Eastern Visayas","token":"eastern visayas"},

        {"code":"090000000","name":"Region IX - Zamboanga Peninsula","token":"zamboanga peninsula"},
        {"code":"100000000","name":"Region X - Northern Mindanao","token":"northern mindanao"},
        {"code":"110000000","name":"Region XI - Davao Region","token":"davao region"},
        {"code":"120000000","name":"Region XII - SOCCSKSARGEN","token":"soccsksargen"},
        {"code":"160000000","name":"Region XIII - Caraga","token":"caraga"},

        {"code":"180000000","name":"NIR - Negros Island Region","token":"negros island region"},
        {"code":"190000000","name":"BARMM - Bangsamoro Autonomous Region in Muslim Mindanao","token":"bangsamoro autonomous region in muslim mindanao"},
    ]

    sample_provinces = [
        {"code":"137400000","region_code":"130000000","name":"Metro Manila","token":"metro manila"},
        {"code":"034900000","region_code":"030000000","name":"Nueva Ecija","token":"nueva ecija"},
        {"code":"060400000","region_code":"060000000","name":"Iloilo","token":"iloilo"},
        {"code":"184500000","region_code":"180000000","name":"Negros Occidental","token":"negros occidental"},
        {"code":"118600000","region_code":"110000000","name":"Davao de Oro","token":"davao de oro"},
        {"code":"129800000","region_code":"190000000","name":"Maguindanao del Norte","token":"maguindanao del norte"},
        {"code":"129900000","region_code":"190000000","name":"Maguindanao del Sur","token":"maguindanao del sur"},
    ]
    sample_cities = [
        {"code":"137404000","province_code":"137400000","name":"Quezon City","token":"quezon city"},
        {"code":"061902000","province_code":"060400000","name":"Iloilo City","token":"iloilo city"},
        {"code":"184500000-01","province_code":"184500000","name":"Bacolod City","token":"bacolod city"},
        {"code":"118601000","province_code":"118600000","name":"Nabunturan","token":"nabunturan"},
        {"code":"129801000","province_code":"129800000","name":"Cotabato City","token":"cotabato city"},
        {"code":"129901000","province_code":"129900000","name":"Buluan","token":"buluan"},
    ]
    sample_barangays = [
        {"code":"137404001","city_code":"137404000","name":"Alicia","token":"alicia"},
        {"code":"137404002","city_code":"137404000","name":"Amihan","token":"amihan"},
        {"code":"061902001","city_code":"061902000","name":"Arévalo Poblacion","token":"arévalo poblacion"},
        {"code":"184500001","city_code":"184500000-01","name":"Barangay 1 (Feria)","token":"barangay 1 (feria)"},
        {"code":"118601001","city_code":"118601000","name":"Anislagan","token":"anislagan"},
        {"code":"129801001","city_code":"129801000","name":"Bagua","token":"bagua"},
        {"code":"129901001","city_code":"129901000","name":"Bagoenged","token":"bagoenged"},
    ]
    with open(os.path.join(data_dir,"psgc_regions.json"),"w",encoding="utf-8") as f: json.dump(sample_regions,f,ensure_ascii=False,indent=2)
    with open(os.path.join(data_dir,"psgc_provinces.json"),"w",encoding="utf-8") as f: json.dump(sample_provinces,f,ensure_ascii=False,indent=2)
    with open(os.path.join(data_dir,"psgc_cities.json"),"w",encoding="utf-8") as f: json.dump(sample_cities,f,ensure_ascii=False,indent=2)
    with open(os.path.join(data_dir,"psgc_barangays.json"),"w",encoding="utf-8") as f: json.dump(sample_barangays,f,ensure_ascii=False,indent=2)

# ---------------- Models ----------------
def load_models(app):
    global MODELS_LOADED
    try:
        base = os.path.join(app.root_path, "AIMODEL")
        MODELS["meta"] = joblib.load(os.path.join(base, "meta_model.pkl"))
        MODELS["rf"]   = joblib.load(os.path.join(base, "rf.pkl"))
        MODELS["lr"]   = joblib.load(os.path.join(base, "lr.pkl"))
        MODELS["xg"]   = joblib.load(os.path.join(base, "xg.pkl"))
        MODELS["training_columns"] = joblib.load(os.path.join(base, "training_columns.pkl"))
        MODELS["X_train_encoded"]  = joblib.load(os.path.join(base, "X_train_encoded.pkl"))
        MODELS_LOADED = True
        load_training_tokens_from_columns(MODELS["training_columns"])
    except Exception as e:
        MODELS_LOADED = False
        print(f"[Model Load Error] {e}")

def smoke_test_prediction(app):
    if not MODELS_LOADED:
        return
    tokens = {k:(v[0] if isinstance(v,list) and v else '') for k,v in CACHED_TOKEN_OPTIONS.items()}
    payload = {
        "first program": tokens.get("first program","bsit"),
        "second program": tokens.get("second program",""),
        "current region": tokens.get("current region","national capital region"),
        "current province": tokens.get("current province","metro manila"),
        "current city/municipality": tokens.get("current city/municipality","quezon city"),
        "permanent country": tokens.get("permanent country","philippines"),
        "permanent region": tokens.get("permanent region","national capital region"),
        "permanent province": tokens.get("permanent province","metro manila"),
        "permanent city/municipality": tokens.get("permanent city/municipality","quezon city"),
        "student type": "full time",
        "school type": "public",
        "dateofbirth": "2005-01-01",
    }
    try:
        row, err = build_feature_row(payload)
        if err: return
        enc = encode_row_to_training(pd.DataFrame([row]))
        prob, conf = predict_with_stack(enc)
        assert 0 <= prob <= 1 and 0 <= conf <= 1
    except Exception:
        pass
    
    @app.get("/api/admin/metrics")
    def admin_metrics():
        
        HIGH_T = float(os.getenv("HIGH_THRESHOLD", "0.75"))
        MED_T  = float(os.getenv("MEDIUM_THRESHOLD", "0.50"))

        try:
            days     = int(request.args.get("days", 30))
            program  = (request.args.get("program") or "").strip().lower()
            region   = (request.args.get("region") or "").strip().lower()
            bucket   = (request.args.get("bucket") or "").strip().upper()
            min_conf = float(request.args.get("min_conf", 0.0))
            sampleN  = min(int(request.args.get("limit", 100)), 1000)
        except Exception:
            return jsonify({"ok": False, "error": "bad_params"}), 400

        since = datetime.utcnow() - timedelta(days=days)

        q = Record.query.filter(Record.created_at >= since)
        if program:  q = q.filter(Record.first_program == program)
        if region:   q = q.filter(Record.curr_region == region)
        if min_conf > 0: q = q.filter(Record.confidence >= min_conf)

        if bucket == "H":
            q = q.filter(Record.prob_enroll_pct >= HIGH_T)
        elif bucket == "M":
            q = q.filter(Record.prob_enroll_pct >= MED_T, Record.prob_enroll_pct < HIGH_T)
        elif bucket == "L":
            q = q.filter(Record.prob_enroll_pct < MED_T)

        total = q.count()
        if total == 0:
            return jsonify({
                "ok": True,
                "summary": {"n": 0, "avg_prob": 0, "avg_conf": 0, "high": 0, "med": 0, "low": 0},
                "trend": [],
                "programs": [],
                "regions": [],
                "student_type": [],
                "local_foreign": [],
                "hist_prob": [0]*20,
                "hist_conf": [0]*20,
                "heat": [],   # bubble heatmap points
                "top": [],
                "queues": {"call_now": [], "warm": [], "nurture": []},
                "program_tokens": [],
                "region_tokens": [],
                "thresholds": {"high": HIGH_T, "medium": MED_T},
            })

        # Summary
        avg_prob = float(q.with_entities(func.avg(Record.prob_enroll_pct)).scalar() or 0)
        avg_conf = float(q.with_entities(func.avg(Record.confidence)).scalar() or 0)
        high = q.filter(Record.prob_enroll_pct >= HIGH_T).count()
        med  = q.filter(Record.prob_enroll_pct >= MED_T, Record.prob_enroll_pct < HIGH_T).count()
        low  = total - high - med

        # Trend by date
        trend_rows = (q.with_entities(
            func.date(Record.created_at).label("d"),
            func.avg(Record.prob_enroll_pct).label("avg_prob"),
            func.avg(Record.confidence).label("avg_conf"),
            func.count(Record.id).label("n"),
        ).group_by(func.date(Record.created_at)).order_by(func.date(Record.created_at)).all())
        trend = [{"date": str(r.d), "avg_prob": float(r.avg_prob or 0), "avg_conf": float(r.avg_conf or 0), "count": int(r.n)} for r in trend_rows]

        # Programs breakdown (first choice)
        prog_rows = (q.with_entities(
            Record.first_program,
            func.count(Record.id).label("n"),
            func.avg(Record.prob_enroll_pct).label("avg_prob"),
            func.avg(Record.confidence).label("avg_conf"),
        ).group_by(Record.first_program).order_by(desc("n")).limit(50).all())
        programs = [{"program": r.first_program, "count": int(r.n), "avg_prob": float(r.avg_prob or 0), "avg_conf": float(r.avg_conf or 0)} for r in prog_rows]

        # Regions breakdown (current)
        reg_rows = (q.with_entities(
            Record.curr_region,
            func.count(Record.id).label("n")
        ).group_by(Record.curr_region).order_by(desc("n")).limit(25).all())
        regions = [{"region": r.curr_region, "count": int(r.n)} for r in reg_rows]

        # Student type / Local-foreign splits
        st_rows = (q.with_entities(Record.student_type, func.count(Record.id))).group_by(Record.student_type).all()
        lf_rows = (q.with_entities(Record.local_or_foreign, func.count(Record.id))).group_by(Record.local_or_foreign).all()
        student_type = [{"type": (a or "unknown"), "count": int(b)} for a, b in st_rows]
        local_foreign = [{"type": (a or "unknown"), "count": int(b)} for a, b in lf_rows]

        # Pull small set of columns for histograms & heatmap & queues
        rows = q.with_entities(
            Record.prob_enroll_pct, Record.confidence, Record.first_program,
            Record.student_type, Record.curr_region, Record.created_at
        ).all()

        # Histograms (20 bins)
        def hist(vals, bins=20):
            out = [0]*bins
            for v in vals:
                if v is None: continue
                i = int(v * bins)
                if i == bins: i = bins-1
                out[i] += 1
            return out

        hist_prob = hist([r.prob_enroll_pct for r in rows], 20)
        hist_conf = hist([r.confidence for r in rows], 20)

        # Heatmap as bubble points on 10x10 grid (size ~ count)
        grid = {}
        for r in rows:
            p = r.prob_enroll_pct or 0.0
            c = r.confidence or 0.0
            i = min(int(p * 10), 9)
            j = min(int(c * 10), 9)
            grid[(i, j)] = grid.get((i, j), 0) + 1
        heat = [{"x": (i+0.5)*10, "y": (j+0.5)*10, "count": cnt} for (i, j), cnt in grid.items()]  # 0..100 axes

        # Prioritized list (topN by prob*conf)
        top_rows = (q.with_entities(
            Record.id, Record.first_program, Record.student_type, Record.curr_region,
            Record.prob_enroll_pct, Record.confidence, Record.created_at
        ).order_by(desc(Record.prob_enroll_pct * Record.confidence)).limit(sampleN).all())
        top = [{
            "id": r.id,
            "first_program": r.first_program,
            "student_type": r.student_type,
            "curr_region": r.curr_region,
            "prob": float(r.prob_enroll_pct or 0),
            "conf": float(r.confidence or 0),
            "priority": float((r.prob_enroll_pct or 0) * (r.confidence or 0)),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in top_rows]

        # Queues
        call_now_rows = (q.filter(Record.prob_enroll_pct >= HIGH_T, Record.confidence >= 0.8)
                        .order_by(desc(Record.prob_enroll_pct * Record.confidence)).limit(10).all())
        warm_rows = (q.filter(Record.prob_enroll_pct >= MED_T, Record.prob_enroll_pct < HIGH_T)
                        .order_by(desc(Record.prob_enroll_pct)).limit(10).all())
        nurture_rows = (q.filter(Record.prob_enroll_pct < MED_T)
                        .order_by(desc(Record.prob_enroll_pct)).limit(10).all())
        def row_min(r):
            return {
                "first_program": r.first_program, "student_type": r.student_type,
                "curr_region": r.curr_region, "prob": float(r.prob_enroll_pct or 0),
                "conf": float(r.confidence or 0), "created_at": r.created_at.isoformat() if r.created_at else None
            }
        queues = {
            "call_now":   [row_min(r) for r in call_now_rows],
            "warm":       [row_min(r) for r in warm_rows],
            "nurture":    [row_min(r) for r in nurture_rows],
        }

        # Tokens (for filter dropdowns)
        program_tokens = [p["program"] for p in programs]
        region_tokens  = [r["region"] for r in regions]

        return jsonify({
            "ok": True,
            "summary": {"n": total, "avg_prob": avg_prob, "avg_conf": avg_conf, "high": high, "med": med, "low": low},
            "trend": trend,
            "programs": programs,
            "regions": regions,
            "student_type": student_type,
            "local_foreign": local_foreign,
            "hist_prob": hist_prob,
            "hist_conf": hist_conf,
            "heat": heat,
            "top": top,
            "queues": queues,
            "program_tokens": program_tokens,
            "region_tokens": region_tokens,
            "thresholds": {"high": HIGH_T, "medium": MED_T},
        })


    @app.get("/api/admin/table")
    def admin_table():
    
        HIGH_T = float(os.getenv("HIGH_THRESHOLD", "0.75"))
        MED_T  = float(os.getenv("MEDIUM_THRESHOLD", "0.50"))

        try:
            days = int(request.args.get("days", 30))
            program = (request.args.get("program") or "").strip().lower()
            region  = (request.args.get("region") or "").strip().lower()
            bucket  = (request.args.get("bucket") or "").strip().upper()
            min_conf = float(request.args.get("min_conf", 0.0))
            page = max(int(request.args.get("page", 1)), 1)
            page_size = min(max(int(request.args.get("page_size", 25)), 1), 200)
            sort = (request.args.get("sort") or "priority").strip().lower()
            direction = (request.args.get("dir") or "desc").strip().lower()
        except Exception:
            return jsonify({"ok": False, "error": "bad_params"}), 400

        since = datetime.utcnow() - timedelta(days=days)
        q = Record.query.filter(Record.created_at >= since)
        if program: q = q.filter(Record.first_program == program)
        if region:  q = q.filter(Record.curr_region == region)
        if min_conf > 0: q = q.filter(Record.confidence >= min_conf)
        if bucket == "H":
            q = q.filter(Record.prob_enroll_pct >= HIGH_T)
        elif bucket == "M":
            q = q.filter(Record.prob_enroll_pct >= MED_T, Record.prob_enroll_pct < HIGH_T)
        elif bucket == "L":
            q = q.filter(Record.prob_enroll_pct < MED_T)

        # Sorting
        sort_map = {
            "priority": Record.prob_enroll_pct * Record.confidence,
            "prob": Record.prob_enroll_pct,
            "conf": Record.confidence,
            "created_at": Record.created_at,
        }
        col = sort_map.get(sort, sort_map["priority"])
        col = col.desc() if direction == "desc" else col.asc()

        total = q.count()
        rows = (q.with_entities(
            Record.id, Record.first_program, Record.student_type, Record.curr_region,
            Record.prob_enroll_pct, Record.confidence, Record.created_at
        ).order_by(col)
        .offset((page-1)*page_size).limit(page_size).all())

        out = [{
            "id": r.id,
            "first_program": r.first_program,
            "student_type": r.student_type,
            "curr_region": r.curr_region,
            "prob": float(r.prob_enroll_pct or 0),
            "conf": float(r.confidence or 0),
            "priority": float((r.prob_enroll_pct or 0) * (r.confidence or 0)),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]

        return jsonify({"ok": True, "total": total, "page": page, "page_size": page_size, "rows": out})

# --------------- App Factory ---------------
def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")
    CORS(app)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","nu-lipa-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL","sqlite:///database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_TYPE"] = "filesystem"

    Session(app)
    db.init_app(app)
    with app.app_context():
        db.create_all()

        # seed admin
        email = os.getenv("ADMIN_EMAIL")
        pwd = os.getenv("ADMIN_PASSWORD")
        if email and pwd:
            # create if not exists
            from sqlalchemy import func
            existing = User.query.filter(func.lower(User.email) == email.lower()).first()
            if not existing:
                u = User(email=email, is_admin=True, must_change_password=True)
                u.set_password(pwd)
                db.session.add(u); db.session.commit()

    ensure_psgc_data(app)
    load_models(app)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "models_loaded": MODELS_LOADED, "has_training_columns": MODELS["training_columns"] is not None})

    @app.get("/api/admin/latest")
    def api_admin_latest():
        try:
            rec = Record.query.order_by(Record.created_at.desc()).first()
            if not rec:
                return jsonify({"ok": False})
            return jsonify({
                "ok": True,
                "record": {
                    "prob_enroll_pct": rec.prob_enroll_pct,
                    "confidence": rec.confidence,
                    "created_at": rec.created_at.isoformat(),
                }
            })
        except Exception:
            return jsonify({"ok": False})

    @app.get("/api/options")
    def api_options():
        _finalize_default_options()
        return jsonify({"tokens": CACHED_TOKEN_OPTIONS})

    @app.post("/api/predict")
    def api_predict():
        payload = request.get_json(force=True, silent=True) or {}
        row_dict, err = build_feature_row(payload)
        if err:
            return jsonify(err), 400
        import pandas as pd
        try:
            df_enc = encode_row_to_training(pd.DataFrame([row_dict]))
            prob, conf = predict_with_stack(df_enc)
        except Exception as e:
            return jsonify({"error":"prediction_failed","message":str(e)}), 500

        # save record (use the global Record class directly)
        rec = Record(
            first_program=row_dict["Program (First Choice)"],
            second_program=row_dict["Program (Second Choice)"],
            curr_region=row_dict["Current Region"],
            curr_province=row_dict["Current Province"],
            curr_city=row_dict["Current City"],
            per_country=row_dict["Permanent Country"],
            per_region=row_dict["Permanent Region"],
            per_province=row_dict["Permanent Province"],
            per_city=row_dict["Permanent City"],
            student_type=row_dict["Student Type"],
            school_type=row_dict["School Type"],
            date_of_birth=payload.get("dateofbirth"),
            age_years=row_dict["Age"],
            local_or_foreign=row_dict["LocalOrForeign"],
            same_region=row_dict["SameRegion"],
            same_province=row_dict["SameProvince"],
            same_city=row_dict["SameCity"],
            prob_enroll_pct=prob,
            confidence=conf,
        )
        db.session.add(rec)
        db.session.commit()

        return jsonify({"prob_enroll_pct": prob, "confidence": conf})



    # Register simple page blueprints (these reference templates already included)
    from .view import view_bp
    from .auth import auth_bp
    app.register_blueprint(view_bp)
    app.register_blueprint(auth_bp)

    try: smoke_test_prediction(app)
    except Exception: pass

    return app

    


    

