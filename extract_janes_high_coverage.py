from bs4 import BeautifulSoup
import re
import json

HTML_FILE = "Janes 2023-2024 (1).htm"
OUTPUT_FILE = "final_output.json"

with open(HTML_FILE, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")

data = []

current_country = None
current_platform_type = None
current_entry = None
last_font5 = False


def clean(txt):
    return re.sub(r"\s+", " ", txt).strip()


def clean_name(name):
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\b[PYA]\s?\d+\b", "", name)
    return name.strip()


def extract_uppercase_names(text):
    candidates = re.findall(r"[A-Z][A-Z0-9'’\-]{2,}(?:\s+[A-Z0-9'’\-]{2,})*", text)
    names = []
    for c in candidates:
        c = clean_name(c)
        if len(c) >= 3 and not c.endswith("CLASS"):
            names.append(c)
    return names


def extract_radars(text):
    radars = []
    parts = re.split(r"\.\s*", text)
    for p in parts:
        if not re.search(r"radar|search|navigation", p, re.I):
            continue
        band = ""
        low = p.lower()
        if "l-band" in low or "i-band" in low:
            band = "I-band"
        elif "e/f" in low:
            band = "E/F-band"

        name = p.split(":")[-1].split(";")[0].strip()
        radars.append({
            "RADAR_TYPE": "Radar",
            "RADAR_NAME": name,
            "BAND_TYPE": band
        })
    return radars


def extract_table_names(table):
    names = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if cols:
            name = clean_name(cols[0].get_text(strip=True))
            if name:
                names.append(name)
    return names


for el in soup.find_all(["span", "p", "table", "img"]):

    # COUNTRY
    if el.name == "span" and "font8" in (el.get("class") or []):
        if current_entry:
            data.append(current_entry)
            current_entry = None
        current_country = clean(el.get_text())
        current_platform_type = None

    # PLATFORM TYPE
    elif el.name == "span" and "font6" in (el.get("class") or []):
        current_platform_type = clean(el.get_text())

    # PLATFORM CLASS
    elif el.name == "span" and "font5" in (el.get("class") or []):
        text = clean(el.get_text())

        if current_entry and last_font5 and text.startswith("("):
            current_entry["PLATFORM_CLASS"] += f" {text}"
        else:
            if current_entry:
                data.append(current_entry)
            current_entry = {
                "COUNTRY_NAME": current_country,
                "CLASS_OF_SHIP": current_platform_type,
                "PLATFORM_CLASS": text,
                "PLATFORM_NAMES": [],
                "RADARS": [],
                "IMG_PATH": []
            }
        last_font5 = True
        continue

    last_font5 = False

    # TABLE NAMES
    if el.name == "table" and current_entry:
        names = extract_table_names(el)
        current_entry["PLATFORM_NAMES"].extend(names)

    # PARAGRAPHS (AGGRESSIVE)
    elif el.name == "p" and current_entry:
        text = clean(el.get_text())

        # PLATFORM NAMES (uppercase blocks)
        if text.isupper() and len(text) < 300:
            current_entry["PLATFORM_NAMES"].extend(extract_uppercase_names(text))

        # RADARS (loose detection)
        if re.search(r"radar|search|navigation", text, re.I):
            current_entry["RADARS"].extend(extract_radars(text))

    # IMAGES
    elif el.name == "img" and current_entry:
        src = el.get("src")
        if src:
            current_entry["IMG_PATH"].append(src)


if current_entry:
    data.append(current_entry)

# FINAL CLEANUP
for d in data:
    d["PLATFORM_NAMES"] = sorted(set(n for n in d["PLATFORM_NAMES"] if n))
    d["RADARS"] = d["RADARS"] or []

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Extraction complete.")
print("Total records:", len(data))
print(json.dumps(data[:3], indent=2, ensure_ascii=False))
