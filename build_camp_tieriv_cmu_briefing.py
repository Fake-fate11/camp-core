from __future__ import annotations

import copy
import subprocess
import zipfile
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
DRIVE_ASSET_DIR = ROOT / "ppt_assets" / "camp_drive_briefing"
MARKDOWN_OUT = ROOT / "CAMP_TiERIV_CMU_Blue_Briefing.md"
RAW_PPTX_OUT = ROOT / "CAMP_TiERIV_CMU_Blue_Briefing_raw_clean.pptx"
PPTX_OUT = ROOT / "CAMP_TiERIV_CMU_Blue_Briefing.pptx"
TEMPLATE_PPTX = ROOT / "CMU_Blue_Academic_Research_Briefing.pptx"
CMU_LOGO = DRIVE_ASSET_DIR / "cmu_logo.png"


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS, "rel": REL_NS}


def asset(name: str) -> str:
    return str((ASSET_DIR / name).as_posix())


def write_markdown() -> None:
    md = f"""# CAMP: A Conic Atom Meta-Policy Framework

Risk-Aware Trajectory Selection for Hard-Constraint Safety

Shawn Lin (Carnegie Mellon University)

![Carnegie Mellon University]({CMU_LOGO.as_posix()}){{width=16%}}

Meeting objective: demonstrate the high-level CAMP design and discuss integration with TiERIV.

::: notes
Open by saying that this meeting is not a low-level engineering review. The goal is to show how CAMP addresses hard-constraint safety and where it would connect to TiERIV's stack.
:::

# The Operational Context

![Top-down multi-agent scene]({(ROOT / "compare_crash_vs_safe.png").as_posix()}){{width=62%}}

::: notes
Explain that trajectory selection is risk management under uncertainty, not only geometric planning. Point out the ego vehicle, uncertain dynamic obstacles, and map-clearance constraints.
:::

# The Efficiency versus Safety Conflict

| Safety side | Deployment tension | Efficiency side |
| :--- | :--- | :--- |
| Hard constraints | A physical vehicle has a millisecond-level control loop. | Real-time latency |
| Map clearance | Heavy optimization can timeout online. | Predictable compute |
| Collision avoidance | Overly conservative policies create freezing behavior. | Smooth progress |

::: notes
Use this slide as the seesaw: pushing safety too hard can create computational or behavioral failure.
:::

# Limitations of Current Solutions

|  | Slow computation | Fast computation |
| :--- | :--- | :--- |
| High safety determinism | Traditional solvers: rigorous, but hard to run online at scale. | Ideal target: fast, deterministic, risk-aware selection. |
| Low safety determinism | Offline search and scenario replay: useful, but not a live policy. | End-to-end DL/RL: fast, but weak hard-safety guarantees. |

::: notes
Lead naturally into CAMP as the system designed for the blank/ideal quadrant.
:::

# Introducing the CAMP Concept

| System position | Role |
| :--- | :--- |
| Black-box base predictor / planner | Generates candidate trajectories from the current scene. |
| CAMP meta-policy filter | Maps candidates to conic atoms, scores risk, and filters unsafe options. |
| Controller | Receives one selected trajectory plus diagnostics. |

::: notes
Emphasize decoupling: behavior generation stays in the base stack; safety enforcement is handled by CAMP.
:::

# Key Innovation 1: One-Shot Inference

![CAMP pipeline]({asset("pipeline.png")}){{width=82%}}

::: notes
Explain the comparison verbally: traditional online optimization has iterative solves and convergence risk; CAMP deployment is one forward pass plus deterministic candidate selection.
:::

# Key Innovation 2: Zero-Retraining Plug-and-Play

| Integration principle | TiERIV implication |
| :--- | :--- |
| Freeze the base predictor | No need to retrain foundational predictive models. |
| Treat planner output as candidate distribution | CAMP can attach to existing trajectory generation modules. |
| Reuse diagnostics and hard masks | Safety layer can evolve without destabilizing the base stack. |

::: notes
The lock metaphor is that the base model remains frozen while CAMP operates as an upper-level filter.
:::

# Evaluation Methodology on nuScenes

![Representative static scenario sheet]({asset("qual_contact_sheet.png")}){{width=74%}}

::: notes
Stress that the evaluation uses challenging real-world scenes rather than simplified demonstrations. Baselines include Pred Top1, Oracle MinADE, Select Static, Reranker Safe, and Finetune Safe.
:::

# Achieving the Absolute Safety Floor

![Hard-constraint violation comparison]({asset("violation_bar.png")}){{width=76%}}

::: notes
Avoid claiming zero violation if the candidate pool contains no safe candidate. The claim is floor achievement under the candidate set.
:::

# Operational Trade-offs: Progress versus Conservatism

![Safety-progress frontier]({asset("tradeoff_scatter.png")}){{width=68%}}

::: notes
Address the industry concern that safety can become crawling behavior. Use the static-frame story verbally: candidate set enters a narrow region, CAMP rejects high-risk options, and ego exits smoothly instead of freezing.
:::

# System-Level Deployment Architecture

| Autonomy stack stage | CAMP data flow |
| :--- | :--- |
| Perception | Agents, map context, scene state, uncertainty signals |
| Prediction / planning | Candidate trajectories and scene embedding |
| CAMP intervention point | Atom extraction, hard mask, risk scoring, candidate selection |
| Control | Selected trajectory and safety diagnostics |

::: notes
Make the integration point concrete for TiERIV: inputs, outputs, and the exact stack boundary.
:::

# Computational Efficiency & Latency

| Module | Runtime role | TiERIV profiling target |
| :--- | :--- | :--- |
| Candidate generator | Existing stack output | Existing budget |
| Atom extraction | Vectorized candidate features | Profile on platform |
| CAMP scoring | One forward pass plus weighted cost | Millisecond-level overhead target |
| Hard-mask selection | Feasible argmin | Deterministic, bounded |
| Controller handoff | Existing tracking interface | Existing budget |

::: notes
Do not overclaim final latency before profiling on TiERIV hardware. The message is a bounded and measurable integration path.
:::

# Proposed Integration with TiERIV

| Next step | Required input from TiERIV |
| :--- | :--- |
| API interface specification | Candidate trajectory format, scene embedding, map and obstacle fields |
| Hardware constraints | CPU/GPU budget, planning-cycle timing, memory ceiling |
| Testing sandbox | Logged scenarios, simulation runner, safety metric definitions |
| Pilot success metrics | Clearance violations, collision proxies, progress, comfort, fallback rate |

::: notes
Shift the meeting toward concrete engineering collaboration and ask where TiERIV's constraints are tightest.
:::

# Summary & Open Discussion

| Core selling point | Why it matters |
| :--- | :--- |
| Absolute safety floor | Minimizes hard-constraint violations within the available candidate set. |
| Zero retraining | Keeps TiERIV's base predictor and planner stable. |
| Real-time efficiency | Moves heavy robust optimization offline and keeps deployment one-shot. |
| Open discussion | Deployment details, platform interface, latency profiling, or mathematical formulation. |

::: notes
Close with the three messages, then hand the floor to TiERIV.
:::

# Appendix: Master Problem Formulation

| Symbol | Role |
| :--- | :--- |
| A(x, y_k) | Conic atom vector for candidate trajectory k. |
| w(x) | Scene-conditioned nonnegative atom weights. |
| m_k | Hard feasibility mask for candidate k. |
| alpha | CVaR tail probability level. |
| RU-CVaR objective | min over Theta of eta plus tail-risk slack plus regularization. |

::: notes
Use this only if the discussion turns theoretical.
:::

# Appendix: Benders Decomposition Implementation

| Step | Logic |
| :--- | :--- |
| 1. Initialize | Start from preference-warmed atom weights. |
| 2. Inner search | Identify active high-risk candidates under current weights. |
| 3. Cut generation | Add cuts that expose current safety violations. |
| 4. Master update | Re-solve the conic master with accumulated cuts. |
| 5. Export | Save fixed policy parameters for one-shot deployment. |

::: notes
Keep the explanation at the algorithmic level: expensive training loop offline, compact policy online.
:::
"""
    MARKDOWN_OUT.write_text(md, encoding="utf-8")


