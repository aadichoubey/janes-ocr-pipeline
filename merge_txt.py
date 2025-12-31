from pathlib import Path

text_dir = Path("output/text")
out_file = Path("output/janes10_full.txt")

with out_file.open("w", encoding="utf-8") as fout:
    for txt in sorted(text_dir.glob("*.txt")):
        fout.write(f"\n\n===== {txt.name} =====\n\n")
        fout.write(txt.read_text(encoding="utf-8"))

print("Merged output written to", out_file)
