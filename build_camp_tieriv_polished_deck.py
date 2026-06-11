from __future__ import annotations

import json
import math
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree
from PIL import Image


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "ppt_assets" / "camp_tieriv_polished"
ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
CMU_LOGO = ROOT / "ppt_assets" / "camp_drive_briefing" / "cmu_logo.png"
BLANK_MD = OUT_DIR / "_blank_16.md"
RAW_PPTX = ROOT / "CAMP_TiERIV_Polished_raw_base.pptx"
PPTX_OUT = ROOT / "CAMP_TiERIV_Polished_Editable_Briefing.pptx"
MANIFEST_OUT = OUT_DIR / "element_manifest.json"

EMU = 914400
SLIDE_W = 13.333
SLIDE_H = 7.5
W = int(round(SLIDE_W * EMU))
H = int(round(SLIDE_H * EMU))

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS, "rel": REL_NS}

NAVY = "092747"
CMU_BLUE = "0055A4"
CMU_RED = "C41230"
SKY = "5EA5D7"
TEAL = "008A8A"
GOLD = "FDB515"
INK = "1C2430"
GRAY = "5E6A71"
LIGHT = "F4F7FA"
MID = "D8E2EA"
GREEN = "2E8B57"
PURPLE = "6868AC"
ORANGE = "E5A100"


def qn(ns: str, tag: str) -> str:
    return f"{{{ {'p': P_NS, 'a': A_NS, 'r': R_NS}[ns] }}}{tag}"


def emu(inch: float) -> int:
    return int(round(inch * EMU))


def pt(value: float) -> str:
    return str(int(round(value * 100)))


def asset(name: str) -> Path:
    return ASSET_DIR / name


@dataclass
class PictureSpec:
    path: Path
    x: float
    y: float
    w: float
    h: float
    name: str
    fit: str = "contain"


@dataclass
class Element:
    xml: etree._Element
    kind: str
    name: str


@dataclass
class SlideSpec:
    title: str
    section: str
    elements: list[Element] = field(default_factory=list)
    pictures: list[PictureSpec] = field(default_factory=list)
    notes: str = ""


class IdGen:
    def __init__(self) -> None:
        self.value = 10

    def next(self) -> int:
        self.value += 1
        return self.value


def el(tag: str, **attrs: str) -> etree._Element:
    node = etree.Element(tag)
    for key, value in attrs.items():
        if value is not None:
            node.set(key, str(value))
    return node


def add_solid(parent: etree._Element, color: str) -> etree._Element:
    fill = etree.SubElement(parent, qn("a", "solidFill"))
    etree.SubElement(fill, qn("a", "srgbClr"), val=color)
    return fill


def shape_base(shape_id: int, name: str, is_text: bool = False) -> etree._Element:
    sp = etree.Element(qn("p", "sp"))
    nv = etree.SubElement(sp, qn("p", "nvSpPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name)
    c_nv_sp = etree.SubElement(nv, qn("p", "cNvSpPr"))
    if is_text:
        c_nv_sp.set("txBox", "1")
    etree.SubElement(nv, qn("p", "nvPr"))
    return sp


def add_xfrm(parent: etree._Element, x: float, y: float, w: float, h: float) -> None:
    xfrm = etree.SubElement(parent, qn("a", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(emu(x)), y=str(emu(y)))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(emu(w)), cy=str(emu(h)))


def rect(
    ids: IdGen,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = "FFFFFF",
    line: str | None = None,
    radius: str = "rect",
) -> Element:
    sp = shape_base(ids.next(), name)
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    add_xfrm(sp_pr, x, y, w, h)
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst=radius)
    etree.SubElement(geom, qn("a", "avLst"))
    add_solid(sp_pr, fill)
    ln = etree.SubElement(sp_pr, qn("a", "ln"), w="12700")
    if line:
        add_solid(ln, line)
    else:
        etree.SubElement(ln, qn("a", "noFill"))
    return Element(sp, "shape", name)


def line(ids: IdGen, name: str, x: float, y: float, w: float, h: float, color: str, width: int = 22000, arrow: bool = False) -> Element:
    sp = shape_base(ids.next(), name)
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    add_xfrm(sp_pr, x, y, w, h)
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="line")
    etree.SubElement(geom, qn("a", "avLst"))
    etree.SubElement(sp_pr, qn("a", "noFill"))
    ln = etree.SubElement(sp_pr, qn("a", "ln"), w=str(width))
    add_solid(ln, color)
    if arrow:
        etree.SubElement(ln, qn("a", "tailEnd"), type="triangle", w="med", len="med")
    return Element(sp, "shape", name)


def textbox(
    ids: IdGen,
    name: str,
    text: str | list[str],
    x: float,
    y: float,
    w: float,
    h: float,
    size: float = 18,
    color: str = INK,
    bold: bool = False,
    align: str = "l",
    valign: str = "top",
    bullet: bool = False,
    font: str = "Aptos",
) -> Element:
    sp = shape_base(ids.next(), name, is_text=True)
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    add_xfrm(sp_pr, x, y, w, h)
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    etree.SubElement(sp_pr, qn("a", "noFill"))
    ln = etree.SubElement(sp_pr, qn("a", "ln"))
    etree.SubElement(ln, qn("a", "noFill"))
    tx = etree.SubElement(sp, qn("p", "txBody"))
    anchor = {"top": "t", "mid": "ctr", "bottom": "b"}.get(valign, "t")
    etree.SubElement(tx, qn("a", "bodyPr"), wrap="square", anchor=anchor, lIns="0", rIns="0", tIns="0", bIns="0")
    etree.SubElement(tx, qn("a", "lstStyle"))
    paragraphs = text if isinstance(text, list) else text.split("\n")
    for para_text in paragraphs:
        p = etree.SubElement(tx, qn("a", "p"))
        p_pr = etree.SubElement(p, qn("a", "pPr"), algn=align)
        if bullet:
            etree.SubElement(p_pr, qn("a", "buChar"), char="•")
        else:
            etree.SubElement(p_pr, qn("a", "buNone"))
        r = etree.SubElement(p, qn("a", "r"))
        r_attrs = {"lang": "en-US", "sz": pt(size)}
        if bold:
            r_attrs["b"] = "1"
        r_pr = etree.SubElement(r, qn("a", "rPr"), **r_attrs)
        add_solid(r_pr, color)
        etree.SubElement(r_pr, qn("a", "latin"), typeface=font)
        etree.SubElement(r, qn("a", "t")).text = para_text
    return Element(sp, "text", name)


