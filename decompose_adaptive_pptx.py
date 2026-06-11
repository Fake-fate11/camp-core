from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from PIL import Image


ROOT = Path(__file__).resolve().parent
SRC_PPTX = ROOT / "Adaptive_Risk-Aware_Motion_Prediction.pptx"
OUT_PPTX = ROOT / "Adaptive_Risk-Aware_Motion_Prediction_decomposed.pptx"
OUT_DIR = ROOT / "ppt_assets" / "adaptive_decomposed_elements"

SLIDE_W_PX = 1376
SLIDE_H_PX = 768

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
IMAGE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


@dataclass(frozen=True)
class ElementBox:
    name: str
    x: int
    y: int
    w: int
    h: int

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.w, self.y + self.h


SLIDE_ELEMENTS: dict[int, list[ElementBox]] = {
    1: [
        ElementBox("cmu_brand", 57, 57, 462, 48),
        ElementBox("review_label", 58, 166, 1260, 73),
        ElementBox("main_title", 58, 241, 1260, 222),
        ElementBox("subtitle", 58, 464, 1260, 166),
        ElementBox("collaboration_footer", 58, 632, 1260, 73),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    2: [
        ElementBox("title_banner", 0, 0, 1376, 124),
        ElementBox("kpi_violation_floor", 20, 148, 335, 412),
        ElementBox("kpi_training_time", 363, 148, 327, 412),
        ElementBox("kpi_scenarios", 696, 148, 322, 412),
        ElementBox("kpi_candidate_pool", 1028, 148, 328, 412),
        ElementBox("central_finding", 20, 588, 1356, 180),
    ],
    3: [
        ElementBox("slide_title", 49, 84, 1106, 54),
        ElementBox("workflow_architecture_diagram", 27, 192, 1323, 544),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    4: [
        ElementBox("slide_title", 51, 77, 1239, 57),
        ElementBox("camp_select_column", 40, 169, 455, 564),
        ElementBox("finetune_safe_column", 485, 169, 450, 564),
        ElementBox("hybrid_column", 925, 169, 430, 564),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    5: [
        ElementBox("slide_title", 49, 65, 1265, 91),
        ElementBox("quantitative_results_table", 40, 195, 1296, 379),
        ElementBox("core_insight_box", 53, 587, 1272, 142),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    6: [
        ElementBox("slide_title", 34, 22, 735, 91),
        ElementBox("safety_frequency_chart", 23, 128, 951, 623),
        ElementBox("right_explanation_panel", 974, 0, 402, 768),
    ],
    7: [
        ElementBox("slide_title", 84, 25, 1206, 50),
        ElementBox("feasibility_donut_panel", 40, 100, 685, 636),
        ElementBox("bottleneck_analysis_panel", 725, 113, 618, 623),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    8: [
        ElementBox("structured_dossier_label", 46, 37, 261, 32),
        ElementBox("slide_title", 45, 76, 1227, 58),
        ElementBox("candidate_pool_table", 39, 135, 1298, 268),
        ElementBox("quality_shift_box", 33, 465, 651, 270),
        ElementBox("safety_scaling_box", 692, 493, 651, 242),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    9: [
        ElementBox("slide_title", 42, 27, 803, 108),
        ElementBox("curve_case_figure", 0, 145, 942, 617),
        ElementBox("scenario_analysis_panel", 941, 145, 425, 585),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    10: [
        ElementBox("slide_title", 67, 31, 1243, 51),
        ElementBox("base_failure_figure", 63, 109, 544, 656),
        ElementBox("scenario_analysis_panel", 675, 120, 649, 605),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    11: [
        ElementBox("slide_title", 48, 44, 1230, 54),
        ElementBox("no_feasible_floor_figure", 28, 152, 877, 577),
        ElementBox("scenario_analysis_panel", 910, 141, 443, 596),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    12: [
        ElementBox("title_band", 0, 0, 1376, 128),
        ElementBox("training_time_table_band", 0, 128, 1376, 222),
        ElementBox("operational_summary_heading_band", 0, 350, 1376, 80),
        ElementBox("high_efficiency_card_band", 0, 430, 480, 300),
        ElementBox("compute_savings_card_band", 480, 430, 432, 300),
        ElementBox("scalability_profile_card_band", 912, 430, 464, 300),
        ElementBox("footer_band", 0, 730, 1376, 38),
    ],
    13: [
        ElementBox("slide_title", 48, 52, 1261, 56),
        ElementBox("metric_audit_chart", 16, 147, 686, 593),
        ElementBox("methodological_correction_panel", 717, 154, 636, 552),
        ElementBox("notebook_logo", 1258, 744, 118, 18),
    ],
    14: [
        ElementBox("slide_title", 25, 20, 1312, 56),
        ElementBox("insight_1_box", 23, 103, 1331, 214),
        ElementBox("insight_2_box", 23, 324, 1331, 214),
        ElementBox("insight_3_box", 21, 543, 1355, 225),
    ],
    15: [
        ElementBox("slide_title", 46, 63, 1233, 58),
        ElementBox("stage_01_technical_alignment", 44, 171, 344, 510),
        ElementBox("stage_02_pilot_integration", 374, 171, 334, 510),
        ElementBox("stage_03_risk_review", 694, 171, 334, 510),
        ElementBox("stage_04_scale_decision_gate", 1014, 171, 344, 510),
        ElementBox("deliverable_footer", 45, 698, 1331, 64),
    ],
}


def slide_number(path: str) -> int:
    return int(Path(path).stem.replace("slide", ""))


def read_source_slide_images() -> dict[int, Image.Image]:
    slides: dict[int, Image.Image] = {}
    with zipfile.ZipFile(SRC_PPTX, "r") as z:
        slide_paths = sorted(
            [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=slide_number,
        )
        for slide_path in slide_paths:
            idx = slide_number(slide_path)
            xml = etree.fromstring(z.read(slide_path))
            blip = xml.xpath(".//a:blip[@r:embed]", namespaces=NS)[0]
            rid = blip.get(f"{{{NS['r']}}}embed")

            rel_path = f"ppt/slides/_rels/slide{idx}.xml.rels"
            rel_xml = etree.fromstring(z.read(rel_path))
            rel = rel_xml.xpath(f".//rel:Relationship[@Id='{rid}']", namespaces=NS)[0]
            media_path = "ppt/" + rel.get("Target").replace("../", "")

            tmp = OUT_DIR / "source_slides" / f"slide_{idx:02d}.png"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(z.read(media_path))
            slides[idx] = Image.open(tmp).convert("RGB")
    return slides


def crop_elements(slides: dict[int, Image.Image]) -> dict[int, list[dict[str, object]]]:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Re-read after cleanup so the source slide cache exists in OUT_DIR too.
    slides = read_source_slide_images()
    manifest: dict[int, list[dict[str, object]]] = {}

    for idx, im in slides.items():
        slide_dir = OUT_DIR / f"slide_{idx:02d}"
        slide_dir.mkdir(parents=True, exist_ok=True)
        manifest[idx] = []

        for seq, element in enumerate(SLIDE_ELEMENTS[idx], start=1):
            crop = im.crop(element.box)
            out_name = f"slide_{idx:02d}_{seq:02d}_{element.name}.png"
            out_path = slide_dir / out_name
            crop.save(out_path, optimize=True)
            manifest[idx].append(
                {
                    "seq": seq,
                    "name": element.name,
                    "type": "PNG picture element",
                    "pixel_box": {
                        "x": element.x,
                        "y": element.y,
                        "w": element.w,
                        "h": element.h,
                    },
                    "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
    return manifest


def rel_id_for(seq: int) -> str:
    # rId1 is the slide layout relationship in the source deck.
    return f"rId{seq + 1}"


def find_original_picture_frame(z: zipfile.ZipFile) -> tuple[int, int, int, int]:
    xml = etree.fromstring(z.read("ppt/slides/slide1.xml"))
    xfrm = xml.xpath(".//p:pic/p:spPr/a:xfrm", namespaces=NS)[0]
    off = xfrm.find("a:off", namespaces=NS)
    ext = xfrm.find("a:ext", namespaces=NS)
    return (
        int(off.get("x")),
        int(off.get("y")),
        int(ext.get("cx")),
        int(ext.get("cy")),
    )


def emu_rect(element: ElementBox, image_frame: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    frame_x, frame_y, frame_cx, frame_cy = image_frame
    x = frame_x + round(element.x * frame_cx / SLIDE_W_PX)
    y = frame_y + round(element.y * frame_cy / SLIDE_H_PX)
    cx = round(element.w * frame_cx / SLIDE_W_PX)
    cy = round(element.h * frame_cy / SLIDE_H_PX)
    return x, y, cx, cy


def make_picture_xml(seq: int, element: ElementBox, image_frame: tuple[int, int, int, int]) -> etree._Element:
    rid = rel_id_for(seq)
    shape_id = seq + 1
    x, y, cx, cy = emu_rect(element, image_frame)

    pic = etree.Element(f"{{{NS['p']}}}pic", nsmap={"p": NS["p"], "a": NS["a"], "r": NS["r"]})
    nv_pic_pr = etree.SubElement(pic, f"{{{NS['p']}}}nvPicPr")
    c_nv_pr = etree.SubElement(nv_pic_pr, f"{{{NS['p']}}}cNvPr")
    c_nv_pr.set("id", str(shape_id))
    c_nv_pr.set("name", element.name)
    c_nv_pic_pr = etree.SubElement(nv_pic_pr, f"{{{NS['p']}}}cNvPicPr")
    pic_locks = etree.SubElement(c_nv_pic_pr, f"{{{NS['a']}}}picLocks")
    pic_locks.set("noChangeAspect", "true")
    etree.SubElement(nv_pic_pr, f"{{{NS['p']}}}nvPr")

    blip_fill = etree.SubElement(pic, f"{{{NS['p']}}}blipFill")
    blip = etree.SubElement(blip_fill, f"{{{NS['a']}}}blip")
    blip.set(f"{{{NS['r']}}}embed", rid)
    stretch = etree.SubElement(blip_fill, f"{{{NS['a']}}}stretch")
    etree.SubElement(stretch, f"{{{NS['a']}}}fillRect")

    sp_pr = etree.SubElement(pic, f"{{{NS['p']}}}spPr")
    xfrm = etree.SubElement(sp_pr, f"{{{NS['a']}}}xfrm")
    off = etree.SubElement(xfrm, f"{{{NS['a']}}}off")
    off.set("x", str(x))
    off.set("y", str(y))
    ext = etree.SubElement(xfrm, f"{{{NS['a']}}}ext")
    ext.set("cx", str(cx))
    ext.set("cy", str(cy))
    geom = etree.SubElement(sp_pr, f"{{{NS['a']}}}prstGeom")
    geom.set("prst", "rect")
    etree.SubElement(geom, f"{{{NS['a']}}}avLst")
    return pic


def build_slide_xml(source_xml: bytes, elements: list[ElementBox], image_frame: tuple[int, int, int, int]) -> bytes:
    root = etree.fromstring(source_xml)
    sp_tree = root.find(".//p:spTree", namespaces=NS)

    for child in list(sp_tree)[2:]:
        sp_tree.remove(child)

    for seq, element in enumerate(elements, start=1):
        sp_tree.append(make_picture_xml(seq, element, image_frame))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def build_rels_xml(idx: int, elements: list[ElementBox]) -> bytes:
    relationships = etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
    layout_rel = etree.SubElement(relationships, f"{{{REL_NS}}}Relationship")
    layout_rel.set("Id", "rId1")
    layout_rel.set("Target", "../slideLayouts/slideLayout7.xml")
    layout_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout")

    for seq, element in enumerate(elements, start=1):
        rel = etree.SubElement(relationships, f"{{{REL_NS}}}Relationship")
        rel.set("Id", rel_id_for(seq))
        rel.set("Target", f"../media/adaptive_decomposed_s{idx:02d}_{seq:02d}_{element.name}.png")
        rel.set("Type", IMAGE_REL_TYPE)

    return etree.tostring(relationships, xml_declaration=True, encoding="UTF-8", standalone=True)


def build_pptx(manifest: dict[int, list[dict[str, object]]]) -> None:
    with zipfile.ZipFile(SRC_PPTX, "r") as zin:
        image_frame = find_original_picture_frame(zin)

        with zipfile.ZipFile(OUT_PPTX, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename

                if name.startswith("ppt/media/"):
                    continue

                if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                    idx = slide_number(name)
                    data = build_slide_xml(zin.read(name), SLIDE_ELEMENTS[idx], image_frame)
                    zout.writestr(item, data)
                    continue

                if name.startswith("ppt/slides/_rels/slide") and name.endswith(".xml.rels"):
                    idx = slide_number(name.replace(".xml.rels", ".xml"))
                    data = build_rels_xml(idx, SLIDE_ELEMENTS[idx])
                    zout.writestr(item, data)
                    continue

                zout.writestr(item, zin.read(name))

            for idx, slide_items in manifest.items():
                for item in slide_items:
                    seq = int(item["seq"])
                    name = str(item["name"])
                    source_file = ROOT / str(item["file"])
                    arcname = f"ppt/media/adaptive_decomposed_s{idx:02d}_{seq:02d}_{name}.png"
                    zout.write(source_file, arcname)


def write_manifest(manifest: dict[int, list[dict[str, object]]]) -> None:
    doc = {
        "source_pptx": SRC_PPTX.name,
        "output_pptx": OUT_PPTX.name,
        "source_observation": (
            "The source deck has 15 slides. Each slide contains a single full-slide PNG picture "
            "and no editable text, table, chart, or shape objects."
        ),
        "decomposition_method": (
            "Each original slide PNG was split into presentation-ready PNG elements by logical "
            "regions, then reinserted at the original pixel-mapped coordinates so the visual "
            "format stays unchanged."
        ),
        "slides": {str(k): v for k, v in manifest.items()},
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


def verify_package() -> None:
    with zipfile.ZipFile(OUT_PPTX, "r") as z:
        for idx, elements in SLIDE_ELEMENTS.items():
            slide_xml = z.read(f"ppt/slides/slide{idx}.xml").decode("utf-8", errors="ignore")
            pic_count = slide_xml.count("<p:pic")
            if pic_count != len(elements):
                raise RuntimeError(f"slide {idx} has {pic_count} pictures, expected {len(elements)}")


def main() -> None:
    slides = read_source_slide_images()
    manifest = crop_elements(slides)
    build_pptx(manifest)
    write_manifest(manifest)
    verify_package()
    print(OUT_PPTX)
    print(OUT_DIR / "manifest.json")


if __name__ == "__main__":
    main()