def qn(namespace: str, tag: str) -> str:
    return f"{{{ {'p': P_NS, 'a': A_NS, 'r': R_NS}[namespace] }}}{tag}"


def next_shape_id(slide_xml: etree._Element) -> int:
    ids = [
        int(el.get("id"))
        for el in slide_xml.xpath(".//p:cNvPr[@id]", namespaces=NS)
        if (el.get("id") or "").isdigit()
    ]
    return max(ids, default=1) + 1


def set_shape_id(shape: etree._Element, shape_id: int, name: str) -> None:
    c_nv_pr = shape.find(".//p:cNvPr", namespaces=NS)
    if c_nv_pr is not None:
        c_nv_pr.set("id", str(shape_id))
        c_nv_pr.set("name", name)


def set_xfrm(shape: etree._Element, x: int, y: int, cx: int, cy: int) -> None:
    xfrm = shape.find(".//a:xfrm", namespaces=NS)
    if xfrm is None:
        sp_pr = shape.find(".//p:spPr", namespaces=NS)
        if sp_pr is None:
            return
        xfrm = etree.SubElement(sp_pr, qn("a", "xfrm"))
    off = xfrm.find("a:off", namespaces=NS)
    if off is None:
        off = etree.SubElement(xfrm, qn("a", "off"))
    ext = xfrm.find("a:ext", namespaces=NS)
    if ext is None:
        ext = etree.SubElement(xfrm, qn("a", "ext"))
    off.set("x", str(x))
    off.set("y", str(y))
    ext.set("cx", str(cx))
    ext.set("cy", str(cy))


