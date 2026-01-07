from bs4 import BeautifulSoup
import json
import re

HTML_FILE = "Janes 2023-2024 (1).htm"
OUTPUT_FILE = "final_output.json"


# -------------------------
# HELPERS
# -------------------------

PENNANT_RE = re.compile(r"^[A-Z]?\s?\d+$")
CLASS_SUFFIX_RE = re.compile(r"^\([A-Z0-9]+\)$")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def is_upper_candidate(text):
    return text.isupper() and 3 < len(text) < 200


def clean_platform_name(name):
    name = clean(name)
    if PENNANT_RE.match(name):
        return None
    return name


def extract_table_names(table):
    names = []
    rows = table.find_all("tr")
    for r in rows[1:]:
        cols = r.find_all("td")
        if cols:
            n = clean_platform_name(cols[0].get_text())
            if n:
                names.append(n)
    return names


def extract_inline_names(text):
    names = []
    for part in re.split(r"\s{2,}", text):
        part = clean_platform_name(part)
        if part:
            names.append(part)
    return names


def extract_radars(text):
    radars = []
    text = re.sub(r"Radars?:", "", text, flags=re.I)

    for part in re.split(r"\.\s*", text):
        if ":" not in part:
            continue

        rtype, rest = part.split(":", 1)
        rtype = rtype.strip()

        band = ""
        low = rest.lower()
        if "l-band" in low or "i-band" in low:
            band = "I-band"
        elif "e/f" in low:
            band = "E/F-band"
        elif "g-band" in low:
            band = "G-band"

        name = rest.split(";")[0].strip()

        radars.append({
            "RADAR_TYPE": rtype,
            "RADAR_NAME": name,
            "BAND_TYPE": band
        })

    return radars


# -------------------------
# LOAD HTML
# -------------------------

with open(HTML_FILE, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")


# -------------------------
# STATE
# -------------------------

output = []

current_country = None
current_platform_type = None
current_entry = None


# -------------------------
# MAIN LOOP
# -------------------------

for el in soup.find_all(["span", "p", "table", "img"]):

    # -------- COUNTRY --------
    if el.name == "span" and "font8" in (el.get("class") or []):
        if current_entry:
            output.append(current_entry)
            current_entry = None

        current_country = clean(el.get_text())
        current_platform_type = None

    # -------- PLATFORM TYPE --------
    elif el.name == "span" and "font6" in (el.get("class") or []):
        current_platform_type = clean(el.get_text())

    # -------- PLATFORM CLASS --------
    elif el.name == "span" and "font5" in (el.get("class") or []):
        text = clean(el.get_text())

        # CLASS SUFFIX → MERGE
        if CLASS_SUFFIX_RE.match(text) and current_entry:
            current_entry["PLATFORM_CLASS"] += f" {text}"
            continue

        # NEW CLASS
        if current_entry:
            output.append(current_entry)

        current_entry = {
            "COUNTRY_NAME": current_country,
            "CLASS_OF_SHIP": current_platform_type,
            "PLATFORM_CLASS": text,
            "PLATFORM_NAMES": [],
            "RADARS": [],
            "IMG_PATH": []
        }

    # -------- TABLE NAMES --------
    elif el.name == "table" and current_entry:
        names = extract_table_names(el)
        if names:
            current_entry["PLATFORM_NAMES"].extend(names)

    # -------- PARAGRAPHS --------
    elif el.name == "p" and current_entry:
        text = clean(el.get_text())

        if re.search(r"\bradars?\b", text, re.I):
            current_entry["RADARS"].extend(extract_radars(text))

        elif is_upper_candidate(text):
            current_entry["PLATFORM_NAMES"].extend(
                extract_inline_names(text)
            )

    # -------- IMAGES --------
    elif el.name == "img" and current_entry:
        src = el.get("src")
        if src:
            current_entry["IMG_PATH"].append(src)


# -------------------------
# FINALIZE
# -------------------------

if current_entry:
    output.append(current_entry)

for o in output:
    o["PLATFORM_NAMES"] = list(dict.fromkeys(o["PLATFORM_NAMES"]))
    o["RADARS"] = o["RADARS"] or []

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("Extraction complete.")
print("Total records:", len(output))
print(json.dumps(output[:2], indent=2, ensure_ascii=False))
