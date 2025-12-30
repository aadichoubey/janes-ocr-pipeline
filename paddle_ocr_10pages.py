import os
import subprocess
from paddleocr import PaddleOCR

PDF = "janes10.pdf"
IMG_DIR = "output/images"
TXT_DIR = "output/text"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(TXT_DIR, exist_ok=True)

# Convert PDF → images
subprocess.run(
    ["pdftoppm", "-r", "200", PDF, f"{IMG_DIR}/page", "-png"],
    check=True
)

# Initialize OCR
ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en",
    use_gpu=False
)

# OCR each page
for img in sorted(os.listdir(IMG_DIR)):
    if not img.endswith(".png"):
        continue

    img_path = os.path.join(IMG_DIR, img)
    result = ocr.ocr(img_path, cls=True)

    lines = []
    if result and result[0]:
        for r in result[0]:
            lines.append(r[1][0])

    with open(f"{TXT_DIR}/{img}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

print("DONE")
