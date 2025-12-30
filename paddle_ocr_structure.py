import os
import subprocess
import json
import numpy as np
from paddleocr import PPStructure

# ---------------- CONFIG ---------------- #

PDF = "janes10.pdf"
IMG_DIR = "output/images"
STRUCT_DIR = "output/structure"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(STRUCT_DIR, exist_ok=True)

# ---------------- HELPERS ---------------- #

def make_json_safe(obj):
    """
    Recursively convert numpy types to Python native types
    so the output can be JSON-serialized.
    """
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

# ---------------- PDF → IMAGES ---------------- #

subprocess.run(
    ["pdftoppm", "-r", "300", PDF, f"{IMG_DIR}/page", "-png"],
    check=True
)

# ---------------- STRUCTURE OCR ---------------- #

engine = PPStructure(
    show_log=True,
    lang="en",
    use_gpu=False  # FORCE CPU (cuDNN not available)
)

# ---------------- RUN PER PAGE ---------------- #

for img in sorted(os.listdir(IMG_DIR)):
    if not img.endswith(".png"):
        continue

    img_path = os.path.join(IMG_DIR, img)
    print(f"Processing {img_path}")

    result = engine(img_path)

    safe_result = make_json_safe(result)

    out_path = os.path.join(
        STRUCT_DIR, img.replace(".png", ".json")
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(safe_result, f, indent=2)

print("STRUCTURE OCR DONE")