def label_box(ids: IdGen, name: str, text: str, x: float, y: float, w: float, h: float, fill: str, color: str = "FFFFFF") -> list[Element]:
    return [
        rect(ids, f"{name} fill", x, y, w, h, fill=fill, line=None, radius="roundRect"),
        textbox(ids, name, text, x + 0.12, y + 0.07, w - 0.24, h - 0.14, size=12, color=color, bold=True, align="c", valign="mid"),
    ]


def table(
    ids: IdGen,
    name: str,
    rows: list[list[str]],
    x: float,
    y: float,
    w: float,
    h: float,
    col_widths: list[float] | None = None,
    header_fill: str = NAVY,
    body_fill: str = "FFFFFF",
    font_size: float = 10.5,
) -> Element:
    gf = etree.Element(qn("p", "graphicFrame"))
    nv = etree.SubElement(gf, qn("p", "nvGraphicFramePr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(ids.next()), name=name)
    etree.SubElement(nv, qn("p", "cNvGraphicFramePr"))
    etree.SubElement(nv, qn("p", "nvPr"))
    xfrm = etree.SubElement(gf, qn("p", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(emu(x)), y=str(emu(y)))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(emu(w)), cy=str(emu(h)))
    graphic = etree.SubElement(gf, qn("a", "graphic"))
    gd = etree.SubElement(graphic, qn("a", "graphicData"), uri="http://schemas.openxmlformats.org/drawingml/2006/table")
    tbl = etree.SubElement(gd, qn("a", "tbl"))
    etree.SubElement(tbl, qn("a", "tblPr"), firstRow="1", bandRow="1")
    grid = etree.SubElement(tbl, qn("a", "tblGrid"))
    ncols = max(len(r) for r in rows)
    if not col_widths:
        col_widths = [w / ncols] * ncols
    total = sum(col_widths)
    col_emus = [str(int(emu(w) * cw / total)) for cw in col_widths]
    for col_w in col_emus:
        etree.SubElement(grid, qn("a", "gridCol"), w=col_w)
    row_h = int(emu(h) / len(rows))
    for r_idx, row in enumerate(rows):
        tr = etree.SubElement(tbl, qn("a", "tr"), h=str(row_h))
        for c_idx in range(ncols):
            text = row[c_idx] if c_idx < len(row) else ""
            tc = etree.SubElement(tr, qn("a", "tc"))
            tx = etree.SubElement(tc, qn("a", "txBody"))
            etree.SubElement(tx, qn("a", "bodyPr"), wrap="square", lIns="45720", rIns="45720", tIns="22860", bIns="22860")
            etree.SubElement(tx, qn("a", "lstStyle"))
            p = etree.SubElement(tx, qn("a", "p"))
            etree.SubElement(p, qn("a", "pPr"), algn="l")
            run = etree.SubElement(p, qn("a", "r"))
            attrs = {"lang": "en-US", "sz": pt(font_size if r_idx else font_size + 0.5)}
            if r_idx == 0:
                attrs["b"] = "1"
            r_pr = etree.SubElement(run, qn("a", "rPr"), **attrs)
            add_solid(r_pr, "FFFFFF" if r_idx == 0 else INK)
            etree.SubElement(r_pr, qn("a", "latin"), typeface="Aptos")
            etree.SubElement(run, qn("a", "t")).text = text
            tc_pr = etree.SubElement(tc, qn("a", "tcPr"))
            add_solid(tc_pr, header_fill if r_idx == 0 else (LIGHT if r_idx % 2 == 0 else body_fill))
            for border in ["lnL", "lnR", "lnT", "lnB"]:
                ln = etree.SubElement(tc_pr, qn("a", border), w="7620")
                add_solid(ln, MID)
    return Element(gf, "table", name)


def picture_xml(shape_id: int, name: str, rid: str, x: float, y: float, w: float, h: float) -> etree._Element:
    pic = etree.Element(qn("p", "pic"))
    nv = etree.SubElement(pic, qn("p", "nvPicPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name, descr=name)
    etree.SubElement(nv, qn("p", "cNvPicPr"))
    etree.SubElement(nv, qn("p", "nvPr"))
    blip_fill = etree.SubElement(pic, qn("p", "blipFill"))
    etree.SubElement(blip_fill, qn("a", "blip"), {qn("r", "embed"): rid})
    stretch = etree.SubElement(blip_fill, qn("a", "stretch"))
    etree.SubElement(stretch, qn("a", "fillRect"))
    sp_pr = etree.SubElement(pic, qn("p", "spPr"))
    add_xfrm(sp_pr, x, y, w, h)
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    return pic


def image_box(path: Path, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    with Image.open(path) as im:
        iw, ih = im.size
    ratio = min(w / iw, h / ih)
    out_w = iw * ratio
    out_h = ih * ratio
    return x + (w - out_w) / 2, y + (h - out_h) / 2, out_w, out_h


def add_chrome(ids: IdGen, spec: SlideSpec, page: int) -> None:
    spec.elements.insert(0, rect(ids, "background", 0, 0, SLIDE_W, SLIDE_H, fill="FFFFFF"))
    spec.elements.insert(1, rect(ids, "top navy band", 0, 0, SLIDE_W, 0.48, fill=NAVY))
    spec.elements.insert(2, rect(ids, "top blue rule", 0, 0.48, SLIDE_W, 0.035, fill=SKY))
    spec.elements.append(textbox(ids, "header label", "CAMP RESEARCH BRIEFING", 9.3, 0.14, 3.15, 0.17, size=7.5, color="FFFFFF", bold=True, align="r", valign="mid"))
    spec.elements.append(rect(ids, "footer rule", 0.45, 7.05, 12.45, 0.012, fill=MID))
    spec.elements.append(textbox(ids, "footer left", "Carnegie Mellon University Research Collaboration", 0.45, 7.14, 5.4, 0.18, size=7.5, color=GRAY))
    spec.elements.append(textbox(ids, "footer right", f"{page:02d}", 12.2, 7.14, 0.65, 0.18, size=7.5, color=GRAY, align="r"))


def title(ids: IdGen, spec: SlideSpec, title_text: str, subtitle: str | None = None) -> None:
    spec.elements.append(textbox(ids, "slide title", title_text, 0.72, 0.78, 7.6, 0.48, size=24, color=NAVY, bold=True))
    if subtitle:
        spec.elements.append(textbox(ids, "slide subtitle", subtitle, 0.75, 1.28, 6.7, 0.32, size=11.5, color=GRAY))
    spec.elements.append(rect(ids, "red title accent", 0.45, 0.82, 0.06, 0.55, fill=CMU_RED))


def create_specs() -> list[SlideSpec]:
    specs: list[SlideSpec] = []

    def new_slide(title_text: str, section: str, subtitle: str | None = None) -> tuple[SlideSpec, IdGen]:
        ids = IdGen()
        spec = SlideSpec(title=title_text, section=section)
        add_chrome(ids, spec, len(specs) + 1)
        title(ids, spec, title_text, subtitle)
        specs.append(spec)
        return spec, ids

    # 1
    ids = IdGen()
    s = SlideSpec("CAMP: A Conic Atom Meta-Policy Framework", "Problem & Motivation")
    add_chrome(ids, s, 1)
    s.elements.append(textbox(ids, "title", "CAMP: A Conic Atom\nMeta-Policy Framework", 0.8, 1.25, 7.4, 1.35, size=34, color=NAVY, bold=True))
    s.elements.append(textbox(ids, "subtitle", "Risk-aware trajectory selection for hard-constraint safety", 0.85, 2.75, 6.8, 0.32, size=15, color=GRAY))
    s.elements.append(textbox(ids, "presenter", "Shawn Lin | Carnegie Mellon University", 0.85, 3.34, 5.6, 0.26, size=12.5, color=INK))
    s.elements.append(textbox(ids, "objective", "Meeting objective: high-level CAMP design + TiERIV integration path", 0.85, 4.05, 5.9, 0.35, size=13, color=CMU_BLUE, bold=True))
    s.elements.extend(label_box(ids, "pill1", "Absolute safety floor", 0.85, 4.72, 2.05, 0.36, CMU_BLUE))
    s.elements.extend(label_box(ids, "pill2", "Zero retraining", 3.05, 4.72, 1.75, 0.36, TEAL))
    s.elements.extend(label_box(ids, "pill3", "Real-time efficiency", 4.95, 4.72, 2.15, 0.36, CMU_RED))
    s.elements.append(rect(ids, "right visual panel", 8.25, 1.1, 3.6, 4.9, fill=LIGHT, line=MID, radius="roundRect"))
    s.pictures.append(PictureSpec(CMU_LOGO, 8.78, 1.42, 2.55, 2.55, "CMU logo"))
    s.elements.append(textbox(ids, "visual caption", "Conic atoms convert heterogeneous safety signals into a common risk space.", 8.68, 4.5, 2.7, 0.72, size=13, color=NAVY, bold=True, align="c", valign="mid"))
    specs.append(s)

    # 2
    s, ids = new_slide("The Operational Context", "Problem & Motivation", "Trajectory selection is risk management under uncertainty.")
    s.elements.append(rect(ids, "image frame", 0.72, 1.58, 7.25, 4.55, fill="FFFFFF", line=MID))
    s.pictures.append(PictureSpec(ROOT / "compare_crash_vs_safe.png", 0.82, 1.68, 7.05, 4.35, "multi-agent top-down scene"))
    s.elements.extend(label_box(ids, "ego label", "Ego vehicle", 1.0, 5.55, 1.45, 0.34, CMU_BLUE))
    s.elements.extend(label_box(ids, "dynamic label", "Uncertain agents", 4.7, 1.82, 1.82, 0.34, CMU_RED))
    s.elements.extend(label_box(ids, "map label", "Map clearance", 5.85, 5.45, 1.82, 0.34, TEAL))
    s.elements.append(table(ids, "risk table", [
        ["Signal", "Decision pressure"],
        ["Ego state", "Pick one executable future"],
        ["Dynamic obstacles", "Behavior is interactive"],
        ["Map context", "Clearance is non-negotiable"],
        ["Candidate pool", "Safety depends on available options"],
    ], 8.35, 1.65, 3.75, 3.7, [1.2, 2.55], font_size=10))
    s.elements.append(textbox(ids, "takeaway", "Industry problem: safe trajectory selection must handle behavior uncertainty without stalling online planning.", 8.35, 5.65, 3.75, 0.5, size=13, color=NAVY, bold=True))

    # 3
    s, ids = new_slide("The Efficiency vs. Safety Conflict", "Problem & Motivation", "Hard constraints and real-time latency pull in opposite directions.")
    s.elements.append(line(ids, "seesaw beam", 2.0, 3.2, 8.2, -1.0, CMU_BLUE, width=36000))
    s.elements.append(rect(ids, "pivot", 5.75, 3.56, 1.0, 0.72, fill=NAVY, line=NAVY, radius="triangle"))
    s.elements.append(rect(ids, "safety pan", 1.05, 2.15, 3.1, 1.1, fill="EAF3FB", line=CMU_BLUE, radius="roundRect"))
    s.elements.append(textbox(ids, "safety text", "Safety\nHard constraints\nMap clearance", 1.22, 2.34, 2.75, 0.66, size=17, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(rect(ids, "efficiency pan", 8.85, 1.2, 3.05, 1.08, fill="FFF4DA", line=GOLD, radius="roundRect"))
    s.elements.append(textbox(ids, "efficiency text", "Efficiency\nReal-time latency\nSmooth progress", 9.02, 1.39, 2.72, 0.66, size=17, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(table(ids, "conflict table", [
        ["Failure mode", "Operational consequence"],
        ["Heavy online solve", "Timeout risk inside the control loop"],
        ["Worst-case conservatism", "Freezing behavior in dense scenes"],
        ["Pure prediction", "No deterministic hard-safety filter"],
    ], 1.15, 4.75, 10.85, 1.52, [2.55, 8.3], font_size=11))

    # 4
    s, ids = new_slide("Limitations of Current Solutions", "Problem & Motivation", "The ideal quadrant is fast, deterministic, and safety-aware.")
    s.elements.append(rect(ids, "matrix outer", 1.15, 1.58, 9.0, 4.55, fill="FFFFFF", line=MID))
    s.elements.append(line(ids, "matrix vertical", 5.65, 1.58, 0, 4.55, MID, width=16000))
    s.elements.append(line(ids, "matrix horizontal", 1.15, 3.85, 9.0, 0, MID, width=16000))
    s.elements.append(textbox(ids, "y label", "Safety determinism", 0.72, 2.54, 0.4, 1.45, size=10, color=GRAY, bold=True, align="c"))
    s.elements.append(textbox(ids, "x label", "Computation speed", 4.05, 6.25, 3.0, 0.22, size=10, color=GRAY, bold=True, align="c"))
    s.elements.append(textbox(ids, "slow", "Slow", 2.85, 6.02, 0.7, 0.2, size=9, color=GRAY, align="c"))
    s.elements.append(textbox(ids, "fast", "Fast", 7.75, 6.02, 0.7, 0.2, size=9, color=GRAY, align="c"))
    s.elements.append(rect(ids, "ideal quadrant", 5.88, 1.82, 3.95, 1.65, fill="E8F6F1", line=TEAL, radius="roundRect"))
    s.elements.append(textbox(ids, "ideal", "Ideal target\nFast + deterministic\nrisk-aware selection", 6.08, 2.12, 3.55, 0.8, size=16, color=TEAL, bold=True, align="c", valign="mid"))
    s.elements.append(rect(ids, "traditional", 1.5, 1.95, 3.5, 1.25, fill="EAF3FB", line=CMU_BLUE, radius="roundRect"))
    s.elements.append(textbox(ids, "traditional text", "Traditional solvers\nHigh safety\nSlow online updates", 1.7, 2.18, 3.1, 0.64, size=14, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(rect(ids, "dl", 6.0, 4.35, 3.5, 1.25, fill="FFF1F3", line=CMU_RED, radius="roundRect"))
    s.elements.append(textbox(ids, "dl text", "End-to-end DL / RL\nFast inference\nWeak guarantees", 6.2, 4.58, 3.1, 0.64, size=14, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(textbox(ids, "side insight", "CAMP fills the missing quadrant by moving robust optimization offline and keeping deployment one-shot.", 10.45, 2.35, 1.8, 1.45, size=14, color=NAVY, bold=True, align="c", valign="mid"))

    # 5
    s, ids = new_slide("Introducing the CAMP Concept", "CAMP Architecture", "A universal risk-filtering meta-policy above the planner.")
    y = 2.18
    boxes = [("Black-box\nPredictor / Planner", 0.85, CMU_BLUE), ("CAMP\nMeta-Policy Filter", 5.0, CMU_RED), ("Tracking\nController", 9.25, TEAL)]
    for text, x, color in boxes:
        s.elements.append(rect(ids, f"{text} box", x, y, 2.85, 1.35, fill="FFFFFF", line=color, radius="roundRect"))
        s.elements.append(textbox(ids, f"{text} text", text, x + 0.2, y + 0.27, 2.45, 0.7, size=17, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(line(ids, "arrow 1", 3.82, 2.84, 1.0, 0, GRAY, arrow=True))
    s.elements.append(line(ids, "arrow 2", 7.98, 2.84, 1.05, 0, GRAY, arrow=True))
    s.elements.append(table(ids, "concept contracts", [
        ["Interface", "What passes through CAMP"],
        ["Input", "Candidate trajectories + scene context + map constraints"],
        ["Meta-policy", "Conic atoms + scene-conditioned weights + hard mask"],
        ["Output", "Selected trajectory + safety diagnostics"],
    ], 1.2, 4.55, 10.55, 1.48, [2.0, 8.55], font_size=10.7))
    s.elements.append(textbox(ids, "concept takeaway", "CAMP decouples behavior generation from safety enforcement.", 2.1, 1.55, 8.8, 0.35, size=16, color=CMU_BLUE, bold=True, align="c"))

    # 6
    s, ids = new_slide("Key Innovation 1: One-Shot Inference", "CAMP Architecture", "No online Benders loop. No online CVXPY solve.")
    s.elements.append(rect(ids, "traditional lane", 0.95, 1.65, 11.4, 1.72, fill="F8F8F8", line=MID, radius="roundRect"))
    s.elements.append(textbox(ids, "traditional label", "Traditional online optimization", 1.25, 1.92, 2.35, 0.25, size=12, color=GRAY, bold=True))
    loop_xs = [4.0, 5.45, 6.9]
    for idx, x in enumerate(loop_xs):
        s.elements.append(rect(ids, f"loop {idx}", x, 1.93, 1.08, 0.54, fill="FFFFFF", line=GRAY, radius="roundRect"))
    s.elements.append(textbox(ids, "loop text", "Solve\nUpdate\nCheck", 4.08, 2.05, 4.0, 0.24, size=10, color=GRAY, bold=True))
    s.elements.append(textbox(ids, "red x", "X", 9.4, 1.78, 0.55, 0.55, size=30, color=CMU_RED, bold=True, align="c", valign="mid"))
    s.elements.append(rect(ids, "camp lane", 0.95, 4.05, 11.4, 1.72, fill="EAF3FB", line=CMU_BLUE, radius="roundRect"))
    s.elements.append(textbox(ids, "camp label", "CAMP deployment path", 1.25, 4.32, 2.0, 0.25, size=12, color=CMU_BLUE, bold=True))
    for text, x in [("Scene\nfeatures", 3.45), ("One-shot\nforward pass", 5.2), ("Hard-mask\nargmin", 7.2), ("Selected\ntrajectory", 9.2)]:
        s.elements.append(rect(ids, f"{text} step", x, 4.62, 1.35, 0.62, fill="FFFFFF", line=CMU_BLUE, radius="roundRect"))
        s.elements.append(textbox(ids, f"{text} label", text, x + 0.08, 4.73, 1.18, 0.28, size=10.5, color=NAVY, bold=True, align="c", valign="mid"))
    for x in [4.82, 6.82, 8.82]:
        s.elements.append(line(ids, f"camp arrow {x}", x, 4.93, 0.28, 0, CMU_BLUE, arrow=True))
    s.elements.append(textbox(ids, "low latency", "Low-latency, bounded control flow", 4.4, 5.5, 4.7, 0.26, size=14, color=CMU_RED, bold=True, align="c"))

    # 7
    s, ids = new_slide("Key Innovation 2: Zero-Retraining Plug-and-Play", "CAMP Architecture", "The base predictor stays frozen while CAMP filters risk.")
    s.elements.append(rect(ids, "model panel", 0.95, 1.65, 5.15, 4.6, fill=LIGHT, line=MID, radius="roundRect"))
    for row in range(3):
        for col in range(3):
            s.elements.append(rect(ids, f"node {row}-{col}", 1.45 + col * 1.35, 2.2 + row * 0.86, 0.28, 0.28, fill="FFFFFF", line=CMU_BLUE, radius="ellipse"))
    for row in range(2):
        for col in range(3):
            s.elements.append(line(ids, f"net line {row}-{col}", 1.72 + col * 1.35, 2.34 + row * 0.86, 1.08, 0.86, MID, width=12000))
            s.elements.append(line(ids, f"net line b {row}-{col}", 1.72 + col * 1.35, 2.34 + row * 0.86, 1.08, -0.02, MID, width=12000))
    s.elements.append(rect(ids, "lock body", 4.7, 1.95, 0.7, 0.58, fill=NAVY, line=NAVY, radius="roundRect"))
    s.elements.append(textbox(ids, "lock label", "LOCKED\nBASE MODEL", 4.25, 2.72, 1.6, 0.42, size=11, color=NAVY, bold=True, align="c"))
    s.elements.append(line(ids, "bypass", 5.95, 3.65, 1.35, 0, GRAY, arrow=True))
    s.elements.append(rect(ids, "camp unit", 7.45, 2.52, 2.2, 1.25, fill="FFF1F3", line=CMU_RED, radius="roundRect"))
    s.elements.append(textbox(ids, "camp unit text", "CAMP\nprocessing unit", 7.72, 2.82, 1.65, 0.48, size=17, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(line(ids, "out", 9.75, 3.14, 1.15, 0, GRAY, arrow=True))
    s.elements.append(rect(ids, "output", 10.95, 2.6, 1.25, 1.05, fill="E8F6F1", line=TEAL, radius="roundRect"))
    s.elements.append(textbox(ids, "output text", "Safe\nchoice", 11.12, 2.86, 0.92, 0.36, size=15, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(table(ids, "plug benefits", [
        ["Integration value", "Why TiERIV should care"],
        ["No retraining", "Avoids destabilizing existing predictor baselines"],
        ["Black-box input", "Accepts trajectory distributions from the current stack"],
        ["Maintainable safety", "Safety layer can evolve independently"],
    ], 6.55, 4.55, 5.65, 1.45, [1.65, 4.0], font_size=9.8))

    # 8
    s, ids = new_slide("Evaluation Methodology on nuScenes", "Evaluation & Results", "Static frames replace videos while preserving scene-level evidence.")
    s.elements.append(rect(ids, "contact frame", 0.75, 1.55, 7.1, 4.85, fill="FFFFFF", line=MID))
    s.pictures.append(PictureSpec(asset("qual_contact_sheet.png"), 0.86, 1.66, 6.88, 4.62, "nuScenes qualitative contact sheet"))
    s.elements.append(table(ids, "eval setup", [
        ["Protocol", "Current project setting"],
        ["Base predictor", "Trajectron++ epoch-20 checkpoint"],
        ["Candidate pool", "K=50 main run; K=12 ablation"],
        ["Atom bank", "9 normalized atoms: comfort, speed, lane, clearance"],
        ["Risk objective", "RU-CVaR tail risk, alpha = 0.90"],
        ["Baselines", "Pred Top1, Oracle, Static, Reranker, Finetune Safe"],
    ], 8.25, 1.75, 4.15, 3.45, [1.35, 2.8], font_size=9.5))
    s.elements.append(textbox(ids, "eval note", "Evaluation emphasizes hard-constraint behavior in real-world multi-agent scenes, not simplified toy cases.", 8.25, 5.55, 4.1, 0.55, size=13, color=NAVY, bold=True))

    # 9
    s, ids = new_slide("Achieving the Absolute Safety Floor", "Evaluation & Results", "CAMP matches the feasible candidate-pool floor instead of chasing average accuracy only.")
    s.elements.append(rect(ids, "bar frame", 0.7, 1.55, 7.15, 4.85, fill="FFFFFF", line=MID))
    s.pictures.append(PictureSpec(asset("violation_bar.png"), 0.88, 1.7, 6.78, 4.52, "hard-constraint violation comparison"))
    s.elements.append(rect(ids, "kpi floor", 8.25, 1.78, 3.75, 1.05, fill="EAF3FB", line=CMU_BLUE, radius="roundRect"))
    s.elements.append(textbox(ids, "kpi floor text", "60.2%\nCandidate-pool floor matched", 8.48, 1.98, 3.3, 0.58, size=20, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(table(ids, "safety reading", [
        ["Reading", "High-level meaning"],
        ["Conic atoms", "Comparable risk space for heterogeneous constraints"],
        ["Hard mask", "Infeasible candidates are excluded at selection time"],
        ["Safety floor", "Selection reaches the best available candidate set"],
    ], 8.25, 3.28, 3.85, 2.35, [1.1, 2.75], font_size=9.8))

    # 10
    s, ids = new_slide("Operational Trade-offs: Progress vs. Conservatism", "Evaluation & Results", "Safety filtering should not become freezing behavior.")
    s.elements.append(rect(ids, "scatter frame", 0.7, 1.55, 5.9, 4.55, fill="FFFFFF", line=MID))
    s.pictures.append(PictureSpec(asset("tradeoff_scatter.png"), 0.86, 1.72, 5.58, 4.18, "safety progress scatter"))
    frame_imgs = [asset("qual_camp_improves_top1.png"), asset("qual_curve.png"), asset("qual_straight.png")]
    labels = ["t=1 candidate set", "t=2 risk filter", "t=3 smooth exit"]
    for idx, img_path in enumerate(frame_imgs):
        x = 7.05 + idx * 1.75
        s.elements.append(rect(ids, f"frame box {idx}", x, 1.95, 1.55, 1.35, fill="FFFFFF", line=MID))
        s.pictures.append(PictureSpec(img_path, x + 0.06, 2.0, 1.43, 1.22, labels[idx]))
        s.elements.append(textbox(ids, f"frame label {idx}", labels[idx], x, 3.38, 1.55, 0.23, size=8.5, color=GRAY, bold=True, align="c"))
    s.elements.append(table(ids, "tradeoff interpretation", [
        ["Concern", "CAMP response"],
        ["Over-conservatism", "Reject high-risk candidates, not all motion"],
        ["Progress loss", "Select feasible low-risk trajectory from K candidates"],
        ["Long-tail risk", "Tail-risk objective focuses on difficult scenes"],
    ], 7.05, 4.15, 5.25, 1.55, [1.35, 3.9], font_size=9.5))

    # 11
    s, ids = new_slide("System-Level Deployment Architecture", "System Integration & Deployment Path", "CAMP sits between planning and control.")
    stack = [("Perception", "agents | map | scene state"), ("Prediction / Planning", "candidate trajectories"), ("CAMP intervention point", "atoms | mask | risk score"), ("Control", "selected trajectory"), ("Monitoring", "diagnostics | fallback")]
    x0 = 0.9
    for i, (head, body) in enumerate(stack):
        x = x0 + i * 2.35
        fill = "FFF1F3" if i == 2 else ("EAF3FB" if i < 2 else "E8F6F1")
        line_col = CMU_RED if i == 2 else (CMU_BLUE if i < 2 else TEAL)
        s.elements.append(rect(ids, f"stack {head}", x, 2.25, 1.85, 1.15, fill=fill, line=line_col, radius="roundRect"))
        s.elements.append(textbox(ids, f"stack text {head}", f"{head}\n{body}", x + 0.13, 2.47, 1.59, 0.55, size=11.5, color=NAVY, bold=True, align="c", valign="mid"))
        if i < len(stack) - 1:
            s.elements.append(line(ids, f"stack arrow {i}", x + 1.92, 2.83, 0.33, 0, GRAY, arrow=True))
    s.elements.append(table(ids, "deployment IO", [
        ["CAMP input", "CAMP output"],
        ["Candidate trajectories", "Selected trajectory"],
        ["Scene embedding", "Risk diagnostics"],
        ["Map / obstacle context", "Fallback status"],
    ], 2.2, 4.55, 8.9, 1.45, [4.45, 4.45], font_size=10.5))

    # 12
    s, ids = new_slide("Computational Efficiency & Latency", "System Integration & Deployment Path", "Deployment path is bounded because optimization is offline.")
    s.elements.append(table(ids, "latency table", [
        ["Online module", "Operation", "Latency posture"],
        ["Candidate generator", "Existing TiERIV stack", "No new CAMP cost"],
        ["Atom extraction", "Vectorized candidate features", "Profile on platform"],
        ["CAMP scoring", "Theta forward pass + weighted atom cost", "Millisecond-level target"],
        ["Hard mask + argmin", "Feasible candidate selection", "Deterministic bounded pass"],
        ["No online optimizer", "No CVXPY / Benders loop at runtime", "Removes convergence risk"],
    ], 0.9, 1.6, 11.6, 3.95, [2.35, 5.35, 3.9], font_size=10.2))
    s.elements.append(rect(ids, "offline callout", 1.15, 5.92, 4.9, 0.58, fill="FFF4DA", line=GOLD, radius="roundRect"))
    s.elements.append(textbox(ids, "offline text", "Heavy robust optimization moves offline.", 1.35, 6.09, 4.5, 0.22, size=13, color=NAVY, bold=True, align="c"))
    s.elements.append(rect(ids, "online callout", 7.1, 5.92, 4.9, 0.58, fill="E8F6F1", line=TEAL, radius="roundRect"))
    s.elements.append(textbox(ids, "online text", "Online selection remains one-shot.", 7.3, 6.09, 4.5, 0.22, size=13, color=NAVY, bold=True, align="c"))

    # 13
    s, ids = new_slide("Proposed Integration with TiERIV", "System Integration & Deployment Path", "Turn the research layer into a platform-ready risk filter.")
    cards = [
        ("1", "API interface", "Candidate format\nscene embedding\nmap / obstacle fields", CMU_BLUE),
        ("2", "Hardware profile", "planning cycle\nCPU/GPU budget\nmemory ceiling", TEAL),
        ("3", "Testing sandbox", "logged scenes\nsim runner\nmetric hooks", ORANGE),
        ("4", "Pilot metrics", "clearance\nprogress\nfallback rate", CMU_RED),
    ]
    for idx, (num, head, body, color) in enumerate(cards):
        x = 0.95 + idx * 3.02
        s.elements.append(rect(ids, f"card {num}", x, 1.75, 2.55, 3.55, fill="FFFFFF", line=color, radius="roundRect"))
        s.elements.append(rect(ids, f"card num {num}", x + 0.18, 1.95, 0.52, 0.52, fill=color, line=color, radius="ellipse"))
        s.elements.append(textbox(ids, f"card num text {num}", num, x + 0.18, 2.08, 0.52, 0.18, size=12, color="FFFFFF", bold=True, align="c"))
        s.elements.append(textbox(ids, f"card head {num}", head, x + 0.82, 2.02, 1.45, 0.25, size=13, color=NAVY, bold=True))
        s.elements.append(textbox(ids, f"card body {num}", body, x + 0.28, 2.85, 2.0, 1.05, size=12, color=GRAY, align="c", valign="mid"))
    s.elements.append(textbox(ids, "integration ask", "Discussion ask: where are TiERIV's tightest interface and hardware constraints?", 1.65, 5.95, 10.0, 0.28, size=14, color=CMU_RED, bold=True, align="c"))

    # 14
    s, ids = new_slide("Summary & Open Discussion", "Conclusion", "Three reasons CAMP is worth an integration conversation.")
    pillars = [("Absolute\nSafety Floor", CMU_BLUE), ("Zero\nRetraining", TEAL), ("Real-time\nEfficiency", CMU_RED)]
    for idx, (txt, color) in enumerate(pillars):
        x = 1.15 + idx * 3.8
        s.elements.append(rect(ids, f"pillar {idx}", x, 1.88, 3.05, 2.25, fill="FFFFFF", line=color, radius="roundRect"))
        s.elements.append(textbox(ids, f"pillar text {idx}", txt, x + 0.35, 2.35, 2.35, 0.86, size=24, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(textbox(ids, "qa", "Q&A", 4.55, 4.95, 4.1, 0.75, size=44, color=NAVY, bold=True, align="c", valign="mid"))
    s.elements.append(textbox(ids, "qa subtitle", "deployment details | platform interface | latency profiling | mathematical formulation", 2.05, 5.85, 9.05, 0.24, size=12, color=GRAY, align="c"))

    # 15
    s, ids = new_slide("Appendix: Master Problem Formulation", "Appendix", "Reserve slide for theoretical questions.")
    s.elements.append(rect(ids, "equation panel", 0.9, 1.55, 6.3, 4.55, fill=LIGHT, line=MID, radius="roundRect"))
    s.elements.append(textbox(ids, "eq title", "RU-CVaR master objective", 1.25, 1.9, 3.2, 0.28, size=15, color=NAVY, bold=True))
    s.elements.append(textbox(ids, "equation text", "min over Theta: eta + tail-risk slack + regularization\n\nsubject to:\n  w(x) >= 0\n  sum_j w_j(x) = 1\n  s_i >= active-risk_i - eta\n  hard-mask infeasible candidates", 1.25, 2.55, 5.55, 2.25, size=16, color=INK))
    s.elements.append(table(ids, "symbol table", [
        ["Symbol", "Role"],
        ["A(x, y_k)", "Conic atom vector for candidate trajectory k"],
        ["w(x)", "Scene-conditioned nonnegative atom weights"],
        ["m_k", "Hard feasibility mask"],
        ["alpha", "CVaR tail probability; current alpha = 0.90"],
    ], 7.65, 1.85, 4.45, 3.1, [1.3, 3.15], font_size=10.5))
    s.elements.append(textbox(ids, "formulation note", "The deployment artifact is not the optimizer. It is the fixed meta-policy produced by the offline master.", 7.75, 5.45, 4.2, 0.5, size=13, color=CMU_RED, bold=True, align="c"))

    # 16
    s, ids = new_slide("Appendix: Benders Decomposition Implementation", "Appendix", "Offline cut generation compresses robust optimization into a deployable policy.")
    steps = [("Warm start", "preference weights"), ("Inner search", "active risky candidates"), ("Cut generation", "risk surface"), ("Master update", "conic solve"), ("Export", "fixed Theta")]
    for idx, (head, body) in enumerate(steps):
        x = 0.9 + idx * 2.35
        s.elements.append(rect(ids, f"benders {idx}", x, 2.05, 1.7, 1.1, fill="FFFFFF", line=CMU_BLUE if idx < 4 else TEAL, radius="roundRect"))
        s.elements.append(textbox(ids, f"benders txt {idx}", f"{head}\n{body}", x + 0.12, 2.32, 1.46, 0.46, size=10.8, color=NAVY, bold=True, align="c", valign="mid"))
        if idx < 4:
            s.elements.append(line(ids, f"benders arrow {idx}", x + 1.78, 2.6, 0.45, 0, GRAY, arrow=True))
    s.elements.append(table(ids, "benders point", [
        ["Design choice", "Deployment implication"],
        ["Benders loop stays offline", "No convergence uncertainty inside control cycle"],
        ["Cuts focus on active high-risk scenes", "Training compute targets meaningful violations"],
        ["Theta checkpoint is compact", "Runtime selection is a deterministic scoring pass"],
    ], 1.15, 4.35, 10.75, 1.65, [2.8, 7.95], font_size=10.2))

    return specs


def generate_blank_pptx() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BLANK_MD.write_text("\n\n".join([f"# blank {i}" for i in range(1, 17)]), encoding="utf-8")
    subprocess.run(["pandoc", str(BLANK_MD), "--slide-level=1", "-o", str(RAW_PPTX)], cwd=ROOT, check=True)


def ensure_png_content_type(ct_root: etree._Element) -> None:
    has_png = any(el.tag.endswith("Default") and el.get("Extension") == "png" for el in ct_root)
    if not has_png:
        etree.SubElement(ct_root, "Default", Extension="png", ContentType="image/png")


def rel_id(existing: etree._Element) -> int:
    nums = []
    for rel in existing.xpath(".//rel:Relationship", namespaces=NS):
        rid = rel.get("Id", "")
        if rid.startswith("rId") and rid[3:].isdigit():
            nums.append(int(rid[3:]))
    return max(nums, default=1) + 1


def render_deck(specs: list[SlideSpec]) -> None:
    media_entries: dict[str, bytes] = {}
    updated_rels: dict[str, bytes] = {}
    manifest = {"source_template": "CMU blue academic style rebuilt as editable PPT elements", "slides": []}
    with zipfile.ZipFile(RAW_PPTX, "r") as zin:
        slide_names = sorted(
            [n for n in zin.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda n: int(Path(n).stem.replace("slide", "")),
        )
        content_types = etree.fromstring(zin.read("[Content_Types].xml"))
        ensure_png_content_type(content_types)
        with zipfile.ZipFile(PPTX_OUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                filename = info.filename
                if filename == "[Content_Types].xml":
                    continue
                if filename.startswith("ppt/slides/_rels/slide"):
                    continue
                data = zin.read(filename)
                if filename in slide_names:
                    idx = slide_names.index(filename)
                    spec = specs[idx]
                    slide_xml = etree.fromstring(data)
                    sp_tree = slide_xml.find(".//p:spTree", namespaces=NS)
                    if sp_tree is not None:
                        keep = list(sp_tree)[:2]
                        for child in list(sp_tree):
                            sp_tree.remove(child)
                        for child in keep:
                            sp_tree.append(child)
                        max_id = 500
                        def is_underlay(element: Element) -> bool:
                            if element.kind != "shape":
                                return False
                            name = element.name.lower()
                            return any(token in name for token in ["background", "band", "rule", "frame", "panel"])

                        underlay = [e for e in spec.elements if is_underlay(e)]
                        chrome_text_names = {"header label", "footer left", "footer right"}
                        overlay_main = [e for e in spec.elements if not is_underlay(e) and e.name not in chrome_text_names]
                        overlay_chrome = [e for e in spec.elements if not is_underlay(e) and e.name in chrome_text_names]
                        overlay = overlay_main + overlay_chrome
                        for element in underlay:
                            sp_tree.append(element.xml)
                        rel_path = f"ppt/slides/_rels/slide{idx + 1}.xml.rels"
                        rel_xml = etree.fromstring(zin.read(rel_path))
                        next_rid = rel_id(rel_xml)
                        for pic_idx, pic in enumerate(spec.pictures, start=1):
                            max_id += 1
                            rid = f"rId{next_rid}"
                            next_rid += 1
                            media_name = f"ppt/media/camp_polished_s{idx + 1:02d}_{pic_idx:02d}.png"
                            media_entries[media_name] = pic.path.read_bytes()
                            etree.SubElement(
                                rel_xml,
                                f"{{{REL_NS}}}Relationship",
                                Id=rid,
                                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                                Target=f"../media/{Path(media_name).name}",
                            )
                            px, py, pw, ph = image_box(pic.path, pic.x, pic.y, pic.w, pic.h)
                            sp_tree.append(picture_xml(max_id, pic.name, rid, px, py, pw, ph))
                        for element in overlay:
                            sp_tree.append(element.xml)
                        data = etree.tostring(slide_xml, xml_declaration=True, encoding="UTF-8", standalone=True)
                        rel_data = etree.tostring(rel_xml, xml_declaration=True, encoding="UTF-8", standalone=True)
                        updated_rels[rel_path] = rel_data
                    manifest["slides"].append(
                        {
                            "slide": idx + 1,
                            "title": spec.title,
                            "native_elements": [e.name for e in spec.elements if e.kind in {"text", "shape", "table"}],
                            "png_elements": [p.name for p in spec.pictures],
                        }
                    )
                zout.writestr(filename, data)
            zout.writestr("[Content_Types].xml", etree.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True))
            for rel_name, rel_data in updated_rels.items():
                zout.writestr(rel_name, rel_data)
            for media_name, media_data in media_entries.items():
                zout.writestr(media_name, media_data)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_blank_pptx()
    specs = create_specs()
    if len(specs) != 16:
        raise RuntimeError(f"Expected 16 slides, got {len(specs)}")
    render_deck(specs)
    print(PPTX_OUT)


if __name__ == "__main__":
    main()
