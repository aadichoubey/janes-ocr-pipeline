from bs4 import BeautifulSoup
import re
import json

# -------------------------
# CONFIG
# -------------------------
HTML_FILE = "Janes 2023-2024 (1).htm"
OUTPUT_FILE = "final_output.json"

# -------------------------
# LOAD HTML
# -------------------------
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

def normalize_band(text):
    t = text.lower()
    if "l-band" in t or "i-band" in t:
        return "I-band"
    if "e/f" in t:
        return "E/F-band"
    if "g-band" in t:
        return "G-band"
    return ""

def extract_inline_names(text):
    names = re.findall(
        r"[A-Z][A-Z0-9'’\-]+(?:\s[A-Z0-9'’\-]+)*",
        text
    )
    return [clean_ship_name(n) for n in names if len(n) > 2]

# -------------------------
# MAIN STREAM LOOP
# -------------------------
for elem in soup.find_all(["span", "p", "table", "img"]):

    # -------------------------
    # COUNTRY (font8)
    # -------------------------
    if elem.name == "span" and "font8" in (elem.get("class") or []):
        if current_entry:
            data.append(current_entry)
            current_entry = None

        current_country = elem.get_text(strip=True)
        current_class_of_ship = None
        last_was_font5 = False

    # -------------------------
    # PLATFORM TYPE (font6)
    # -------------------------
    elif elem.name == "span" and "font6" in (elem.get("class") or []):
        current_class_of_ship = elem.get_text(strip=True)
        last_was_font5 = False

    # -------------------------
    # PLATFORM CLASS (font5)
    # -------------------------
    elif elem.name == "span" and "font5" in (elem.get("class") or []):
        text = elem.get_text(strip=True)

        # merge consecutive font5 spans (e.g. "(PB)")
        if current_entry and last_was_font5:
            current_entry["PLATFORM_CLASS"] += f" {text}"
        else:
            if current_entry:
                data.append(current_entry)

            current_entry = {
                "COUNTRY_NAME": current_country,
                "CLASS_OF_SHIP": current_class_of_ship,
                "PLATFORM_CLASS": text,
                "PLATFORM NAMES": [],
                "RADARS": [],
                "IMG_PATH": []
            }

        last_was_font5 = True
        continue

    # -------------------------
    # TABLE PLATFORM NAMES
    # -------------------------
    elif elem.name == "table" and current_entry:
        for row in elem.find_all("tr")[1:]:
            cols = row.find_all("td")
            if cols:
                name = clean_ship_name(cols[0].get_text(strip=True))
                if name and name not in current_entry["PLATFORM NAMES"]:
                    current_entry["PLATFORM NAMES"].append(name)

        last_was_font5 = False

    # -------------------------
    # PARAGRAPHS (RADARS + INLINE NAMES)
    # -------------------------
    elif elem.name == "p" and current_entry:
        text = elem.get_text(" ", strip=True)
        bold = elem.find("b")

        # ---- RADARS (this is why they were empty before)
        if bold and "radars" in bold.get_text(strip=True).lower():
            radar_text = re.sub(r"^Radars:\s*", "", text, flags=re.I)
            parts = radar_text.split(".")
            for part in parts:
                if ":" in part:
                    rtype, rest = part.split(":", 1)
                    rname = rest.split(";")[0].strip()
                    band = normalize_band(rest)

                    current_entry["RADARS"].append({
                        "RADAR_TYPE": rtype.strip(),
                        "RADAR_NAME": rname,
                        "BAND_TYPE": band
                    })

        # ---- INLINE PLATFORM NAMES
        elif text.isupper() and len(text) < 200:
            for n in extract_inline_names(text):
                if n not in current_entry["PLATFORM NAMES"]:
                    current_entry["PLATFORM NAMES"].append(n)

        last_was_font5 = False

    # -------------------------
    # IMAGES
    # -------------------------
    elif elem.name == "img" and current_entry:
        src = elem.get("src")
        if src:
            current_entry["IMG_PATH"].append(src)

        last_was_font5 = False

# -------------------------
# FINALIZE
# -------------------------
if current_entry:
    data.append(current_entry)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Extraction complete.")
print("Total records:", len(data))
print(json.dumps(data[:2], indent=2, ensure_ascii=False))