def set_text(shape: etree._Element, text: str, size: int = 750, color: str = "5E6A71") -> None:
    text_nodes = shape.xpath(".//a:t", namespaces=NS)
    if text_nodes:
        text_nodes[0].text = text
        for node in text_nodes[1:]:
            node.text = ""
    for r_pr in shape.xpath(".//a:rPr", namespaces=NS):
        r_pr.set("sz", str(size))
        for child in list(r_pr):
            if child.tag == qn("a", "solidFill"):
                r_pr.remove(child)
        fill = etree.SubElement(r_pr, qn("a", "solidFill"))
        etree.SubElement(fill, qn("a", "srgbClr"), val=color)


def remove_placeholder(shape: etree._Element) -> None:
    nv_pr = shape.find(".//p:nvPr", namespaces=NS)
    if nv_pr is not None:
        for ph in nv_pr.findall("p:ph", namespaces=NS):
            nv_pr.remove(ph)


def template_shape_by_id(shape_id: str) -> etree._Element:
    with zipfile.ZipFile(TEMPLATE_PPTX, "r") as z:
        xml = etree.fromstring(z.read("ppt/slides/slide1.xml"))
    return xml.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr[@id="{shape_id}"]]', namespaces=NS)[0]


def add_cmu_elements(raw_pptx: Path, styled_pptx: Path) -> None:
    top_line = template_shape_by_id("4")
    bottom_line = template_shape_by_id("5")
    header_text_template = template_shape_by_id("10")
    footer_text_template = template_shape_by_id("36")
    page_text_template = template_shape_by_id("11")

    with zipfile.ZipFile(raw_pptx, "r") as zin:
        presentation_xml = etree.fromstring(zin.read("ppt/presentation.xml"))
        size_el = presentation_xml.find(".//p:sldSz", namespaces=NS)
        slide_w = int(size_el.get("cx"))
        slide_h = int(size_el.get("cy"))
        slide_names = sorted(
            [n for n in zin.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda n: int(Path(n).stem.replace("slide", "")),
        )
        slide_count = len(slide_names)

        with zipfile.ZipFile(styled_pptx, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in slide_names:
                    slide_index = slide_names.index(info.filename) + 1
                    xml = etree.fromstring(data)
                    sp_tree = xml.find(".//p:spTree", namespaces=NS)
                    if sp_tree is not None:
                        next_id = next_shape_id(xml)

                        top = copy.deepcopy(top_line)
                        set_shape_id(top, next_id, "CMU blue top rule")
                        set_xfrm(top, 0, 0, slide_w, 0)
                        next_id += 1

                        bottom = copy.deepcopy(bottom_line)
                        set_shape_id(bottom, next_id, "CMU blue footer rule")
                        set_xfrm(bottom, 0, slide_h - 311896, slide_w, 0)
                        next_id += 1

                        header = copy.deepcopy(header_text_template)
                        set_shape_id(header, next_id, "CMU briefing header")
                        set_xfrm(header, slide_w - 2790000, 110000, 2300000, 190000)
                        set_text(header, "CAMP RESEARCH BRIEFING", size=700, color="092747")
                        remove_placeholder(header)
                        next_id += 1

                        footer = copy.deepcopy(footer_text_template)
                        set_shape_id(footer, next_id, "CMU footer label")
                        set_xfrm(footer, 420000, slide_h - 250000, 5600000, 160000)
                        set_text(footer, "Carnegie Mellon University Research Collaboration", size=650, color="5E6A71")
                        remove_placeholder(footer)
                        next_id += 1

                        page = copy.deepcopy(page_text_template)
                        set_shape_id(page, next_id, "CMU page number")
                        set_xfrm(page, slide_w - 650000, slide_h - 250000, 320000, 160000)
                        set_text(page, f"{slide_index:02d}", size=650, color="5E6A71")
                        remove_placeholder(page)

                        sp_tree.insert(2, top)
                        sp_tree.insert(3, bottom)
                        sp_tree.append(header)
                        sp_tree.append(footer)
                        sp_tree.append(page)
                    data = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
                zout.writestr(info.filename, data)


def run_pandoc() -> None:
    subprocess.run(
        [
            "pandoc",
            str(MARKDOWN_OUT),
            "--slide-level=1",
            "-o",
            str(RAW_PPTX_OUT),
        ],
        cwd=ROOT,
        check=True,
    )
    add_cmu_elements(RAW_PPTX_OUT, PPTX_OUT)


def main() -> None:
    if not CMU_LOGO.exists():
        DRIVE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(TEMPLATE_PPTX, "r") as z:
            CMU_LOGO.write_bytes(z.read("ppt/media/image-1-1.png"))
    write_markdown()
    run_pandoc()
    print(PPTX_OUT)


if __name__ == "__main__":
    main()
