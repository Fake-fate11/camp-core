from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "ppt_assets" / "camp_drive_briefing"
SOURCE_ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
MARKDOWN_OUT = ROOT / "CAMP_Conic_Atom_Meta_Policy_Briefing.md"
RAW_PPTX_OUT = ROOT / "_camp_conic_atom_meta_policy_raw.pptx"
PPTX_OUT = ROOT / "CAMP_Conic_Atom_Meta_Policy_Briefing.pptx"
REFERENCE_PPTX = ROOT / "CMU_Blue_Academic_Research_Briefing.pptx"


CMU_RED = "#C41230"
CMU_BLUE = "#0055A4"
DARK_BLUE = "#15395B"
GRAY = "#5E6A71"
EMU_PER_INCH = 914400
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def qn(namespace: str, tag: str) -> str:
    namespaces = {"p": P_NS, "a": A_NS}
    return f"{{{namespaces[namespace]}}}{tag}"


def emu(inches: float) -> int:
    return int(round(inches * EMU_PER_INCH))


def srgb(color: str) -> str:
    return color.strip().lstrip("#").upper()


def add_solid_fill(parent: etree._Element, color: str) -> None:
    fill = etree.SubElement(parent, qn("a", "solidFill"))
    etree.SubElement(fill, qn("a", "srgbClr"), val=srgb(color))


def add_no_line(parent: etree._Element) -> None:
    line = etree.SubElement(parent, qn("a", "ln"))
    etree.SubElement(line, qn("a", "noFill"))


def make_rect(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, color: str) -> etree._Element:
    sp = etree.Element(qn("p", "sp"))
    nv = etree.SubElement(sp, qn("p", "nvSpPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name)
    etree.SubElement(nv, qn("p", "cNvSpPr"))
    etree.SubElement(nv, qn("p", "nvPr"))
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(x), y=str(y))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(cx), cy=str(cy))
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    add_solid_fill(sp_pr, color)
    add_no_line(sp_pr)
    return sp


def make_textbox(
    shape_id: int,
    name: str,
    text: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    size_pt: float,
    color: str,
    bold: bool = False,
    align: str = "l",
) -> etree._Element:
    sp = etree.Element(qn("p", "sp"))
    nv = etree.SubElement(sp, qn("p", "nvSpPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name)
    etree.SubElement(nv, qn("p", "cNvSpPr"), txBox="1")
    etree.SubElement(nv, qn("p", "nvPr"))
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(x), y=str(y))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(cx), cy=str(cy))
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    etree.SubElement(sp_pr, qn("a", "noFill"))
    add_no_line(sp_pr)

    tx_body = etree.SubElement(sp, qn("p", "txBody"))
    etree.SubElement(tx_body, qn("a", "bodyPr"), wrap="none", anchor="ctr")
    etree.SubElement(tx_body, qn("a", "lstStyle"))
    para = etree.SubElement(tx_body, qn("a", "p"))
    etree.SubElement(para, qn("a", "pPr"), algn=align)
    run = etree.SubElement(para, qn("a", "r"))
    attrs = {"lang": "en-US", "sz": str(int(round(size_pt * 100)))}
    if bold:
        attrs["b"] = "1"
    r_pr = etree.SubElement(run, qn("a", "rPr"), **attrs)
    add_solid_fill(r_pr, color)
    etree.SubElement(r_pr, qn("a", "latin"), typeface="Aptos")
    etree.SubElement(run, qn("a", "t")).text = text
    return sp


def img(name: str) -> str:
    return str((SOURCE_ASSET_DIR / name).as_posix())


