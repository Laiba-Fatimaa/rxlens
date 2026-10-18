import html
import time
import streamlit as st
from PIL import Image
from google import genai
from core import MODEL, load_db, extract_name, check_duplicates, child_alerts

st.set_page_config(page_title="RxLens", page_icon="💊", layout="centered")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_data
def get_db():
    return load_db()


DB = get_db()
BRANDS = sorted(d["brand"] for d in DB.values())
WHO = ["Myself (adult)", "Another adult", "A child"]
DEMO_NAMES = ["Panadol Extra", "Panadol Cold & Flu"]

# ======================= STYLES (dark) =======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], p, h1, h2, h3, h4, label, button, input {font-family: 'Plus Jakarta Sans', sans-serif;}
#MainMenu {visibility: hidden;} footer {visibility: hidden;}
.stApp {background: radial-gradient(1200px 600px at 80% -10%, #1E1B4B 0%, #0B1020 55%);}
.block-container {max-width: 860px; padding-top: 1.5rem;}

@keyframes fadeUp {from {opacity:0; transform:translateY(18px);} to {opacity:1; transform:none;}}
@keyframes slideIn {from {opacity:0; transform:translateX(-24px);} to {opacity:1; transform:none;}}
@keyframes floaty {0%,100% {transform:translateY(0) rotate(-6deg);} 50% {transform:translateY(-12px) rotate(6deg);}}
@keyframes glow {0%,100% {box-shadow:0 0 24px rgba(34,211,238,.25);} 50% {box-shadow:0 0 44px rgba(167,139,250,.45);}}
@keyframes pop {0% {transform:scale(.6); opacity:0;} 70% {transform:scale(1.08);} 100% {transform:scale(1); opacity:1;}}

.hero {background: linear-gradient(135deg, #312E81, #0E7490); border:1px solid rgba(34,211,238,.35);
  text-align:center; padding:42px 28px; border-radius:24px; margin-bottom:18px;
  animation: fadeUp .7s ease both, glow 5s ease-in-out infinite;}
.hero h1 {color:#fff !important; font-size:3.1rem; font-weight:800; margin:6px 0; letter-spacing:-1px;}
.hero p {color:#CFFAFE !important; font-size:1.1rem; margin:0;}
.float {display:inline-block; font-size:3.3rem; animation: floaty 3s ease-in-out infinite;}

.problem {background:#131B33; border:1px solid #243056; border-radius:20px; padding:22px; margin:16px 0; animation: fadeUp .8s ease both;}
.problem h3 {margin:0 0 12px; color:#fff;}
.pair {display:flex; align-items:center; gap:10px; flex-wrap:wrap; justify-content:center;}
.box {background:#0B1020; border:1px solid #334155; border-radius:14px; padding:12px 16px; text-align:center; min-width:150px;}
.box b {color:#fff; display:block;}
.chip {display:inline-block; margin-top:6px; background:rgba(248,113,113,.15); color:#FCA5A5;
  border:1px solid rgba(248,113,113,.5); border-radius:999px; padding:2px 10px; font-size:.8rem; font-weight:700;}
.plus {font-size:1.6rem; color:#67E8F9;}
.arrow {color:#94A3B8; margin:10px 0 0; text-align:center;}

.features {display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:16px;}
.feature {background:#131B33; border:1px solid #243056; border-radius:18px; padding:18px 14px; text-align:center;
  animation: fadeUp .8s ease both; transition: transform .2s ease, border-color .2s ease;}
.feature:nth-child(2){animation-delay:.15s;} .feature:nth-child(3){animation-delay:.3s;}
.feature:hover {transform:translateY(-6px); border-color:#22D3EE;}
.feature .ico {font-size:2rem;} .feature b {display:block; color:#fff; margin:6px 0 4px;}
.feature span {color:#94A3B8; font-size:.86rem;}
@media (max-width:640px){.features{grid-template-columns:1fr;}}

.notice {background:rgba(99,102,241,.12); border-left:5px solid #818CF8; color:#C7D2FE;
  border-radius:12px; padding:12px 16px; font-size:.9rem; margin:6px 0 18px;}

.splash {text-align:center; padding:70px 0 10px; animation: fadeUp .4s ease both;}
.splash h3 {color:#fff; margin-top:10px;}

.topbar {animation: slideIn .5s ease both;} .topbar h2 {margin:0; font-weight:800; color:#fff;}
.topbar span {color:#94A3B8;}
.stepper {display:flex; align-items:center; margin:14px 0 22px; animation: fadeUp .5s ease both;}
.step {display:flex; align-items:center; gap:8px; font-weight:600; color:#64748B;}
.step .dot {width:30px; height:30px; border-radius:50%; background:#1E293B; color:#94A3B8;
  display:inline-flex; align-items:center; justify-content:center; font-size:.85rem;}
.step.active {color:#67E8F9;}
.step.active .dot {background:linear-gradient(135deg,#6366F1,#22D3EE); color:#fff; animation: pop .4s ease both;}
.step.done {color:#34D399;} .step.done .dot {background:#10B981; color:#fff;}
.line {flex:1; height:3px; background:#1E293B; margin:0 12px; border-radius:3px;}

[data-testid="stFileUploaderDropzone"] {border:2px dashed #4F46E5; border-radius:18px; transition: all .2s ease;}
[data-testid="stFileUploaderDropzone"]:hover {border-color:#22D3EE;}

.card {border-radius:16px; padding:16px 20px; margin:12px 0; border-left:7px solid;
  animation: slideIn .5s ease both; transition: transform .2s ease;}
.card:hover {transform:translateX(4px);}
.card-title {font-weight:800; margin-bottom:4px; font-size:1.02rem;}
.card.danger {background:#2A1215; border-color:#F87171; color:#FECACA;}
.card.ok {background:#0B2A22; border-color:#34D399; color:#A7F3D0;}
.card.warn {background:#2B2110; border-color:#FBBF24; color:#FDE68A;}
.card.info {background:#10243D; border-color:#60A5FA; color:#BFDBFE;}

div.stButton > button, div.stDownloadButton > button {
  background:linear-gradient(135deg,#6366F1,#22D3EE); color:#fff; border:none; border-radius:14px;
  font-weight:700; padding:.7rem 1.6rem; box-shadow:0 8px 22px rgba(99,102,241,.35); transition:all .2s ease;}
div.stButton > button:hover, div.stDownloadButton > button:hover {transform:translateY(-3px); color:#fff;
  box-shadow:0 12px 28px rgba(34,211,238,.35);}
div.stButton > button:disabled {background:#1E293B; color:#64748B; box-shadow:none;}

/* ---- fixes ---- */
.block-container {padding-top: 3.5rem !important;}
[data-testid="stAppDeployButton"], .stDeployButton {display: none !important;}
header[data-testid="stHeader"] {background: transparent;}
[data-testid="stSidebar"] {background: #0F1730 !important; border-right: 1px solid #243056;}
[data-testid="stSidebar"] * {color: #E6EDF7 !important;}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {color: #22D3EE !important;}
.hero {padding: 24px 24px !important; margin-bottom: 14px !important;}
.hero h1 {font-size: 2.4rem !important; margin: 2px 0 !important;}
.hero .float {font-size: 2.4rem !important;}
</style>
""", unsafe_allow_html=True)


# ======================= HELPERS =======================
def esc(x):
    return html.escape(str(x))


def card(kind, title, body="", delay=0.0):
    st.markdown(f'<div class="card {kind}" style="animation-delay:{delay}s">'
                f'<div class="card-title">{title}</div><div>{body}</div></div>',
                unsafe_allow_html=True)


def stepper_html(current):
    labels = ["Profile", "Scan & confirm", "Results"]
    parts = []
    for i, label in enumerate(labels, 1):
        cls = "done" if i < current else "active" if i == current else ""
        parts.append(f'<div class="step {cls}"><span class="dot">{"✓" if i < current else i}</span>{label}</div>')
    return '<div class="stepper">' + '<div class="line"></div>'.join(parts) + '</div>'


def splash_then(slot, next_stage, message):
    slot.empty()
    st.markdown(f'<div class="splash"><div class="float">💊</div><h3>{message}</h3></div>',
                unsafe_allow_html=True)
    bar = st.progress(0, text="Loading medicine database")
    labels = ["Loading medicine database", "Warming up the AI reader", "Almost ready"]
    for p in range(0, 101, 10):
        time.sleep(0.06)
        bar.progress(p, text=labels[min(p // 40, 2)])
    st.session_state["stage"] = next_stage
    st.rerun()


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


st.session_state.setdefault("stage", "welcome")
st.session_state.setdefault("demo", False)
st.session_state.setdefault("profile", {"who": WHO[0], "age": 30, "weight": None, "allergies": ""})
stage = st.session_state["stage"]

# ======================= 1. WELCOME =======================
if stage == "welcome":
    slot = st.empty()
    with slot.container():
        st.markdown("""
<div class="hero"><div class="float">💊</div><h1>RxLens</h1>
<p>The same medicine can hide under different brand names. We help you spot it.</p></div>
""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        start = c1.button("🚀 Start a medicine check", use_container_width=True)
        demo = c2.button("🎬 Try a demo scenario", use_container_width=True)

        st.markdown("""
<div class="problem"><h3>The hidden-ingredient problem</h3>
<div class="pair">
  <div class="box"><b>Panadol Extra</b><span class="chip">paracetamol</span></div>
  <div class="plus">+</div>
  <div class="box"><b>Panadol Cold &amp; Flu</b><span class="chip">paracetamol</span></div>
</div>
<p class="arrow">Two different-looking boxes. One ingredient. Easy to double up without noticing.</p></div>

<div class="features">
<div class="feature"><div class="ico">📸</div><b>AI reads</b><span>Gemini reads the name from your photo</span></div>
<div class="feature"><div class="ico">✍️</div><b>You confirm</b><span>AI can be wrong, so you correct names first</span></div>
<div class="feature"><div class="ico">🧮</div><b>Code checks</b><span>Plain, readable rules compare ingredients</span></div>
</div>
<div class="notice"><b>Not medical advice.</b> RxLens flags possible duplication for pharmacist
confirmation. Images are processed in memory and are not stored.</div>
""", unsafe_allow_html=True)

    if start:
        st.session_state["demo"] = False
        splash_then(slot, "setup", "Preparing your session…")
    if demo:
        st.session_state["demo"] = True
        st.session_state["auto_run"] = True
        st.session_state["profile"] = {"who": WHO[0], "age": 30, "weight": None, "allergies": ""}
        st.session_state.pop("result", None)
        splash_then(slot, "check", "Loading the demo scenario…")

# ======================= 2. PROFILE =======================
elif stage == "setup":
    st.session_state["demo"] = False
    st.markdown('<div class="topbar"><h2>👤 Who is this check for?</h2>'
                '<span>This changes which safety rules apply.</span></div>', unsafe_allow_html=True)
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
    if c2.button("Continue to scan →", use_container_width=True, key="setup_next"):
        st.session_state["profile"] = {"who": who, "age": int(age), "weight": weight, "allergies": allergies}
        st.session_state["stage"] = "check"
        st.rerun()

# ======================= 3. SCAN / CONFIRM / RESULTS =======================
else:
    prof = st.session_state["profile"]
    is_child = prof["who"] == "A child"
    demo_mode = st.session_state.get("demo", False)

    with st.sidebar:
        st.markdown("### 💊 RxLens")
        st.metric("Verified products in database", len(DB))
        st.markdown(f"**Checking for:** {prof['who']}, {prof['age']} y"
                    + (f", {prof['weight']:g} kg" if is_child else ""))
        if st.button("✏️ Edit profile", use_container_width=True, key="side_edit"):
            st.session_state["stage"] = "setup"
            st.rerun()
        if st.button("🏠 Home", use_container_width=True, key="side_home"):
            st.session_state["stage"] = "welcome"
            st.session_state.pop("result", None)
            st.rerun()
        st.caption("🔒 Images are processed in memory and never stored. Small database, packaging "
                   "only. Products not in the database are marked 'couldn't verify'. Not medical advice.")

    nav1, nav2, _ = st.columns([1, 1, 2])
    if nav1.button("← Back", use_container_width=True, key="nav_back"):
        st.session_state["stage"] = "setup"
        st.rerun()
    if nav2.button("🏠 Home", use_container_width=True, key="nav_home"):
        st.session_state["stage"] = "welcome"
        st.session_state.pop("result", None)
        st.rerun()

    st.markdown('<div class="topbar"><h2>💊 New medicine check</h2>'
                '<span>Add at least two medicines to compare.</span></div>', unsafe_allow_html=True)
    stepper_slot = st.empty()

    names = []
    if demo_mode:
        # DEMO: no upload, no widgets. The two medicines are loaded directly.
        names = list(DEMO_NAMES)
        card("info", "🎬 Demo scenario",
             "Panadol Extra and Panadol Cold &amp; Flu are pre-loaded, so no photo upload is needed. "
             "To scan your own boxes, press Home and choose Start.")
        for n in names:
            st.write(f"💊 {n}")
    else:
        tab_photo, tab_list = st.tabs(["📸 Scan packages", "⌨️ Pick from list"])
        with tab_photo:
            st.caption("Photograph the front of each box in good light, one box per photo.")
            files = st.file_uploader("Drop photos here", type=["jpg", "jpeg", "png"],
                                     accept_multiple_files=True, label_visibility="collapsed")
            if files:
                st.markdown("**Check what the AI read.** Fix anything that's wrong.")
            for i, f in enumerate(files or []):
                key = f"{f.name}-{f.size}"
                if key not in st.session_state or "error" in st.session_state[key]:
                    with st.spinner(f"🔍 Reading {f.name}…"):
                        try:
                            st.session_state[key] = extract_name(client, Image.open(f), MODEL)
                        except Exception as e:
                            st.session_state[key] = {"brand_name": "", "strength": "", "error": str(e)}
                data = st.session_state[key]
                c1, c2 = st.columns([1, 2])
                c1.image(Image.open(f), width=130)
                if "error" in data:
                    c2.warning("The AI couldn't read this photo. Type the name yourself.")
                    c2.caption("Reason: " + str(data["error"])[:300])
                name = c2.text_input("Medicine name", value=data.get("brand_name", ""), key=f"name-{i}-{key}")
                if data.get("strength"):
                    c2.caption(f"Strength seen on the box: {data['strength']}")
                if name.strip():
                    names.append(name.strip())
        with tab_list:
            st.caption("No photo? Choose from the verified database instead.")
            names += st.multiselect("Medicines", BRANDS, key="picked", label_visibility="collapsed")

    st.divider()
    st.metric("Medicines ready to check", len(names))
    auto_run = bool(st.session_state.pop("auto_run", False)) and len(names) >= 2
    clicked = st.button("⚡ Run safety check", use_container_width=True, disabled=len(names) < 2)
    run = clicked or auto_run

    if run:
        with st.status("Running checks…", expanded=True) as status:
            st.write("🔎 Matching names against the database")
            time.sleep(0.4)
            data = check_duplicates(names, DB)
            st.write("🧪 Comparing active ingredients and adding up listed doses")
            time.sleep(0.4)
            st.write("🧬 Applying interaction and age rules")
            time.sleep(0.4)
            status.update(label="Checks complete", state="complete", expanded=False)
        st.session_state["result"] = {"names": tuple(names), "data": data}
        st.toast("Results are ready", icon="✅")

    saved = st.session_state.get("result")
    show = bool(saved) and saved["names"] == tuple(names) and len(names) >= 2

    if show:
        verified, unverified, duplicates, interactions = saved["data"]
        st.markdown("### 📊 Results")
        d = 0.0

        if is_child:
            card("warn", "👶 Child mode",
                 f"Age {prof['age']}, weight {prof['weight']:g} kg noted. RxLens does <b>not</b> calculate "
                 f"child doses. Use the dosing chart on the box or ask a pharmacist or doctor.", d)
            d += 0.12
            for _, e in verified:
                if "ml" in e["strength"].lower() and "/" in e["strength"]:
                    card("info", f"🧴 {esc(e['brand'])}: label concentration {esc(e['strength'])}",
                         "The correct amount depends on weight and age. Follow the box's chart. "
                         "Never use an adult product for a child without asking a pharmacist.", d)
                    d += 0.12
            for a in child_alerts(verified, prof["age"]):
                card("danger", f"🚫 {esc(a['title'])}", esc(a["desc"]), d)
                d += 0.12

        if prof["allergies"].strip():
            hits = allergy_hits(prof["allergies"], verified)
            if hits:
                for term, brand in hits:
                    card("danger", f"🚨 Possible allergy match: {esc(term)}",
                         f"<b>{esc(brand)}</b> may be related to the allergy you listed. "
                         f"Ask a pharmacist before use.", d)
                    d += 0.12
            else:
                card("info", "Allergy keyword check",
                     f"No match for “{esc(prof['allergies'])}” among verified products. "
                     f"This is a simple keyword check, not a guarantee.", d)
                d += 0.12

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
            card("danger", f"⚠️ Possible duplicate ingredient: {esc(ing.title())}", body, d)
            d += 0.12

        for inter in interactions:
            card("danger", f"🛡️ {esc(inter['title'])}", esc(inter["desc"]), d)
            d += 0.12

        if not duplicates and not interactions and verified:
            card("ok", "✅ No duplicate or rule triggered among verified products",
                 "This is not a safety guarantee. RxLens only checks what is in its small database.", d)
            d += 0.12
        if unverified:
            card("warn", f"❓ Couldn't verify: {esc(', '.join(unverified))}",
                 "Not in our database, so these were NOT checked. Ask your pharmacist.", d)

        with st.expander("🔍 What we matched (and the source)"):
            for typed, e in verified:
                st.write(f"**{typed}** → {e['brand']}: {', '.join(e['ingredients'])} "
                         f"({e['strength']}) · class: {', '.join(e['drug_class'])} · Source: {e['source']}")

        lines = ["RxLens summary (not medical advice)",
                 f"For: {prof['who']}, {prof['age']} y", ""]
        for _, e in verified:
            lines.append(f"- {e['brand']}: {', '.join(e['ingredients'])} ({e['strength']})")
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
        st.download_button("📄 Download summary for your pharmacist", "\n".join(lines),
                           file_name="rxlens_summary.txt")

    stepper_slot.markdown(stepper_html(3 if show else 2), unsafe_allow_html=True)