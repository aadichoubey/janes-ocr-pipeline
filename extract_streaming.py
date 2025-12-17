import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from pdf2image.pdf2image import pdfinfo_from_path


PDF_FILE = "janes10.pdf"
OUTPUT_DIR = "output"
PAGES_DIR = os.path.join(OUTPUT_DIR, "pages")

DPI = 150 

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

os.makedirs(PAGES_DIR, exist_ok=True)

html_path = os.path.join(OUTPUT_DIR, "output.html")


html = open(html_path, "w", encoding="utf-8")
html.write("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Jane's Fighting Ships – OCR Output</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
.page { margin-bottom: 50px; }
.page img { max-width: 900px; border: 1px solid #ccc; }
pre { background: #111; color: #f8f8f2; padding: 10px; white-space: pre-wrap; }
</style>
</head>
<body>
<h1>OCR Output (Streaming)</h1>
""")


info = pdfinfo_from_path(PDF_FILE)
total_pages = info["Pages"]

print(f"Total pages to process: {total_pages}")

for page_num in range(1, total_pages + 1):
    print(f"Processing page {page_num}/{total_pages}")

    page_image = convert_from_path(
        PDF_FILE,
        dpi=DPI,
        first_page=page_num,
        last_page=page_num
    )[0]

    image_name = f"page_{page_num:04}.png"
    image_path = os.path.join(PAGES_DIR, image_name)
    page_image.save(image_path, "PNG")

    text = pytesseract.image_to_string(
        page_image,
        config="--oem 3 --psm 6"
    )

    html.write(f"<div class='page'>\n")
    html.write(f"<h2>Page {page_num}</h2>\n")
    html.write(f"<img src='pages/{image_name}'><br>\n")
    html.write("<h3>OCR Text</h3>\n")
    html.write("<pre>\n")
    html.write(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    html.write("\n</pre>\n")
    html.write("</div>\n")

html.write("</body></html>")
html.close()

print(f"\nDone. Open {html_path} in your browser.")
