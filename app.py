import html
import time
import streamlit as st
from PIL import Image
from google import genai
from core import MODEL, load_db, extract_name, check_duplicates, child_alerts

st.set_page_config(page_title="RxLens", page_icon="💊", layout="wide")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_data
def get_db():
    return load_db()


DB = get_db()
BRANDS = sorted(d["brand"] for d in DB.values())
WHO = ["Myself (adult)", "Another adult", "A child"]
DEMO_NAMES = ["Panadol Extra", "Panadol Cold & Flu"]

# The first entry is the main demo. The rest sit in a collapsed section.
SAMPLES = [
    {"label": "Duplicate paracetamol", "desc": "Panadol Extra + Panadol Cold & Flu",
     "names": ["Panadol Extra", "Panadol Cold & Flu"], "who": WHO[0], "age": 30, "weight": None},
    {"label": "Hidden in a combination", "desc": "Panadol + Buscopan Plus",
     "names": ["Panadol", "Buscopan Plus"], "who": WHO[0], "age": 30, "weight": None},
    {"label": "Ibuprofen under two brands", "desc": "Brufen + Arinac Forte",
     "names": ["Brufen", "Arinac Forte"], "who": WHO[0], "age": 30, "weight": None},
    {"label": "Two different NSAIDs", "desc": "Brufen + Disprin",
     "names": ["Brufen", "Disprin"], "who": WHO[0], "age": 30, "weight": None},
    {"label": "Child mode", "desc": "Calpol + Disprin, age 8, 25 kg",
     "names": ["Calpol", "Disprin"], "who": WHO[2], "age": 8, "weight": 25.0},
    {"label": "No overlap found", "desc": "Flagyl + Gravinate",
     "names": ["Flagyl", "Gravinate"], "who": WHO[0], "age": 30, "weight": None},
]


def src_kind(source):
    s = source.lower()
    if "not box-verified" in s or "reference" in s:
        return "ref"
    if "box scan" in s:
        return "box"
    return "doc"


N_BOX = sum(1 for d in DB.values() if src_kind(d["source"]) == "box")
N_DOC = sum(1 for d in DB.values() if src_kind(d["source"]) == "doc")
N_REF = sum(1 for d in DB.values() if src_kind(d["source"]) == "ref")

