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

# -------------------------
# HELPERS
# -------------------------
def clean_ship_name(name):
    name = re.sub(r"\(.*?\)", "", name)        # remove (ex-...)
    name = re.sub(r"\b[PYA]\s?\d+\b", "", name) # remove pennant numbers
    return name.strip()

def normalize_band(text):
    text = text.lower()
    if "l-band" in text or "i-band" in text:
        return "I-band"
    if "e/f" in text:
        return "E/F-band"
    if "g-band" in text:
        return "G-band"
    return ""

# -------------------------
# MAIN LOOP (ORDER MATTERS)
# -------------------------
for elem in soup.find_all(["h1", "h2", "h3", "p", "table", "img"]):

    # ---- COUNTRY ----
    if elem.name == "h1":
        span = elem.find("span", class_="font8")
        if span:
            # close previous entry
            if current_entry:
                data.append(current_entry)
                current_entry = None

            current_country = span.get_text(strip=True)
            current_class_of_ship = None

    # ---- CLASS OF SHIP (PATROL FORCES etc.) ----
    elif elem.name in ["h2", "p"]:
        text = elem.get_text(strip=True)
        if text.isupper() and 5 < len(text) < 40:
            current_class_of_ship = text

    # ---- PLATFORM CLASS ----
    elif elem.name == "h3":
        # close previous platform class
        if current_entry:
            data.append(current_entry)

        current_entry = {
            "COUNTRY_NAME": current_country,
            "CLASS_OF_SHIP": current_class_of_ship,
            "PLATFORM_CLASS": elem.get_text(" ", strip=True),
            "PLATFORM NAMES": [],
            "RADARS": [],
            "IMG_PATH": []
        }

    # ---- TABLE: PLATFORM NAMES ----
    elif elem.name == "table" and current_entry:
        rows = elem.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if cols:
                name = clean_ship_name(cols[0].get_text(strip=True))
                if name:
                    current_entry["PLATFORM NAMES"].append(name)

    # ---- INLINE PLATFORM NAMES ----
    elif elem.name == "p" and current_entry:
        text = elem.get_text(" ", strip=True)

        # RADARS
        if text.lower().startswith("radars"):
            radar_parts = text.split(".")
            for part in radar_parts:
                if ":" in part:
                    rtype, rest = part.split(":", 1)
                    rname = rest.split(";")[0].strip()
                    band = normalize_band(rest)

                    current_entry["RADARS"].append({
                        "RADAR_TYPE": rtype.replace("Radars", "").strip(),
                        "RADAR_NAME": rname,
                        "BAND_TYPE": band
                    })

        # PLATFORM NAMES INLINE
        elif re.search(r"\b[A-Z]{3,}\b", text) and len(text) < 200:
            names = re.findall(r"[A-Z][A-Z0-9'’\-]+(?:\s[A-Z0-9'’\-]+)*", text)
            for n in names:
                clean = clean_ship_name(n)
                if clean and clean not in current_entry["PLATFORM NAMES"]:
                    current_entry["PLATFORM NAMES"].append(clean)

    # ---- IMAGES ----
    elif elem.name == "img" and current_entry:
        src = elem.get("src")
        if src:
            current_entry["IMG_PATH"].append(src)

# -------------------------
# FINALIZE LAST ENTRY
# -------------------------
if current_entry:
    data.append(current_entry)

# -------------------------
# WRITE OUTPUT
# -------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Extraction complete.")
print("Total records:", len(data))
print(json.dumps(data[:2], indent=2, ensure_ascii=False))
