"""Extract 投资交易心理分析.pdf into book.txt with page markers."""
import sys
from pypdf import PdfReader

PDF_PATH = r"D:\AI量化\仓颉skill\投资交易心理分析.pdf"
OUT_PATH = r"D:\AI量化\仓颉skill\books\trading-psychology\book.txt"

reader = PdfReader(PDF_PATH)
print(f"Total pages: {len(reader.pages)}")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        f.write(f"\n===== PAGE {i} =====\n\n")
        f.write(text)
        if i % 50 == 0:
            print(f"  ... page {i} done", flush=True)

print("DONE")
