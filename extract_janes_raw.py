from bs4 import BeautifulSoup
import json
import re

# -------------------------
# CONFIG
# -------------------------
HTML_FILE = "Janes 2023-2024 (1).htm"
OUTPUT_FILE = "raw_extracted.json"

# -------------------------
# LOAD HTML
# -------------------------
with open(HTML_FILE, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")

data = []

current_country = None
current_class_of_ship = None
current_entry = None
last_font5 = False


# -------------------------
# HELPERS
# -------------------------
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def flush_entry():
    global current_entry
    if current_entry:
        data.append(current_entry)
        current_entry = None


def extract_table(table):
    rows = []
    for tr in table.find_all("tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    return rows


# -------------------------
# MAIN STREAM (ORDERED)
# -------------------------
for elem in soup.find_all(["span", "p", "table", "img"]):

    # -------- COUNTRY (font8) --------
    if elem.name == "span" and "font8" in (elem.get("class") or []):
        flush_entry()
        current_country = clean_text(elem.get_text())
        current_class_of_ship = None
        last_font5 = False
        continue

    # -------- CLASS OF SHIP (font6) --------
    if elem.name == "span" and "font6" in (elem.get("class") or []):
        current_class_of_ship = clean_text(elem.get_text())
        last_font5 = False
        continue

    # -------- PLATFORM CLASS (font5) --------
    if elem.name == "span" and "font5" in (elem.get("class") or []):
        text = clean_text(elem.get_text())

        # Merge consecutive font5 spans (e.g. "(PB)")
        if current_entry and last_font5:
            current_entry["PLATFORM_CLASS"] += " " + text
        else:
            flush_entry()
            current_entry = {
                "COUNTRY_NAME": current_country,
                "CLASS_OF_SHIP": current_class_of_ship,
                "PLATFORM_CLASS": text,
                "RAW_TEXT": [],
                "IMG_PATH": []
            }

        last_font5 = True
        continue

    # -------- TABLE --------
    if elem.name == "table" and current_entry:
        table_data = extract_table(elem)
        if table_data:
            current_entry["RAW_TEXT"].append({
                "TABLE": table_data
            })
        last_font5 = False
        continue

    # -------- PARAGRAPH --------
    if elem.name == "p" and current_entry:
        text = clean_text(elem.get_text(" "))
        if text:
            current_entry["RAW_TEXT"].append(text)
        last_font5 = False
        continue

    # -------- IMAGE --------
    if elem.name == "img" and current_entry:
        src = elem.get("src")
        if src:
            current_entry["IMG_PATH"].append(src)
        last_font5 = False
        continue


# -------------------------
# FINALIZE
# -------------------------
flush_entry()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Raw extraction complete.")
print("Total platform blocks:", len(data))
print(json.dumps(data[:2], indent=2, ensure_ascii=False))
