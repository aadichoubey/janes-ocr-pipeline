import json
import re

INPUT_FILE = "raw_extracted.json"
OUTPUT_FILE = "final_output.json"

# -------------------------
# FILTERS & CONSTANTS
# -------------------------

BAD_PLATFORM_CLASSES = {
    "PENNANT LIST",
    "DELETIONS",
    "NOTES",
    "COMMENTS",
    "PROGRAMMES",
    "PROGRAMS",
    "MODERNISATION",
    "MODERNIZATION",
    "STRUCTURE",
    "OPERATIONAL",
    "AUXILIARIES",
    "COAST DEFENCE",
    "COAST DEFENSE",
}

BAD_NAME_TOKENS = {
    "CLASS", "CRAFT", "BOATS", "BOAT",
    "PATROL", "INSHORE", "RESPONSE",
    "PBF", "PBR", "PB", "WPB",
    "NAVY", "COAST", "GUARD",
    "SURVEY", "AIRCRAFT",
    "HELICOPTER", "SQUADRON",
    "WING", "FLIGHT"
}

RADAR_GARBAGE = {"L-", "K-", "F-", "G-", "X-", "BAND"}

KNOWN_RADAR_VENDORS = {
    "RAYTHEON", "THALES", "SAAB", "INDRA",
    "SELEX", "LEONARDO", "LOCKHEED",
    "NORTHROP", "ELTA", "FURUNO",
    "JRC", "HENSOLDT"
}

# -------------------------
# HELPERS
# -------------------------

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def clean_name(name):
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\b[PYA]\s?\d+\b", "", name)
    return clean_text(name)


def looks_like_ship_name(name):
    if not name or len(name) < 3:
        return False
    if any(tok in name.upper() for tok in BAD_NAME_TOKENS):
        return False
    if not re.match(r"^[A-Z0-9'’\- ]+$", name):
        return False
    if not re.search(r"[A-Z]", name):
        return False
    return True


def split_inline_names(text):
    """
    Safe splitting of merged ship names without regex lookbehind.
    Strategy:
    1) Split on 2+ spaces
    2) Further split on single space before ALL-CAPS words
    """
    names = []

    chunks = re.split(r"\s{2,}", text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        sub_chunks = re.split(r"\s(?=[A-Z]{3,}\b)", chunk)
        for sc in sub_chunks:
            n = clean_name(sc)
            if looks_like_ship_name(n):
                names.append(n)

    return names


def normalize_band(text):
    t = text.lower()
    if "l-band" in t or "i-band" in t:
        return "I-band"
    if "e/f" in t:
        return "E/F-band"
    if "g-band" in t:
        return "G-band"
    return ""


def valid_radar_name(name):
    if not name or len(name) < 3:
        return False
    if any(g in name.upper() for g in RADAR_GARBAGE):
        return False
    # must have a digit OR known vendor
    if not re.search(r"\d", name):
        if not any(v in name.upper() for v in KNOWN_RADAR_VENDORS):
            return False
    return True

# -------------------------
# EXTRACTION LOGIC
# -------------------------

def extract_platform_names(raw_text):
    names = set()

    # 1️⃣ TABLES FIRST (AUTHORITATIVE)
    for item in raw_text:
        if isinstance(item, dict) and "TABLE" in item:
            rows = item["TABLE"]
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                if not row:
                    continue
                name = clean_name(row[0])
                if looks_like_ship_name(name):
                    names.add(name)

    # 2️⃣ INLINE FALLBACK (ONLY IF TABLE FAILED)
    if not names:
        for item in raw_text:
            if not isinstance(item, str):
                continue
            if not item.isupper():
                continue
            for n in split_inline_names(item):
                names.add(n)

    return sorted(names)


def extract_radars(raw_text):
    radars = []

    for item in raw_text:
        if not isinstance(item, str):
            continue
        if not item.lower().startswith("radars"):
            continue

        text = re.sub(r"Radars?:", "", item, flags=re.I)
        sentences = re.split(r"\.\s*", text)

        for sentence in sentences:
            if ":" not in sentence:
                continue

            rtype, rest = sentence.split(":", 1)
            rtype = clean_text(rtype)
            band = normalize_band(rest)

            candidates = re.findall(
                r"[A-Z][A-Z0-9\-]+(?:\s[A-Z0-9\-]+)*",
                rest
            )

            for c in candidates:
                name = clean_text(c)
                if valid_radar_name(name):
                    radars.append({
                        "RADAR_TYPE": rtype,
                        "RADAR_NAME": name,
                        "BAND_TYPE": band
                    })

    return radars

# -------------------------
# MAIN NORMALIZATION
# -------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

final_data = []

for entry in raw_data:
    platform_class = clean_text(entry["PLATFORM_CLASS"])

    if platform_class.upper() in BAD_PLATFORM_CLASSES:
        continue

    final_data.append({
        "COUNTRY_NAME": entry["COUNTRY_NAME"],
        "CLASS_OF_SHIP": entry["CLASS_OF_SHIP"],
        "PLATFORM_CLASS": platform_class,
        "PLATFORM NAMES": extract_platform_names(entry["RAW_TEXT"]),
        "RADARS": extract_radars(entry["RAW_TEXT"]),
        "IMG_PATH": entry["IMG_PATH"][0] if entry["IMG_PATH"] else None
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print("Normalization complete.")
print("Total records:", len(final_data))
print(json.dumps(final_data[:2], indent=2, ensure_ascii=False))
