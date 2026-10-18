import csv
import json
import re
import time
from rapidfuzz import process, fuzz
from google.genai import types

MODEL = "gemini-3.8-flash"   # if you get a 404, run list_models.py and use a current flash model
MATCH_CUTOFF = 80

# Usual ADULT label maximums. Verify against your leaflets and cite them in the README.
LIMITS = {
    "paracetamol": {"single_mg": 1000, "daily_mg": 4000},
}

PROMPT = """You are reading a photo of medicine packaging.
Return ONLY JSON in this form: {"brand_name": "...", "strength": "..."}
Use an empty string for any field you cannot clearly read. Do not guess."""


def parse_doses(strength, n_ingredients):
    """'500 mg + 65 mg' -> [500.0, 65.0]. Returns None entries when the
    strength can't be matched safely to each ingredient."""
    parts = [p.strip() for p in strength.split("+")]
    if len(parts) != n_ingredients:
        return [None] * n_ingredients
    out = []
    for p in parts:
        m = re.fullmatch(r"([\d.]+)\s*mg", p, re.I)
        out.append(float(m.group(1)) if m else None)
    return out


def load_db(path="medicines.csv"):
    db = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ings = [i.strip().lower() for i in row["ingredients"].split(";")]
            db[row["brand"].strip().lower()] = {
                "brand": row["brand"].strip(),
                "ingredients": ings,
                "strength": row["strength"].strip(),
                "doses": parse_doses(row["strength"].strip(), len(ings)),
                "source": row["source"].strip(),
                "drug_class": [c.strip().lower() for c in row.get("drug_class", "").split(";") if c.strip()],
            }
    return db


def extract_name(client, image, model=MODEL):
    """AI PART: Gemini reads the package photo. Retries if Google is busy."""
    last_error = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[image, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            data = json.loads(response.text)
            if isinstance(data, list):
                data = data[0] if data else {}
            return data
        except Exception as e:
            last_error = e
            msg = str(e)
            if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_error


def match_brand(name, db, cutoff=MATCH_CUTOFF):
    if not name or not name.strip():
        return None
    result = process.extractOne(name.lower(), list(db.keys()),
                                scorer=fuzz.WRatio, score_cutoff=cutoff)
    return db[result[0]] if result else None


def find_interactions(verified):
    """RULE: two DIFFERENT NSAIDs together. Cite your reference in the README."""
    out, seen = [], {}
    for _, e in verified:
        if "nsaid" in e["drug_class"]:
            for ing in e["ingredients"]:
                seen.setdefault(ing, e["brand"])
    if len(seen) >= 2:
        pairs = " + ".join(f"{b} ({i})" for i, b in seen.items())
        out.append({
            "title": f"Two different NSAIDs together: {pairs}",
            "desc": "Combining NSAIDs can increase the risk of stomach irritation and bleeding. "
                    "Ask a pharmacist before using them together.",
        })
    return out


def check_duplicates(names, db):
    """RULE PART: no AI here. Returns verified, unverified, duplicates, interactions."""
    verified, unverified, seen_brands = [], [], set()
    for n in names:
        e = match_brand(n, db)
        if not e:
            unverified.append(n)
        elif e["brand"] not in seen_brands:
            seen_brands.add(e["brand"])
            verified.append((n, e))

    by_ing = {}
    for _, e in verified:
        for ing, dose in zip(e["ingredients"], e["doses"]):
            by_ing.setdefault(ing, []).append((e["brand"], dose))

    duplicates = {}
    for ing, items in by_ing.items():
        if len(items) > 1:
            doses = [d for _, d in items]
            known = all(d is not None for d in doses)
            lim = LIMITS.get(ing, {})
            duplicates[ing] = {
                "prods": [b for b, _ in items],
                "total_dose": sum(doses) if known else 0,
                "single_limit": lim.get("single_mg"),
                "daily_limit": lim.get("daily_mg"),
            }
    return verified, unverified, duplicates, find_interactions(verified)


def child_alerts(verified, age):
    """RULE: aspirin-containing products for under 16s. We never compute child doses."""
    out = []
    if age < 16:
        for _, e in verified:
            if "aspirin" in e["ingredients"]:
                out.append({
                    "title": f"{e['brand']} contains aspirin",
                    "desc": "Aspirin-containing medicines are generally not recommended for children "
                            "and teenagers. Ask a doctor or pharmacist first.",
                })
    return out