#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRAINING_SOURCE = ROOT / "scripts/integrations/train_diffusion_planner_robust_camp.py"
DATASET_AUDIT_SOURCE = ROOT / "scripts/integrations/audit_diffusion_planner_camp_dataset.py"

READY_STATUS = "offline_convex_selector_training_plan_ready"
BLOCKED_STATUS = "offline_convex_selector_training_plan_blocked"
SOURCE_STATUS = "selector_label_weight_preflight_ready"
SOURCE_NEXT_WORK = "offline_convex_selector_training_plan_design_only"
AUTHORIZED_NEXT_WORK = "offline_convex_selector_training_input_manifest_gate"

FORMAL_SEEDS = (11, 12, 13)
REQUIRED_TRAINING_TOKENS = (
    "--label_source",
    "safety_cost_v1_hard_guarded",
    "solve_robust_margin_cutting_plane",
    "RobustMarginConfig",
    "project_simplex_rows",
    "risk_type",
    "cvar",
    "--alpha",
    "--l2_reg",
    "--require_atom_schema",
    "load_candidate_safety_cost_v1_values",
)
REQUIRED_DATASET_AUDIT_TOKENS = (
    "--closed_loop_outcome_policy",
    "--forbid_seed",
    "--require_finite_candidate_contract",
)
BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only offline convex selector training plan for DP-CAMP. "
            "This checks source readiness and emits a predeclared plan; it does "
            "not train or run Diffusion Planner."
        )
    )
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--training_source", type=Path, default=TRAINING_SOURCE)
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT_SOURCE)
    parser.add_argument(
        "--training_log_root",
        default="/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263",
    )
    parser.add_argument(
        "--output_training_dir",
        default="/root/autodl-tmp/camp_dp_offline_convex_selector_training",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        preflight=_load_json(args.preflight_json),
        label=args.label,
        training_source=args.training_source,
        dataset_audit_source=args.dataset_audit_source,
        training_log_root=args.training_log_root,
        output_training_dir=args.output_training_dir,
        paths={"preflight_json": str(args.preflight_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    preflight: dict[str, Any],
    label: str | None = None,
    training_source: Path = TRAINING_SOURCE,
    dataset_audit_source: Path = DATASET_AUDIT_SOURCE,
    training_log_root: str,
    output_training_dir: str,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    training_text = _read_text(training_source)
    dataset_audit_text = _read_text(dataset_audit_source)
    source_checks = [
        *_preflight_checks(preflight),
        _token_check("training_source_supports_hard_guarded_cvar", training_text, REQUIRED_TRAINING_TOKENS),
        _token_check("dataset_audit_supports_no_leak_contract", dataset_audit_text, REQUIRED_DATASET_AUDIT_TOKENS),
    ]
    plan_checks = _plan_checks(training_log_root=training_log_root, output_training_dir=output_training_dir)
    passed = all(check["passed"] for check in [*source_checks, *plan_checks])
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_selector_training_plan_v1",
            "label": label,
            "role": (
                "design-only plan for a static robust CAMP selector trained over "
                "fixed DP candidate logs with hard-guarded SafetyCost labels"
            ),
            "training": False,
            "training_execution": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": {
                **(paths or {}),
                "training_source": str(training_source),
                "dataset_audit_source": str(dataset_audit_source),
            },
            "math_boundary": (
                "The planned training treats DP candidate atoms as constants and "
                "optimizes CAMP weights only through affine scores a_k^T w. The "
                "chosen implementation is the existing robust margin cutting-plane "
                "master with simplex weights, L2 regularization, and optional CVaR "
                "risk. Hard-guarded SafetyCost labels come from offline outcomes "
                "only and cannot appear as online selector inputs. This remains a "
                "finite-candidate convex CAMP training plan, not a DP-side "
                "classical Benders claim."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "training_plan": _training_plan(training_log_root, output_training_dir),
        "input_manifest_gate": _input_manifest_gate(training_log_root),
        "accept_reject_gates": _accept_reject_gates(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _preflight_checks(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = preflight.get("final_decision") or {}
    return [
        _check_equal("preflight_status_ready", decision.get("status"), SOURCE_STATUS),
        _check_equal("preflight_passed", decision.get("passed"), True),
        _check_equal(
            "preflight_authorizes_training_plan",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "preflight_training_execution_not_authorized",
            decision.get("training_execution_authorized"),
            False,
        ),
        _check_equal(
            "preflight_camp_retraining_not_authorized",
            decision.get("camp_retraining_authorized"),
            False,
        ),
        *_blocked_action_checks(decision, "preflight"),
    ]


def _plan_checks(*, training_log_root: str, output_training_dir: str) -> list[dict[str, Any]]:
    return [
        _check_nonempty("training_log_root_declared", training_log_root),
        _check_nonempty("output_training_dir_declared", output_training_dir),
        {
            "name": "formal_seeds_forbidden",
            "passed": True,
            "forbid_seed": list(FORMAL_SEEDS),
        },
        {
            "name": "input_manifest_required_before_training",
            "passed": True,
            "reason": (
                "training execution remains blocked until a manifest proves "
                "nonformal logs, required fields, atom schema, and no-leak policy"
            ),
        },
    ]


def _training_plan(training_log_root: str, output_training_dir: str) -> dict[str, Any]:
    command_template = [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/train_diffusion_planner_robust_camp.py",
        "--mode",
        "static",
        "--training_scope",
        "feasible_ranking",
        "--label_source",
        "safety_cost_v1_hard_guarded",
        "--objective",
        "robust_margin_cvar",
        "--risk_type",
        "cvar",
        "--alpha",
        "0.9",
        "--margin_scale",
        "0.1",
        "--margin_clip",
        "2.0",
        "--l2_reg",
        "1e-4",
        "--max_iter",
        "20",
        "--tolerance",
        "1e-6",
        "--solver",
        "CLARABEL",
        "--scale_percentile",
        "95.0",
        "--val_fraction",
        "0.2",
        "--seed",
        "7",
        "--require_atom_schema",
        "--output_dir",
        output_training_dir,
        "--selection_log",
        "<repeat for each nonformal camp_selection_log.json from approved manifest>",
    ]
    return {
        "training_log_root": training_log_root,
        "output_training_dir": output_training_dir,
        "model_family": "static robust CAMP finite-candidate affine scorer",
        "label_source": "safety_cost_v1_hard_guarded",
        "objective": "robust_margin_cvar",
        "risk_type": "cvar",
        "alpha": 0.9,
        "constraints": ["w >= 0", "sum(w) = 1", "required atom schema"],
        "regularization": {"l2_reg": 1e-4},
        "split": {"type": "grouped_train_val", "val_fraction": 0.2, "seed": 7},
        "command_template": command_template,
    }


def _input_manifest_gate(training_log_root: str) -> dict[str, Any]:
    return {
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "root": training_log_root,
        "required_before_training": [
            "discover exact camp_selection_log.json list",
            "exclude seeds 11, 12, and 13",
            "verify candidate_closed_loop_outcomes are present for labels",
            "verify atoms and feasible_mask shape consistency",
            "verify exact ordered atom schema",
            "verify required scenario buckets remain covered",
            "write immutable manifest with path count and SHA",
        ],
    }


def _accept_reject_gates() -> dict[str, list[str]]:
    return {
        "accept": [
            "input manifest excludes formal seeds and contains nonempty fixed logs",
            "dataset audit passes closed_loop_outcome_policy=required",
            "training artifact produces simplex weights and atom scales",
            "complete-master or cutting-plane audit matches saved solution",
            "candidate-branch SafetyCost evaluation improves or is noninferior to DP Top-1 in all required buckets",
            "hard-guarded oracle gap is reduced with no forbidden online outcome features",
        ],
        "reject": [
            "any formal seed appears in the manifest or artifact",
            "any label depends on future outcome at online selection time",
            "atom schema changes without a separate no-leak gate",
            "training becomes nonconvex or uses a neural selector",
            "selector worsens required SafetyCost buckets, fallback, or comfort gates",
            "any result is described as classical Benders without dual/cut proof",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["training_plan"]
    lines = [
        "# Offline Convex Selector Training Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- training execution authorized: `{decision['training_execution_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` | {_detail(check)} |")
    lines.extend(["", "## Plan", ""])
    lines.extend(
        [
            f"- model family: `{plan['model_family']}`",
            f"- label source: `{plan['label_source']}`",
            f"- objective: `{plan['objective']}`",
            f"- risk type: `{plan['risk_type']}`",
            f"- alpha: `{plan['alpha']}`",
            f"- split: `{plan['split']}`",
            "",
            "## Command Template",
            "",
            "```bash",
            " \\\n  ".join(plan["command_template"]),
            "```",
            "",
            "## Input Manifest Gate",
            "",
            f"- authorized next work: `{report['input_manifest_gate']['authorized_next_work']}`",
        ]
    )
    for item in report["input_manifest_gate"]["required_before_training"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Accept Gates", ""])
    lines.extend(f"- {item}" for item in report["accept_reject_gates"]["accept"])
    lines.extend(["", "## Reject Gates", ""])
    lines.extend(f"- {item}" for item in report["accept_reject_gates"]["reject"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Build and audit an immutable nonformal training input manifest "
            "before training execution."
            if passed
            else "Repair preflight or source support before any training plan use."
        ),
    }


def _blocked_action_checks(decision: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name, False), False)
        for name in BLOCKED_ACTIONS
    ]


def _token_check(name: str, text: str | None, tokens: tuple[str, ...]) -> dict[str, Any]:
    missing = [token for token in tokens if text is None or token not in text]
    return {"name": name, "passed": not missing, "missing_tokens": missing}


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check_nonempty(name: str, value: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(str(value).strip()), "actual": value}


def _detail(check: dict[str, Any]) -> str:
    if "missing_tokens" in check:
        return ", ".join(check["missing_tokens"]) or "none"
    if "expected" in check:
        return f"actual=`{check.get('actual')}`, expected=`{check.get('expected')}`"
    if "reason" in check:
        return str(check["reason"])
    if "forbid_seed" in check:
        return ",".join(str(seed) for seed in check["forbid_seed"])
    return str(check.get("actual", ""))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
