#!/usr/bin/env python3
"""Materialize the sealed nonFresh actual-native production RC authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_authority import (  # noqa: E402
    FILES,
    freeze_nonfresh_production_equivalence_authority,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_fixture import (  # noqa: E402
    build_nonfresh_map_suite,
    build_nonfresh_prepared_runtime_rows,
    build_nonfresh_production_equivalence_plan,
    build_nonfresh_runtime_qualification_rows,
    select_nonfresh_actual_native_fixtures,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (  # noqa: E402
    materialize_signal_complete_route_assets,
    validate_signal_complete_route_assets,
)
from scripts.integrations.materialize_diffusion_planner_v25_signal_complete_routes import (  # noqa: E402
    _route_class,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    FIXED_DP_HEAD,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = (
    "camp_dp_v25_nonfresh_production_equivalence_materialization_v2"
)


def build(
    *,
    dp_repo: Path,
    formal_source_artifact: Path,
    formal_source_root_sha256: str,
    corrected_full_corpus_artifact: Path,
    corrected_full_corpus_root_sha256: str,
    corrected_full_corpus_review_artifact: Path,
    corrected_full_corpus_review_root_sha256: str,
    r0_source_artifact: Path,
    r0_source_root_sha256: str,
    training_artifact: Path,
    training_root_sha256: str,
    training_review_artifact: Path,
    training_review_root_sha256: str,
    calibration_freeze_artifact: Path,
    calibration_freeze_root_sha256: str,
    calibration_freeze_review_artifact: Path,
    calibration_freeze_review_root_sha256: str,
    accepted_protocol_preopen_artifact: Path,
    accepted_protocol_preopen_root_sha256: str,
    accepted_protocol_preopen_review_artifact: Path,
    accepted_protocol_preopen_review_root_sha256: str,
    fixed_dp_args: Path,
    probe_template: Path,
    output_dir: Path,
) -> str:
    implementation_head = _git_head(ROOT)
    dp_root = Path(dp_repo).resolve()
    if (
        _tracked_dirty(ROOT)
        or _git_head(dp_root) != FIXED_DP_HEAD
        or _tracked_dirty(dp_root)
    ):
        raise ValueError("production-equivalence CAMP/DP HEAD or clean drifted")
    output = Path(output_dir)
    if str(output) != str(output.resolve()) or output.exists():
        raise ValueError(
            "production-equivalence output must be canonical and absent"
        )
    source_bindings = {
        "formal_source": _open_binding(
            formal_source_artifact,
            formal_source_root_sha256,
            "formal source",
        ),
        "corrected_full_corpus": _open_binding(
            corrected_full_corpus_artifact,
            corrected_full_corpus_root_sha256,
            "corrected full corpus",
        ),
        "corrected_full_corpus_review": _open_binding(
            corrected_full_corpus_review_artifact,
            corrected_full_corpus_review_root_sha256,
            "corrected full corpus review",
        ),
        "r0_source": _open_binding(
            r0_source_artifact, r0_source_root_sha256, "R0 source"
        ),
    }
    upstream_bindings = {
        "training": _open_binding(
            training_artifact, training_root_sha256, "training"
        ),
        "training_review": _open_binding(
            training_review_artifact,
            training_review_root_sha256,
            "training review",
        ),
        "calibration_freeze": _open_binding(
            calibration_freeze_artifact,
            calibration_freeze_root_sha256,
            "calibration freeze",
        ),
        "calibration_freeze_review": _open_binding(
            calibration_freeze_review_artifact,
            calibration_freeze_review_root_sha256,
            "calibration freeze review",
        ),
        "accepted_protocol_preopen": _open_binding(
            accepted_protocol_preopen_artifact,
            accepted_protocol_preopen_root_sha256,
            "accepted protocol preopen",
        ),
        "accepted_protocol_preopen_review": _open_binding(
            accepted_protocol_preopen_review_artifact,
            accepted_protocol_preopen_review_root_sha256,
            "accepted protocol preopen review",
        ),
    }
    protocol_source = _canonical_json(
        Path(accepted_protocol_preopen_artifact).resolve()
        / "preopen_authority.json"
    )
    experiment_protocol = protocol_source.get("experiment_protocol")
    if type(experiment_protocol) is not dict:
        raise ValueError("accepted experiment protocol is unavailable")
    external_assets = {
        "fixed_dp_args": _file_asset(fixed_dp_args, "fixed DP args"),
        "probe_template": _file_asset(probe_template, "probe template"),
    }
    formal_plan = _strict_external_json(
        Path(formal_source_artifact).resolve()
        / "controlled_corpus_final_plan.json"
    )
    semantic_chains = _strict_external_json(
        Path(corrected_full_corpus_artifact).resolve()
        / "semantic_authority_chains.json"
    )
    selected = select_nonfresh_actual_native_fixtures(
        formal_plan=formal_plan,
        semantic_authority_chains=semantic_chains,
    )
    plan = build_nonfresh_production_equivalence_plan(
        selected_fixtures=selected,
        source_fixture_root_sha256=corrected_full_corpus_root_sha256,
    )

    output.mkdir(parents=True)
    try:
        maps_root = output / "maps"
        maps_root.mkdir()
        source_map_paths: dict[str, str] = {}
        for selected_row in selected:
            case = selected_row["case"]
            source = Path(case["source_map_path"]).resolve()
            map_sha = case["source_map_sha256"]
            if (
                not source.is_file()
                or source.is_symlink()
                or _sha256(source) != map_sha
            ):
                raise ValueError("accepted nonFresh source map bytes drifted")
            source_map_paths.setdefault(map_sha, str(source))
            target = maps_root / f"{map_sha}.osm"
            if not target.exists():
                shutil.copyfile(source, target)
            if _sha256(target) != map_sha:
                raise ValueError("copied nonFresh map bytes drifted")
        map_suite = build_nonfresh_map_suite(
            plan=plan,
            map_artifact=output,
            source_map_paths=source_map_paths,
        )
        route_class, _route_source = _route_class(dp_root)
        route_root = output / "route_materialization"
        route_manifest = materialize_signal_complete_route_assets(
            plan=plan,
            map_artifact=output,
            output_dir=route_root,
            route_class=route_class,
        )
        route_manifest = validate_signal_complete_route_assets(
            route_manifest,
            plan=plan,
            map_artifact=output,
            route_class=route_class,
        )
        prepared = build_nonfresh_prepared_runtime_rows(
            plan=plan,
            selected_fixtures=selected,
            map_artifact=output,
        )
        qualifications = build_nonfresh_runtime_qualification_rows(plan)
        authority = freeze_nonfresh_production_equivalence_authority(
            implementation_head=implementation_head,
            fixed_dp_head=FIXED_DP_HEAD,
            critical_implementation_manifest=tracked_implementation_manifest(
                ROOT
            ),
            experiment_protocol=experiment_protocol,
            execution_plan=plan,
            prepared_runtime_rows=prepared,
            route_asset_manifest=route_manifest,
            map_suite=map_suite,
            runtime_qualification_rows=qualifications,
            upstream_bindings=upstream_bindings,
            source_fixture_bindings=source_bindings,
            frozen_external_assets=external_assets,
        )
        _write(output / "preopen_authority.json", authority)
        _write(output / FILES["plan"], plan)
        _write(output / FILES["prepared_runtime"], prepared)
        _write(output / FILES["route_assets"], route_manifest)
        _write(output / FILES["map_suite"], map_suite)
        _write(
            output / "runtime_qualification_rows.json",
            qualifications,
        )
        _write(
            output / "selected_source_fixtures.json",
            [
                {
                    "nonfresh_scenario_class": row[
                        "nonfresh_scenario_class"
                    ],
                    "source_scenario_id": row["case"]["scenario_id"],
                    "route_identity_sha256": row["case"][
                        "route_identity_sha256"
                    ],
                    "source_chain_sha256": row["source_chain"][
                        "source_chain_sha256"
                    ],
                }
                for row in selected
            ],
        )
        _write(
            route_root / "route_assets.json",
            route_manifest,
        )
        _write(
            output / "report.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": (
                    "sealed_nonfresh_actual_native_production_"
                    "equivalence_authority"
                ),
                "implementation_head": implementation_head,
                "actual_native_receipt_contract_sha256": authority[
                    "actual_native_receipt_contract_sha256"
                ],
                "scenario_classes": list(
                    authority["scenario_classes"]
                ),
                "paired_unit_count": 3,
                "arm_run_count": 9,
                "tick_count": 576,
                "real_accepted_nonfresh_native_sources_used": True,
                "fresh_identity_or_rows_used": False,
                "fresh_outcomes_used": False,
            },
        )
        (output / "HEADS").write_bytes(
            (
                f"camp_head={implementation_head}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ).encode("ascii")
        )
        (output / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (output / "run.exit").write_bytes(b"0\n")
        return seal_artifact(
            output,
            label=(
                "V25 nonFresh actual-native production-equivalence authority"
            ),
        )
    except BaseException as exc:
        _write(
            output / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": (
                    "failed_nonfresh_actual_native_production_"
                    "equivalence_materialization"
                ),
                "reason": str(exc),
                "fresh_identity_cas_created": False,
                "fresh_outcome_consumed": False,
                "outcome_fields_consumed": [],
            },
        )
        (output / "run.exit").write_bytes(b"1\n")
        seal_artifact(
            output,
            label=(
                "failed V25 nonFresh actual-native production-equivalence "
                "authority"
            ),
        )
        raise


def _open_binding(
    path: Path, root_sha256: str, label: str
) -> dict[str, str]:
    artifact = Path(path).resolve()
    verify_complete_seal(artifact, root_sha256, label=label)
    if (artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError(f"{label} did not pass")
    return {"path": str(artifact), "root_sha256": root_sha256}


def _file_asset(path: Path, label: str) -> dict[str, str]:
    asset = Path(path).resolve()
    if not asset.is_file() or asset.is_symlink():
        raise ValueError(f"{label} is missing")
    return {"path": str(asset), "sha256": _sha256(asset)}


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
        object_pairs_hook=_pairs,
    )
    if type(value) is not dict or raw != _bytes(value):
        raise ValueError(f"noncanonical JSON: {path}")
    return value


def _strict_external_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8", "strict"),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
        object_pairs_hook=_pairs,
    )
    if type(value) is not dict:
        raise ValueError(f"external sealed JSON object required: {path}")
    return value


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dp-repo", type=Path, required=True)
    for name in (
        "formal-source",
        "corrected-full-corpus",
        "corrected-full-corpus-review",
        "r0-source",
        "training",
        "training-review",
        "calibration-freeze",
        "calibration-freeze-review",
        "accepted-protocol-preopen",
        "accepted-protocol-preopen-review",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(
            f"--{name}-root-sha256", type=str, required=True
        )
    parser.add_argument("--fixed-dp-args", type=Path, required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = build(**vars(_arguments()))
    print(
        json.dumps(
            {"status": "passed", "root_sha256": root},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