def write_template_manifest() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_template": str(REFERENCE_PPTX),
        "deck_title": "CAMP: A Conic Atom Meta-Policy Framework for Risk-Aware Trajectory Selection",
        "template_elements_rebuilt_as": [
            {"name": "CMU blue top rule", "type": "native rectangle shape"},
            {"name": "CMU red accent rule", "type": "native rectangle shape"},
            {"name": "academic footer", "type": "separate editable text boxes"},
            {"name": "slide titles", "type": "separate editable text boxes"},
            {"name": "body copy", "type": "editable bullet text boxes"},
            {"name": "SOTA and appendix matrices", "type": "native PowerPoint tables"},
            {"name": "repo evidence figures", "type": "individual PNG images"},
        ],
        "png_assets": [
            "computational_graph.png",
            "atom_bank.png",
            "evidence_chain.png",
            "tradeoff_scatter.png",
            "violation_bar.png",
            "qual_contact_sheet.png",
        ],
    }
    (ASSET_DIR / "template_element_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def write_markdown() -> None:
    md = f"""# CAMP: A Conic Atom Meta-Policy Framework for Risk-Aware Trajectory Selection

High-Level Design, Theoretical Innovations, and Deployment Path

Shawn Lin (Carnegie Mellon University)

::: notes
Opening page for an industry-facing research briefing. Keep the title concise and do not overload this slide.
:::

# Operational Context & Background

* **Trajectory selection:** Autonomous vehicles generate multiple candidate futures, score them against scene context, and commit to one executable trajectory.
* **Risk-awareness imperative:** Multi-agent interaction creates map, behavior, and prediction uncertainty that deterministic or worst-case planners handle poorly.
* **Industry demand:** Production stacks must move forward assertively while keeping hard safety constraints visible, auditable, and enforceable.

| Production tension | Why it matters |
| :--- | :--- |
| Aggressive progress | Avoids unnecessary freezing and protects route completion. |
| Conservative safety | Prevents map-clearance, collision, and comfort violations. |
| Millisecond loop budget | Keeps planning compatible with real vehicle compute. |

::: notes
Frame trajectory selection as the operational point where prediction, planning, and safety meet.
:::

# Problem Definition & The Safety-Efficiency Conflict

* **Core problem:** Select one candidate trajectory while respecting hard map clearance, collision, comfort, and feasibility constraints.
* **Real-time dilemma:** Online optimization can miss millisecond control-loop deadlines in dynamic, non-convex, multi-agent scenes.
* **Objective:** Drive hard-constraint violations to the candidate-pool safety floor without computational failure or conservative freezing.

| Constraint channel | Online risk | CAMP design response |
| :--- | :--- | :--- |
| Map clearance | Lane or drivable-area boundary intrusion | Atomized clearance costs and hard feasibility masks |
| Dynamic agents | Collision and interaction uncertainty | Candidate-wise risk scoring under uncertainty |
| Runtime budget | Solver convergence ambiguity | One-shot selection at deployment |

::: notes
The safety floor is bounded by the candidate pool: selection cannot choose a safe trajectory if no safe candidate exists.
:::

# State of the Art (SOTA) & Literature Review

| Category | Strengths | Weaknesses |
| :--- | :--- | :--- |
| Traditional mathematical optimization | Handles hard constraints formally; gives deterministic bounds under idealized assumptions. | High online latency; struggles with dynamic updates, non-convexity, and large candidate sets. |
| Learning-based methods: end-to-end DL / RL | Fast inference; strong pattern recognition for common driving behavior. | Limited deterministic safety guarantees; vulnerable in long-tail interactive scenes. |
| Design takeaway | The missing capability is not another predictor alone. | A fast safety layer must sit above heterogeneous predictors. |

::: notes
This slide establishes why neither pure optimization nor pure learning fully solves deployment-grade trajectory selection.
:::

# The Technical Gap & Motivation for a Meta-Policy

* **Missing link:** A universal defensive layer that bridges fast predictive models with rigorous safety guarantees.
* **Why retraining fails:** Edge-case retraining is expensive, destabilizes baseline behavior, and repeats for every new safety requirement.
* **Meta-policy concept:** Decouple behavior prediction from safety enforcement through an upper-level policy that filters candidate trajectories.

| Existing stack component | Kept intact | CAMP intervention |
| :--- | :--- | :--- |
| Predictor / planner | Black-box candidate generator | Supplies trajectory distribution |
| Safety logic | Explicit hard constraints | Encoded as conic atoms and masks |
| Tracking controller | Executes selected path | Receives a lower-risk trajectory |

::: notes
Stress that CAMP is an overlay rather than a replacement for the base autonomy stack.
:::

# Introduction to the CAMP Framework Architecture

**Framework:** Conic Atom Meta-Policy (CAMP)

| Pipeline stage | Role in CAMP |
| :--- | :--- |
| Candidate generation | Receive arbitrary trajectory candidates from a predictor or planner. |
| Atom mapping | Project candidates into a conic safety space with normalized risk atoms. |
| Risk filtering | Apply scene-conditioned weights and hard feasibility masks. |
| Trajectory handoff | Select the lowest-risk feasible candidate for downstream tracking. |

::: notes
This slide keeps the high-level architecture fully editable as a native table.
:::

# Key Innovation 1: One-Shot Inference Mechanism

* **Concept:** Replace iterative online optimization loops with direct candidate scoring and selection.
* **Computational efficiency:** Deployment uses a fixed meta-policy, a single forward pass, and an inner minimum over candidate costs.
* **Strategic value:** Removes uncertainty about whether a solver converges inside the control-loop cycle.

| Offline phase | Online phase |
| :--- | :--- |
| Fit conic meta-policy with RU-CVaR and Benders cuts. | Score candidates once using fixed parameters. |
| Absorb expensive robust optimization into training. | Select in real time with deterministic control flow. |

::: notes
This is the key deployment argument: robust training can be heavy, but inference stays lightweight.
:::

# Key Innovation 2: Modular Plug-and-Play Integration

* **Zero retraining architecture:** The base predictor/planner remains independent and can be treated as a black box.
* **Interoperability:** CAMP accepts arbitrary candidate trajectory distributions, supporting stacks such as Autoware-style modular pipelines.
* **Maintenance advantage:** Updates to base driving logic do not require rebuilding the safety layer unless the interface or atom bank changes.

| Integration surface | Required contract |
| :--- | :--- |
| Input | Candidate trajectories, scene embedding, map context, feasibility masks |
| CAMP module | Atom normalization, conic risk weights, hard-mask selection |
| Output | Selected trajectory plus risk diagnostics for monitoring |

::: notes
Position CAMP as a narrow, testable adapter between candidate generation and execution.
:::

# Strategic Impact & Theoretical Advantages

* **Mathematical risk hedging:** Adapts selection under uncertainty with robust abstractions rather than ad hoc penalties.
* **Safety floor achievement:** Minimizes hard-constraint violations down to the feasible-candidate floor.
* **Paradigm shift:** Safety assurance and real-time efficiency can coexist when heavy optimization is moved offline.

| Advantage | Why it is strategically useful |
| :--- | :--- |
| Conic atom representation | Turns heterogeneous safety signals into a common risk space. |
| RU-CVaR objective | Focuses training on high-tail risk rather than average-case comfort. |
| Meta-policy overlay | Lets teams improve safety without destabilizing the base model. |

::: notes
Use this slide to connect the mathematical contribution to deployment value.
:::

# Validation Framework & Collaborative Next Steps

* **Simulation benchmarking:** Current evaluations use nuScenes-style map-aware clearance and dynamic-neighbor risk checks.
* **System integration architecture:** CAMP maps naturally between trajectory generation and tracking-control execution.
* **Discussion for today:** Evaluate integration with TiERIV's proprietary platform and deployment pipeline.

| Next step | Collaboration question |
| :--- | :--- |
| Platform interface audit | Which trajectory, map, and scene-embedding signals are already exposed? |
| Hardware profiling | What latency ceiling and memory budget should the CAMP layer target? |
| Field-test metrics | Which infractions, disengagements, and comfort metrics define pilot success? |

::: notes
This is the transition from research result to joint deployment planning.
:::

# Appendix A: RU-CVaR-Based Master Problem

| Component | Role |
| :--- | :--- |
| Scene-conditioned weights | Map scene embedding to nonnegative atom weights. |
| Inner candidate response | Identify worst offending candidates under current weights. |
| RU-CVaR variables | Model tail risk through eta, slack, and sample penalties. |
| Hard masks | Preserve infeasible-candidate exclusion during selection. |
| Deployment output | Fixed meta-policy used by the one-shot inference layer. |

::: notes
Appendix slide for mathematical detail if the meeting turns technical.
:::

# Appendix B: Benders Decomposition Execution

| Step | Execution logic |
| :--- | :--- |
| 1. Warm start | Initialize policy weights from offline preference structure. |
| 2. Inner maximization | Find active high-risk candidates under current policy. |
| 3. Cut generation | Add cuts that expose the current risk violation surface. |
| 4. Master update | Re-solve the conic master with accumulated cuts. |
| 5. Export policy | Save fixed parameters for deployment-time scoring. |
| Deployment boundary | The expensive loop is offline; deployment receives only the compressed policy. |

::: notes
Keep this algorithmic; avoid implementation minutiae unless requested.
:::

# Appendix C: Quantitative Trade-Off Curves & Scene Demos

![Accuracy-safety trade-off]({img("tradeoff_scatter.png")}){{width=88%}}

::: notes
This slide preserves quantitative evidence as a separate repo PNG element. Use the qualitative case sheet and videos during live Q&A if requested.
:::
"""
    MARKDOWN_OUT.write_text(md, encoding="utf-8")


def style_slide_xml(xml_bytes: bytes, slide_index: int, slide_count: int, slide_w: int, slide_h: int) -> bytes:
    xml = etree.fromstring(xml_bytes)
    sp_tree = xml.find(".//p:spTree", namespaces={"p": P_NS})
    if sp_tree is None:
        return xml_bytes

    existing_ids = [
        int(el.get("id"))
        for el in xml.xpath(".//p:cNvPr[@id]", namespaces={"p": P_NS})
        if (el.get("id") or "").isdigit()
    ]
    next_id = max(existing_ids, default=1000) + 1

    bg_shapes = [
        make_rect(next_id, "CMU blue top rule", 0, 0, slide_w, emu(0.035), CMU_BLUE),
        make_rect(next_id + 1, "CMU red top accent", 0, emu(0.035), slide_w, emu(0.018), CMU_RED),
        make_rect(next_id + 2, "CMU bottom rule", 0, slide_h - emu(0.055), slide_w, emu(0.025), "#C8D0D8"),
    ]
    for offset, shape in enumerate(bg_shapes):
        sp_tree.insert(2 + offset, shape)

    footer_left = make_textbox(
        next_id + 3,
        "CMU footer left",
        "CAMP Conic Atom Meta-Policy research briefing",
        emu(0.35),
        slide_h - emu(0.32),
        emu(5.3),
        emu(0.18),
        7.5,
        GRAY,
    )
    footer_right = make_textbox(
        next_id + 4,
        "CMU footer right",
        f"June 2026 | {slide_index}/{slide_count}",
        slide_w - emu(3.0),
        slide_h - emu(0.32),
        emu(2.65),
        emu(0.18),
        7.5,
        GRAY,
        align="r",
    )
    sp_tree.append(footer_left)
    sp_tree.append(footer_right)

    if slide_index == 1:
        title_band = make_rect(
            next_id + 5,
            "CMU title accent block",
            0,
            slide_h - emu(1.25),
            emu(4.1),
            emu(1.25),
            DARK_BLUE,
        )
        red_block = make_rect(
            next_id + 6,
            "CMU title red accent",
            0,
            slide_h - emu(0.18),
            emu(4.1),
            emu(0.18),
            CMU_RED,
        )
        sp_tree.insert(2, title_band)
        sp_tree.insert(3, red_block)

    return etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)