# ======================= STYLES =======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], p, h1, h2, h3, h4, label, button, input, textarea {font-family: 'Plus Jakarta Sans', sans-serif;}
#MainMenu {visibility: hidden;} footer {visibility: hidden;}
[data-testid="stAppDeployButton"], .stDeployButton {display: none !important;}
header[data-testid="stHeader"] {background: transparent;}
.stApp {background:
  radial-gradient(900px 480px at 88% -8%, rgba(99,102,241,.28) 0%, transparent 60%),
  radial-gradient(700px 420px at 4% 105%, rgba(34,211,238,.12) 0%, transparent 60%),
  #0B1020;}
.block-container {max-width: 1180px; padding-top: 3.2rem; padding-bottom: 3rem;}

@keyframes fadeUp {from {opacity:0; transform:translateY(10px);} to {opacity:1; transform:none;}}
@keyframes pulse {0%,100% {opacity:1; box-shadow:0 0 18px rgba(99,102,241,.5);} 50% {opacity:.7; box-shadow:0 0 34px rgba(34,211,238,.7);}}
@keyframes shimmer {0% {background-position:0% 50%;} 100% {background-position:100% 50%;}}

/* ---- top bar ---- */
.nav {display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;
  padding-bottom:14px; margin-bottom:26px; border-bottom:1px solid #243056;}
.brand {display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.logo {width:34px; height:34px; border-radius:10px; background:linear-gradient(135deg,#6366F1,#22D3EE);
  color:#fff; font-weight:800; display:inline-flex; align-items:center; justify-content:center; font-size:.9rem;
  box-shadow:0 0 18px rgba(99,102,241,.55);}
.brand-name {font-weight:800; font-size:1.2rem; color:#fff; letter-spacing:-.3px;}
.nav-r {display:flex; gap:8px; flex-wrap:wrap;}
.badge {display:inline-block; font-size:.66rem; font-weight:700; letter-spacing:.08em; padding:3px 10px;
  border-radius:999px; border:1px solid #2F3E66; color:#A5B2D0; background:#101830;}
.badge.blue {color:#A5B4FC; border-color:rgba(129,140,248,.5); background:rgba(99,102,241,.12);}
.badge.cyan {color:#67E8F9; border-color:rgba(34,211,238,.5); background:rgba(34,211,238,.10);}
.badge.green {color:#34D399; border-color:rgba(52,211,153,.45); background:rgba(52,211,153,.08);}
.badge.amber {color:#FBBF24; border-color:rgba(251,191,36,.45); background:rgba(251,191,36,.08);}

/* ---- landing ---- */
.eyebrow {font-size:.72rem; font-weight:700; letter-spacing:.16em; color:#67E8F9; margin-bottom:12px;}
.hero-h {font-size:2.8rem; font-weight:800; line-height:1.08; color:#fff; letter-spacing:-1.3px; margin:0 0 14px;
  animation: fadeUp .5s ease both;}
.hero-h span {background:linear-gradient(120deg,#818CF8,#22D3EE,#818CF8); background-size:200% 200%;
  -webkit-background-clip:text; background-clip:text; color:transparent; animation: shimmer 5s linear infinite alternate;}
.hero-sub {color:#A5B2D0; font-size:1.02rem; line-height:1.6; margin-bottom:22px; max-width:560px;}
.panel {background:linear-gradient(180deg,#141D38,#101830); border:1px solid #243056; border-radius:16px;
  padding:18px 20px; margin-bottom:14px; animation: fadeUp .5s ease both;
  box-shadow:0 10px 30px rgba(0,0,0,.25), 0 0 0 1px rgba(99,102,241,.05); transition:all .2s ease;}
.panel:hover {border-color:rgba(34,211,238,.45); box-shadow:0 10px 34px rgba(0,0,0,.3), 0 0 26px rgba(34,211,238,.12);}
.panel-t {font-size:.7rem; font-weight:700; letter-spacing:.14em; color:#8E9BBA; margin-bottom:12px;}
.how {display:flex; gap:12px; align-items:flex-start; margin-bottom:13px;}
.how:last-child {margin-bottom:0;}
.num {min-width:28px; height:28px; border-radius:50%; background:rgba(99,102,241,.18); color:#A5B4FC;
  border:1px solid rgba(129,140,248,.5); font-size:.8rem; font-weight:700; display:inline-flex;
  align-items:center; justify-content:center; box-shadow:0 0 12px rgba(99,102,241,.25);}
.how b {color:#fff; display:block; font-size:.95rem;}
.how span {color:#8E9BBA; font-size:.85rem; line-height:1.45;}
.tagline {margin-top:14px; padding-top:12px; border-top:1px solid #243056; color:#E6EDF7; font-weight:700; font-size:.92rem;}
.tagline span {color:#22D3EE;}
.sec {font-size:.72rem; font-weight:700; letter-spacing:.16em; color:#8E9BBA; margin:24px 0 10px;}
.stats {display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:6px;}
.stat {background:linear-gradient(180deg,#141D38,#101830); border:1px solid #243056; border-radius:14px; padding:14px 16px;
  transition:all .2s ease;}
.stat:hover {border-color:rgba(34,211,238,.45); box-shadow:0 0 22px rgba(34,211,238,.12);}
.stat b {display:block; color:#fff; font-size:1.6rem; font-weight:800; letter-spacing:-.5px;}
.stat span {color:#8E9BBA; font-size:.78rem;}
.pair {display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.pbox {background:#0B1020; border:1px solid #2F3E66; border-radius:12px; padding:10px 14px;}
.pbox b {display:block; color:#fff; font-size:.9rem;}
.chip {display:inline-block; margin-top:5px; font-size:.7rem; font-weight:700; color:#FCA5A5;
  background:rgba(248,113,113,.12); border:1px solid rgba(248,113,113,.4); border-radius:999px; padding:1px 9px;}
.plus {color:#22D3EE; font-size:1.3rem; font-weight:700;}
@media (max-width:760px){.stats{grid-template-columns:repeat(2,1fr);} .hero-h{font-size:2rem;}}

/* ---- stepper ---- */
.stepper {display:flex; align-items:center; margin:6px 0 20px;}
.step {display:flex; align-items:center; gap:8px; font-weight:600; font-size:.85rem; color:#64748B;}
.step .dot {width:27px; height:27px; border-radius:50%; background:#131B33; color:#8E9BBA; font-size:.75rem;
  display:inline-flex; align-items:center; justify-content:center; border:1px solid #243056;}
.step.active {color:#67E8F9;}
.step.active .dot {background:linear-gradient(135deg,#6366F1,#22D3EE); color:#fff; border-color:transparent;
  box-shadow:0 0 16px rgba(34,211,238,.5);}
.step.done {color:#34D399;} .step.done .dot {background:rgba(52,211,153,.15); color:#34D399; border-color:rgba(52,211,153,.5);}
.line {flex:1; height:2px; background:#243056; margin:0 12px;}

/* ---- titles ---- */
.title {font-size:1.55rem; font-weight:800; color:#fff; letter-spacing:-.4px; margin:0;}
.subtitle {color:#8E9BBA; font-size:.9rem; margin:2px 0 6px;}

/* ---- splash ---- */
.splash {text-align:center; padding:90px 0 14px; animation: fadeUp .3s ease both;}
.splash .logo {width:56px; height:56px; font-size:1.3rem; border-radius:15px; animation: pulse 1.5s infinite;}
.splash h3 {color:#fff; margin-top:14px; font-weight:700;}

/* ---- banner and cards ---- */
.banner {display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;
  border-radius:14px; padding:14px 18px; margin-bottom:10px; border:1px solid; animation: fadeUp .4s ease both;}
.banner b {font-size:1rem;} .banner span {font-size:.82rem; opacity:.85;}
.banner.bad {background:rgba(248,113,113,.10); border-color:rgba(248,113,113,.5); color:#FECACA;
  box-shadow:0 0 26px rgba(248,113,113,.14);}
.banner.ok {background:rgba(52,211,153,.08); border-color:rgba(52,211,153,.4); color:#A7F3D0;
  box-shadow:0 0 26px rgba(52,211,153,.10);}
.banner.warn {background:rgba(251,191,36,.08); border-color:rgba(251,191,36,.4); color:#FDE68A;}
.card {border-radius:14px; padding:14px 18px; margin:10px 0; border:1px solid; border-left-width:5px;
  animation: fadeUp .4s ease both; transition:transform .2s ease;}
.card:hover {transform:translateX(3px);}
.card-title {font-weight:700; margin-bottom:3px; font-size:.95rem;}
.card div {font-size:.88rem; line-height:1.5;}
.card.danger {background:rgba(248,113,113,.07); border-color:rgba(248,113,113,.35); border-left-color:#F87171; color:#FECACA;}
.card.ok {background:rgba(52,211,153,.07); border-color:rgba(52,211,153,.35); border-left-color:#34D399; color:#A7F3D0;}
.card.warn {background:rgba(251,191,36,.07); border-color:rgba(251,191,36,.35); border-left-color:#FBBF24; color:#FDE68A;}
.card.info {background:rgba(99,102,241,.09); border-color:rgba(129,140,248,.35); border-left-color:#818CF8; color:#C7D2FE;}
.empty {background:linear-gradient(180deg,#141D38,#101830); border:1px dashed #2F3E66; border-radius:16px;
  padding:42px 20px; text-align:center; color:#8E9BBA;}
.empty b {display:block; color:#E6EDF7; margin-bottom:4px;}
.tbl {width:100%; border-collapse:collapse; font-size:.82rem; margin-top:6px;}
.tbl th {text-align:left; color:#8E9BBA; font-weight:600; font-size:.7rem; letter-spacing:.08em; padding:8px;
  border-bottom:1px solid #243056;}
.tbl td {color:#E6EDF7; padding:9px 8px; border-bottom:1px solid #1A2644; vertical-align:top;}
.tbl-wrap {overflow-x:auto;}
.sess {background:linear-gradient(180deg,#141D38,#101830); border:1px solid #243056; border-radius:14px;
  padding:12px 14px; margin-bottom:12px;}
.sess small {color:#8E9BBA; font-size:.72rem;}
.sess b {color:#fff; display:block; font-size:.95rem;}

/* ---- glowing buttons ---- */
div.stButton > button, div.stDownloadButton > button {
  background:#131B33; color:#E6EDF7; border:1px solid #2F3E66; border-radius:12px; font-weight:600;
  padding:.6rem 1.2rem; box-shadow:0 0 0 rgba(34,211,238,0); transition:all .18s ease;}
div.stButton > button *, div.stDownloadButton > button * {color:inherit !important;}
div.stButton > button:hover, div.stDownloadButton > button:hover {
  border-color:#22D3EE; background:#16213F; color:#fff; transform:translateY(-2px);
  box-shadow:0 6px 22px rgba(34,211,238,.28);}
div.stButton > button[kind="primary"], div.stButton > button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(135deg,#6366F1,#22D3EE); border:none; color:#fff; font-weight:700;
  box-shadow:0 6px 22px rgba(99,102,241,.45);}
div.stButton > button[kind="primary"]:hover, div.stButton > button[data-testid="stBaseButton-primary"]:hover {
  transform:translateY(-3px); box-shadow:0 10px 32px rgba(34,211,238,.55);}
div.stButton > button:disabled {background:#101830; color:#475569; border-color:#1A2644; box-shadow:none; transform:none;}

[data-testid="stFileUploaderDropzone"] {background:#101830; border:1.5px dashed #3B4A78; border-radius:14px;}
[data-testid="stFileUploaderDropzone"]:hover {border-color:#22D3EE; box-shadow:0 0 20px rgba(34,211,238,.12);}
[data-testid="stSidebar"] {background:#0C1328 !important; border-right:1px solid #243056;}
[data-testid="stSidebar"] * {color:#E6EDF7;}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {color:#22D3EE;}
</style>
""", unsafe_allow_html=True)


# ======================= HELPERS =======================
def esc(x):
    return html.escape(str(x))


def card(kind, title, body="", delay=0.0):
    st.markdown(f'<div class="card {kind}" style="animation-delay:{delay}s">'
                f'<div class="card-title">{title}</div><div>{body}</div></div>',
                unsafe_allow_html=True)


def nav_bar():
    st.markdown(
        '<div class="nav"><div class="brand"><span class="logo">Rx</span>'
        '<span class="brand-name">RxLens</span>'
        '<span class="badge blue">GEMINI VISION</span><span class="badge cyan">RULE ENGINE</span></div>'
        f'<div class="nav-r"><span class="badge">{len(DB)} PRODUCTS</span>'
        '<span class="badge amber">NOT MEDICAL ADVICE</span></div></div>',
        unsafe_allow_html=True)


def stepper_html(current):
    labels = ["Profile", "Scan and confirm", "Results"]
    parts = []
    for i, label in enumerate(labels, 1):
        cls = "done" if i < current else "active" if i == current else ""
        parts.append(f'<div class="step {cls}"><span class="dot">{"✓" if i < current else i}</span>{label}</div>')
    return '<div class="stepper">' + '<div class="line"></div>'.join(parts) + '</div>'


def splash_then(slot, next_stage, message):
    slot.empty()
    st.markdown(f'<div class="splash"><span class="logo">Rx</span><h3>{message}</h3></div>',
                unsafe_allow_html=True)
    bar = st.progress(0, text="Loading medicine database")
    labels = ["Loading medicine database", "Preparing the AI reader", "Almost ready"]
    for p in range(0, 101, 10):
        time.sleep(0.05)
        bar.progress(p, text=labels[min(p // 40, 2)])
    st.session_state["stage"] = next_stage
    st.rerun()


def start_sample(s):
    st.session_state["demo"] = True
    st.session_state["demo_names"] = list(s["names"])
    st.session_state["demo_label"] = s["label"]
    st.session_state["auto_run"] = True
    st.session_state["profile"] = {"who": s["who"], "age": s["age"], "weight": s["weight"], "allergies": ""}
    st.session_state.pop("result", None)


ALLERGY_MAP = {
    "penicillin": ["amoxicillin", "ampicillin", "clavulanic acid"],
    "nsaid": ["nsaid", "ibuprofen", "diclofenac", "aspirin", "mefenamic acid"],
    "sulfa": ["sulfamethoxazole"],
}


def allergy_hits(text, verified):
    hits = set()
    for t in [t.strip().lower() for t in text.split(",") if t.strip()]:
        if t.endswith("s") and len(t) > 3:
            t = t[:-1]
        keys = {t} | set(ALLERGY_MAP.get(t, []))
        for _, e in verified:
            hay = list(e["ingredients"]) + list(e["drug_class"])
            if any(k in h or h in k for k in keys for h in hay if h):
                hits.add((t, e["brand"]))
    return sorted(hits)


def render_results(saved, prof, is_child):
    verified, unverified, duplicates, interactions = saved["data"]
    cards = []

    if is_child:
        w = f"{prof['weight']:g} kg" if prof.get("weight") else "weight not given"
        cards.append(("warn", "👶 Child mode",
                      f"Age {prof['age']}, {w} noted. RxLens does <b>not</b> calculate child doses. "
                      f"Use the dosing chart on the box or ask a pharmacist or doctor."))
        for _, e in verified:
            if "ml" in e["strength"].lower() and "/" in e["strength"]:
                cards.append(("info", f"🧴 {esc(e['brand'])}: label concentration {esc(e['strength'])}",
                              "The correct amount depends on weight and age. Follow the box's chart. "
                              "Never use an adult product for a child without asking a pharmacist."))
        for a in child_alerts(verified, prof["age"]):
            cards.append(("danger", f"🚫 {esc(a['title'])}", esc(a["desc"])))

    if prof["allergies"].strip():
        hits = allergy_hits(prof["allergies"], verified)
        if hits:
            for term, brand in hits:
                cards.append(("danger", f"🚨 Possible allergy match: {esc(term)}",
                              f"<b>{esc(brand)}</b> may be related to the allergy you listed. "
                              f"Ask a pharmacist before use."))
        else:
            cards.append(("info", "Allergy keyword check",
                          f"No match for “{esc(prof['allergies'])}” among matched products. "
                          f"This is a simple keyword check, not a guarantee."))

    for ing, info in duplicates.items():
        body = f"Found in {esc(', '.join(info['prods']))}. "
        if info["total_dose"] > 0:
            body += (f"Listed strengths add up to <b>{info['total_dose']:g} mg</b> "
                     f"if one dose of each is taken together. ")
            if not is_child and info["single_limit"] and info["total_dose"] > info["single_limit"]:
                body += (f"<b>That is above the usual adult single-dose maximum on labels "
                         f"({info['single_limit']:g} mg).</b> ")
            if not is_child and info["daily_limit"]:
                body += (f"Doses from all products count toward the same adult daily maximum on labels "
                         f"({info['daily_limit']:g} mg). ")
        else:
            body += "The listed strengths could not be added reliably. "
        body += "Confirm with a pharmacist before combining."
        cards.append(("danger", f"⚠️ Possible duplicate ingredient: {esc(ing.title())}", body))

    for inter in interactions:
        cards.append(("danger", f"🛡️ {esc(inter['title'])}", esc(inter["desc"])))

    if unverified:
        cards.append(("warn", f"❓ Couldn't verify: {esc(', '.join(unverified))}",
                      "Not in our database, so these were NOT checked. Ask your pharmacist."))

    flags = sum(1 for c in cards if c[0] == "danger")
    if flags:
        st.markdown(f'<div class="banner bad"><b>{flags} flag{"s" if flags != 1 else ""} for pharmacist review</b>'
                    f'<span>{len(verified)} matched · {len(unverified)} unverified</span></div>',
                    unsafe_allow_html=True)
    elif verified:
        st.markdown('<div class="banner ok"><b>No duplicate or rule triggered</b>'
                    '<span>Not a safety guarantee. RxLens only checks its own database.</span></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="banner warn"><b>Nothing could be verified</b>'
                    '<span>None of these products are in the database.</span></div>',
                    unsafe_allow_html=True)

    for i, (kind, title, body) in enumerate(cards):
        card(kind, title, body, round(i * 0.08, 2))

    if verified:
        labels = {"box": ("Box-verified", "green"), "doc": ("Leaflet", "blue"),
                  "ref": ("Public reference, unverified", "amber")}
        rows = ""
        for typed, e in verified:
            text, color = labels[src_kind(e["source"])]
            shown = esc(e["brand"])
            if typed.strip().lower() != e["brand"].lower():
                shown = f'{esc(typed)} → {esc(e["brand"])}'
            rows += (f'<tr><td><b>{shown}</b></td><td>{esc(", ".join(e["ingredients"]))}</td>'
                     f'<td>{esc(e["strength"])}</td>'
                     f'<td><span class="badge {color}">{text}</span></td></tr>')
        st.markdown('<div class="sec">EVIDENCE TRAIL</div><div class="tbl-wrap"><table class="tbl">'
                    '<tr><th>PRODUCT</th><th>ACTIVE INGREDIENTS</th><th>STRENGTH</th><th>SOURCE</th></tr>'
                    + rows + '</table></div>', unsafe_allow_html=True)

    lines = ["RxLens summary (not medical advice)", f"For: {prof['who']}, {prof['age']} y", ""]
    for _, e in verified:
        lines.append(f"- {e['brand']}: {', '.join(e['ingredients'])} ({e['strength']}) [{e['source']}]")
    for u in unverified:
        lines.append(f"- {u}: NOT VERIFIED")
    lines.append("")
    for ing, info in duplicates.items():
        dose = f" (listed doses add up to {info['total_dose']:g} mg)" if info["total_dose"] > 0 else ""
        lines.append(f"POSSIBLE DUPLICATE: {ing} in {', '.join(info['prods'])}{dose}")
    for inter in interactions:
        lines.append(f"RULE TRIGGERED: {inter['title']}")
    if not duplicates and not interactions:
        lines.append("No duplicate or rule triggered among verified products (not a safety guarantee).")
    lines.append("Please confirm with a pharmacist or doctor.")
    st.download_button("Download summary for your pharmacist", "\n".join(lines),
                       file_name="rxlens_summary.txt")


st.session_state.setdefault("stage", "welcome")
st.session_state.setdefault("demo", False)
st.session_state.setdefault("profile", {"who": WHO[0], "age": 30, "weight": None, "allergies": ""})
stage = st.session_state["stage"]

# ======================= 1. LANDING =======================
if stage == "welcome":
    slot = st.empty()
    chosen = None
    with slot.container():
        nav_bar()
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            st.markdown(
                '<div class="eyebrow">MEDICINE SAFETY ASSISTANT</div>'
                '<div class="hero-h">Same medicine. <span>Different brand name.</span> Spot it before you double up.</div>'
                '<div class="hero-sub">Photograph your medicine boxes. AI reads the names, you confirm them, '
                'and transparent code checks a sourced database for overlapping active ingredients.</div>',
                unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            start = b1.button("Start a medicine check", type="primary", use_container_width=True, key="w_start")
            demo = b2.button("🎬 Try a demo scenario", use_container_width=True, key="w_demo")
        with right:
            st.markdown(
                '<div class="panel"><div class="panel-t">HOW IT WORKS</div>'
                '<div class="how"><span class="num">1</span><div><b>AI reads the box</b>'
                '<span>Gemini vision extracts the brand name from your photo.</span></div></div>'
                '<div class="how"><span class="num">2</span><div><b>You confirm</b>'
                '<span>AI can misread, so you correct names before any check runs.</span></div></div>'
                '<div class="how"><span class="num">3</span><div><b>Rules decide</b>'
                '<span>Plain code compares ingredients from a sourced database.</span></div></div>'
                '<div class="tagline">AI reads. <span>Rules decide.</span></div></div>',
                unsafe_allow_html=True)

        st.markdown(
            '<div class="sec">THE HIDDEN-INGREDIENT PROBLEM</div>'
            '<div class="panel"><div class="pair">'
            '<div class="pbox"><b>Panadol Extra</b><span class="chip">paracetamol</span></div><span class="plus">+</span>'
            '<div class="pbox"><b>Panadol Cold &amp; Flu</b><span class="chip">paracetamol</span></div>'
            '<span style="color:#8E9BBA;font-size:.88rem;margin-left:8px;">Two different-looking boxes, '
            'one ingredient. Easy to double up without noticing.</span></div></div>'
            '<div class="stats">'
            f'<div class="stat"><b>{len(DB)}</b><span>Products in database</span></div>'
            f'<div class="stat"><b>{N_BOX}</b><span>Box-verified</span></div>'
            '<div class="stat"><b>3</b><span>Result states, never "safe"</span></div>'
            '<div class="stat"><b>0</b><span>Images stored</span></div></div>',
            unsafe_allow_html=True)

        with st.expander("More sample scenarios"):
            rest = list(range(1, len(SAMPLES)))
            for r in range(0, len(rest), 3):
                cols = st.columns(3)
                for col, idx in zip(cols, rest[r:r + 3]):
                    s = SAMPLES[idx]
                    if col.button(s["label"], help=s["desc"], use_container_width=True, key=f"sample_{idx}"):
                        chosen = idx

    if start:
        st.session_state["demo"] = False
        splash_then(slot, "setup", "Preparing your session…")
    if demo:
        start_sample(SAMPLES[0])
        splash_then(slot, "check", "Loading the demo scenario…")
    if chosen is not None:
        start_sample(SAMPLES[chosen])
        splash_then(slot, "check", "Loading the sample scenario…")

# ======================= 2. PROFILE =======================
elif stage == "setup":
    st.session_state["demo"] = False
    nav_bar()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="title">Who is this check for?</div>'
                    '<div class="subtitle">This changes which safety rules apply.</div>',
                    unsafe_allow_html=True)
        st.markdown(stepper_html(1), unsafe_allow_html=True)
        p = st.session_state["profile"]

        who = st.radio("Patient", WHO, horizontal=True, index=WHO.index(p["who"]))
        weight = None
        if who == "A child":
            c1, c2 = st.columns(2)
            age = c1.number_input("Child's age (years)", 0, 17, min(int(p["age"]), 17))
            weight = c2.number_input("Child's weight (kg)", 1.0, 120.0, float(p["weight"] or 15.0), step=0.5)
            st.info("RxLens never calculates child doses. It shows the label's concentration and "
                    "sends you to the box's dosing chart or a pharmacist.")
        else:
            age = st.number_input("Age (years)", 18, 120, max(int(p["age"]), 18))
        allergies = st.text_input("Known allergies (optional)", value=p["allergies"],
                                  placeholder="e.g. penicillin, NSAIDs")

        c1, c2 = st.columns(2)
        if c1.button("← Back", use_container_width=True, key="setup_back"):
            st.session_state["stage"] = "welcome"
            st.rerun()
        if c2.button("Continue to scan →", type="primary", use_container_width=True, key="setup_next"):
            st.session_state["profile"] = {"who": who, "age": int(age), "weight": weight, "allergies": allergies}
            st.session_state["stage"] = "check"
            st.rerun()

# ======================= 3. CHECK =======================
else:
    prof = st.session_state["profile"]
    is_child = prof["who"] == "A child"
    demo_mode = st.session_state.get("demo", False)

    with st.sidebar:
        who_line = f"{prof['who']}, {prof['age']} y" + (f", {prof['weight']:g} kg" if is_child and prof.get("weight") else "")
        st.markdown(f'<div class="sess"><small>SESSION</small><b>Anonymous</b>'
                    f'<small>No account · nothing stored</small></div>'
                    f'<div class="sess"><small>CHECKING FOR</small><b>{esc(who_line)}</b></div>',
                    unsafe_allow_html=True)
        if st.button("Edit profile", use_container_width=True, key="side_edit"):
            st.session_state["stage"] = "setup"
            st.rerun()
        if st.button("Home", use_container_width=True, key="side_home"):
            st.session_state["stage"] = "welcome"
            st.session_state.pop("result", None)
            st.rerun()
        st.markdown("---")
        st.markdown("**Database sources**")
        st.write(f"Box-verified: {N_BOX}")
        st.write(f"Leaflet: {N_DOC}")
        st.write(f"Public reference: {N_REF}")
        st.caption("Products not in the database are marked 'couldn't verify', never guessed. "
                   "Images are processed in memory and never stored. Not medical advice.")

    nav_bar()
    n1, n2, _ = st.columns([1, 1, 6])
    if n1.button("← Back", use_container_width=True, key="nav_back"):
        st.session_state["stage"] = "welcome" if demo_mode else "setup"
        st.rerun()
    if n2.button("Home", use_container_width=True, key="nav_home"):
        st.session_state["stage"] = "welcome"
        st.session_state.pop("result", None)
        st.rerun()

    st.markdown('<div class="title">New medicine check</div>'
                '<div class="subtitle">Add at least two medicines to compare.</div>', unsafe_allow_html=True)
    stepper_slot = st.empty()

    left, right = st.columns([1.05, 1], gap="large")
    names = []

    with left:
        st.markdown('<div class="sec" style="margin-top:4px">1 · INPUT</div>', unsafe_allow_html=True)
        if demo_mode:
            names = list(st.session_state.get("demo_names", DEMO_NAMES))
            card("info", f"Demo scenario: {esc(st.session_state.get('demo_label', 'Demo'))}",
                 "Medicines are pre-loaded, so no photo upload is needed. "
                 "Press Home and choose Start to scan your own boxes.")
            for n in names:
                st.write(f"💊 {n}")
        else:
            tab_photo, tab_list = st.tabs(["Scan packages", "Pick from list"])
            with tab_photo:
                st.caption("Photograph the front of each box in good light, one box per photo.")
                files = st.file_uploader("Drop photos here", type=["jpg", "jpeg", "png"],
                                         accept_multiple_files=True, label_visibility="collapsed")
                if files:
                    st.markdown("**Check what the AI read.** Fix anything that's wrong.")
                for i, f in enumerate(files or []):
                    key = f"{f.name}-{f.size}"
                    if key not in st.session_state or "error" in st.session_state[key]:
                        with st.spinner(f"Reading {f.name}…"):
                            try:
                                st.session_state[key] = extract_name(client, Image.open(f), MODEL)
                            except Exception as e:
                                st.session_state[key] = {"brand_name": "", "strength": "", "error": str(e)}
                    data = st.session_state[key]
                    c1, c2 = st.columns([1, 2])
                    c1.image(Image.open(f), width=110)
                    if "error" in data:
                        c2.warning("The AI couldn't read this photo. Type the name yourself.")
                        c2.caption("Reason: " + str(data["error"])[:300])
                    name = c2.text_input("Medicine name", value=data.get("brand_name", ""), key=f"name-{i}-{key}")
                    if data.get("strength"):
                        c2.caption(f"Strength seen on the box: {data['strength']}")
                    if name.strip():
                        names.append(name.strip())
            with tab_list:
                st.caption("No photo? Choose from the database instead.")
                names += st.multiselect("Medicines", BRANDS, key="picked", label_visibility="collapsed")

        st.metric("Medicines queued", len(names))
        auto_run = bool(st.session_state.pop("auto_run", False)) and len(names) >= 2
        clicked = st.button("⚡ Run safety check", type="primary", use_container_width=True,
                            disabled=len(names) < 2, key="run_btn")
        run = clicked or auto_run

        if run:
            with st.status("Running checks…", expanded=True) as status:
                st.write("🔎 Matching names against the database")
                time.sleep(0.35)
                data = check_duplicates(names, DB)
                st.write("🧪 Comparing active ingredients and adding up listed doses")
                time.sleep(0.35)
                st.write("🧬 Applying interaction and age rules")
                time.sleep(0.35)
                status.update(label="Checks complete", state="complete", expanded=False)
            st.session_state["result"] = {"names": tuple(names), "data": data}
            st.toast("Results are ready", icon="✅")

    saved = st.session_state.get("result")
    show = bool(saved) and saved["names"] == tuple(names) and len(names) >= 2

    with right:
        st.markdown('<div class="sec" style="margin-top:4px">2 · ANALYSIS</div>', unsafe_allow_html=True)
        if show:
            render_results(saved, prof, is_child)
        else:
            st.markdown('<div class="empty"><b>Awaiting analysis</b>'
                        'Add two or more medicines and run the check. Results, the evidence trail '
                        'and a pharmacist summary appear here.</div>', unsafe_allow_html=True)

    stepper_slot.markdown(stepper_html(3 if show else 2), unsafe_allow_html=True)