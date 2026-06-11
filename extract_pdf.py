import os
from pypdf import PdfReader

def extract_text(pdf_path, out_path):
    print(f"Extracting {pdf_path} to {out_path}...")
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Done")

if __name__ == "__main__":
    extract_text("experiment_design.pdf", "experiment_design.txt")
    extract_text("Formulation.pdf", "Formulation.txt")
