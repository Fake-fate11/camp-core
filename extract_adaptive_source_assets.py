from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Adaptive_Risk-Aware_Motion_Prediction.pptx"
OUT = ROOT / "ppt_assets" / "adaptive_source_elements"
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def slide_number(name: str) -> int:
    return int(Path(name).stem.replace("slide", ""))


def extract() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(SRC, "r") as z:
        slides = sorted(
            [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=slide_number,
        )
        for slide_path in slides:
            idx = slide_number(slide_path)
            xml = etree.fromstring(z.read(slide_path))
            blips = xml.xpath(".//a:blip[@r:embed]", namespaces=NS)
            if not blips:
                continue
            rid = blips[0].get(f"{{{NS['r']}}}embed")
            rel_path = f"ppt/slides/_rels/slide{idx}.xml.rels"
            rel_xml = etree.fromstring(z.read(rel_path))
            rel = rel_xml.xpath(f".//rel:Relationship[@Id='{rid}']", namespaces=NS)[0]
            target = rel.get("Target")
            media_path = str(Path("ppt/slides").joinpath(target).resolve())
            # Path.resolve on Windows will treat this as absolute; normalize manually.
            media_path = "ppt/" + target.replace("../", "")
            suffix = Path(media_path).suffix.lower() or ".png"
            out_file = OUT / f"slide_{idx:02d}{suffix}"
            out_file.write_bytes(z.read(media_path))
            extracted.append(out_file)
    return extracted


def make_contact_sheet(images: list[Path]) -> None:
    thumbs = []
    for p in images:
        im = Image.open(p).convert("RGB")
        im.thumbnail((420, 236), Image.LANCZOS)
        canvas = Image.new("RGB", (420, 270), "white")
        canvas.paste(im, ((420 - im.width) // 2, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 244), p.stem, fill=(20, 30, 42))
        thumbs.append(canvas)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 420, rows * 270), "white")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * 420, (i // cols) * 270))
    sheet.save(OUT / "contact_sheet.png", quality=95)


def main() -> None:
    images = extract()
    make_contact_sheet(images)
    print(f"extracted={len(images)}")
    for p in images:
        print(p)
    print(OUT / "contact_sheet.png")


if __name__ == "__main__":
    main()