def postprocess_pptx(raw_pptx: Path, final_pptx: Path) -> None:
    with zipfile.ZipFile(raw_pptx, "r") as zin:
        presentation_xml = etree.fromstring(zin.read("ppt/presentation.xml"))
        size_el = presentation_xml.find(".//p:sldSz", namespaces={"p": P_NS})
        slide_w = int(size_el.get("cx")) if size_el is not None else emu(13.333)
        slide_h = int(size_el.get("cy")) if size_el is not None else emu(7.5)
        slide_names = sorted(
            [name for name in zin.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
            key=lambda n: int(Path(n).stem.replace("slide", "")),
        )
        slide_count = len(slide_names)

        theme_bytes = None
        if REFERENCE_PPTX.exists():
            with zipfile.ZipFile(REFERENCE_PPTX, "r") as ref_zip:
                if "ppt/theme/theme1.xml" in ref_zip.namelist():
                    theme_bytes = ref_zip.read("ppt/theme/theme1.xml")

        with zipfile.ZipFile(final_pptx, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in slide_names:
                    slide_index = slide_names.index(info.filename) + 1
                    data = style_slide_xml(data, slide_index, slide_count, slide_w, slide_h)
                elif info.filename == "ppt/theme/theme1.xml" and theme_bytes is not None:
                    data = theme_bytes
                zout.writestr(info.filename, data)


def run_pandoc() -> None:
    cmd = [
        "pandoc",
        str(MARKDOWN_OUT),
        "--slide-level=1",
        "-o",
        str(RAW_PPTX_OUT),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    postprocess_pptx(RAW_PPTX_OUT, PPTX_OUT)


def main() -> None:
    write_template_manifest()
    write_markdown()
    run_pandoc()
    print(PPTX_OUT)


if __name__ == "__main__":
    main()
