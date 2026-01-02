from bs4 import BeautifulSoup
import re
import json

HTML_FILE = "Janes 2023-2024 (1).htm"
OUTPUT_FILE = "final_output.json"

with open(HTML_FILE, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")

data = []

current_country = None
current_class_of_ship = None
current_entry = None
last_was_font5 = False


# -------------------------
# HELPERS
# -------------------------
def clean_ship_name(name):
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\b[PYA]\s?\d+\b", "", name)
    return name.strip()


def normalize_platform_class(text):
    # drop role-only suffixes like "(PB)"
    return re.sub(r"\s*\((PB|PBR|PBX|PBF)\)\s*$", "", text).strip()


def normalize_band(text):
    t = text.lower()
    band_match = re.search(r"([a-z]/[a-z]|[a-z])-band", t)
    if band_match:
        return band_match.group(0).upper()
    if "i-band" in t or "l-band" in t:
        return "I-band"
    return ""


def extract_inline_names(text):
    raw = re.findall(r"[A-Z][A-Z0-9'’\-]+(?:\s[A-Z0-9'’\-]+)*", text)
    cleaned = []
    for r in raw:
        n = clean_ship_name(r)
        if n and not n.endswith("CLASS"):
            cleaned.append(n)
    return cleaned


def extract_radars(text):
    radars = []

    # remove leading keywords if present
    text = re.sub(r"Radars?:", "", text, flags=re.I)

    # split on sentences
    parts = re.split(r"\.\s*", text)

    for part in parts:
        if ":" in part:
            rtype, rest = part.split(":", 1)
            band = normalize_band(rest)

            # radar names can be numbered or empty
            names = re.split(r"\d+\s+", rest)
            if not names:
                radars.append({
                    "RADAR_TYPE": rtype.strip(),
                    "RADAR_NAME": "",
                    "BAND_TYPE": band
                })
            else:
                for n in names:
                    name = n.split(";")[0].strip()
                    radars.append({
                        "RADAR_TYPE": rtype.strip(),
                        "RADAR_NAME": name,
                        "BAND_TYPE": band
                    })
    return radars


# -------------------------
# MAIN STREAM LOOP
# -------------------------
for elem in soup.find_all(["span", "p", "table", "img"]):

    # -------- COUNTRY --------
    if elem.name == "span" and "font8" in (elem.get("class") or []):
        if current_entry:
            data.append(current_entry)
            current_entry = None
        current_country = elem.get_text(strip=True)
        current_class_of_ship = None
        last_was_font5 = False

    # -------- CLASS OF SHIP --------
    elif elem.name == "span" and "font6" in (elem.get("class") or []):
        current_class_of_ship = elem.get_text(strip=True)
        last_was_font5 = False

    # -------- PLATFORM CLASS --------
    elif elem.name == "span" and "font5" in (elem.get("class") or []):
        text = elem.get_text(strip=True)

        if current_entry and last_was_font5:
            current_entry["PLATFORM_CLASS"] += f" {text}"
        else:
            if current_entry:
                data.append(current_entry)
            current_entry = {
                "COUNTRY_NAME": current_country,
                "CLASS_OF_SHIP": current_class_of_ship,
                "PLATFORM_CLASS": normalize_platform_class(text),
                "PLATFORM NAMES": [],
                "RADARS": [],
                "IMG_PATH": None
            }

        last_was_font5 = True
        continue

    # -------- TABLE PLATFORM NAMES --------
    elif elem.name == "table" and current_entry:
        for row in elem.find_all("tr")[1:]:
            cols = row.find_all("td")
            if cols:
                name = clean_ship_name(cols[0].get_text(strip=True))
                if name:
                    current_entry["PLATFORM NAMES"].append(name)
        last_was_font5 = False

    # -------- PARAGRAPHS --------
    elif elem.name == "p" and current_entry:
        text = elem.get_text(" ", strip=True)

        # RADARS (heuristic, not keyword-only)
        if any(k in text.lower() for k in ["radar", "search", "navigation"]):
            current_entry["RADARS"].extend(extract_radars(text))

        # INLINE PLATFORM NAMES
        elif text.isupper() and len(text) < 200:
            current_entry["PLATFORM NAMES"].extend(
                extract_inline_names(text)
            )

        last_was_font5 = False

    # -------- IMAGES --------
    elif elem.name == "img" and current_entry:
        src = elem.get("src")
        if src:
            if current_entry["IMG_PATH"] is None:
                current_entry["IMG_PATH"] = src
            else:
                if isinstance(current_entry["IMG_PATH"], str):
                    current_entry["IMG_PATH"] = [current_entry["IMG_PATH"]]
                current_entry["IMG_PATH"].append(src)
        last_was_font5 = False


# -------------------------
# FINALIZE & CLEANUP
# -------------------------
if current_entry:
    data.append(current_entry)

for d in data:
    d["PLATFORM NAMES"] = sorted(set(n for n in d["PLATFORM NAMES"] if n))
    if not d["RADARS"]:
        d["RADARS"] = []

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Extraction complete.")
print("Total records:", len(data))
print(json.dumps(data[:2], indent=2, ensure_ascii=False))
