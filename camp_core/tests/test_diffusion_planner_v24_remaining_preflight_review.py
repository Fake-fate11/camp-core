import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_CAMP_HEAD = "a" * 40
REVIEWER_CAMP_HEAD = "b" * 40


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    manifest = "".join(
        f"{_file_sha(path)}  {path.relative_to(root).as_posix()}\n" for path in files
    )
    (root / "SHA256SUMS").write_text(manifest, encoding="utf-8")
    root_sha = _file_sha(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="ascii")
    return root_sha


def _row_order_sha(routes: list[dict]) -> str:
    rows = [
        {"record_key": route["record_key"], "seed": seed}
        for route in sorted(routes, key=lambda item: item["record_key"])
        for seed in (24002, 24003, 24004, 24005)
    ]
    encoded = (
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fixture(tmp_path: Path) -> dict:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    routes = []
    for index in range(2):
        map_path = tmp_path / f"map-{index}.osm"
        map_path.write_text(f"map-{index}", encoding="utf-8")
        asset_path = corpus_root / "route_assets" / f"route-{index}.pkl"
        asset_path.parent.mkdir(exist_ok=True)
        asset_path.write_text(f"route-{index}", encoding="utf-8")
        identity = _sha(f"route:{index}")
        routes.append(
            {
                "record_key": f"family/map/{index}/{identity[:16]}",
                "identity_sha256": identity,
                "map_family_id": "family",
                "logical_map_sha256": _sha("logical-map"),
                "corridor_group_sha256": _sha("corridor"),
                "source_map_path": str(map_path),
                "source_map_sha256": _file_sha(map_path),
                "source_stratum": {"traffic_light": False},
                "route_spec": {
                    "map_path": str(map_path),
                    "lanelet_ids": [index + 1],
                    "start_pose": [0.0, 0.0, 0.0],
                    "goal_pose": [80.0, 0.0, 0.0],
                },
                "route_asset": {
                    "path": str(asset_path),
                    "sha256": _file_sha(asset_path),
                },
                "seeds": [24001, 24002, 24003, 24004, 24005],
            }
        )
    corpus = {
        "schema": "camp_dp_v24_native_corpus_manifest_v1",
        "split": "train",
        "route_count": 2,
        "routes": routes,
        "seeds": [24001, 24002, 24003, 24004, 24005],
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
    }
    (corpus_root / "corpus_manifest.json").write_text(json.dumps(corpus))
    corpus_sha = _seal(corpus_root)

    corpus_review_root = tmp_path / "corpus-review"
    corpus_review_root.mkdir()
    corpus_review = {
        "schema": "camp_dp_v24_native_corpus_static_preflight_review_v1",
        "status": "passed",
        "failed_count": 0,
        "source_preflight_root_sha256": corpus_sha,
        "preflight_reexecuted": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "training_executed": False,
        "claim_authorized": False,
    }
    (corpus_review_root / "review.json").write_text(json.dumps(corpus_review))
    corpus_review_sha = _seal(corpus_review_root)

    pilot_root = tmp_path / "pilot"
    for index, route in enumerate(routes):
        receipt = {
            "schema": "camp_dp_v24_native_corpus_pilot_run_receipt_v1",
            "status": "failed" if index == 0 else "ok",
            "phase": "capability_pilot_all_train_routes_first_seed",
            "record_key": route["record_key"],
            "route_identity_sha256": route["identity_sha256"],
            "seed": 24001,
            "retained_in_denominator": True,
            "failure_reason": (
                "ValueError: route slot 0 requires a positive speed limit"
                if index == 0
                else None
            ),
            "snapshot_sha256": [],
        }
        path = (
            pilot_root
            / "receipts"
            / "train"
            / route["identity_sha256"]
            / "seed_24001.json"
        )
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(receipt))
    pilot_sha = _seal(pilot_root)

    route_order = [
        route["record_key"]
        for route in sorted(routes, key=lambda item: item["record_key"])
    ]
    pilot_review = {
        "schema": "camp_dp_v24_native_corpus_pilot_independent_review_v1",
        "status": "passed_with_warning",
        "failed_count": 0,
        "source_pilot_root_sha256": pilot_sha,
        "source_corpus_preflight_root_sha256": corpus_sha,
        "recomputed": {
            "failure_reason_counts": {
                "ValueError: route slot 0 requires a positive speed limit": 1
            }
        },
        "decision": {
            "authorized": True,
            "action": "execute_frozen_remaining_train_seeds",
            "seeds": [24002, 24003, 24004, 24005],
            "route_count": 2,
            "route_order": route_order,
            "preserve_all_failures_and_denominator": True,
            "route_removal_replacement_reordering_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "review_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    pilot_review_root = tmp_path / "pilot-review"
    pilot_review_root.mkdir()
    (pilot_review_root / "review.json").write_text(json.dumps(pilot_review))
    pilot_review_sha = _seal(pilot_review_root)

    preflight = {
        "schema": "camp_dp_v24_native_corpus_remaining_execution_preflight_v1",
        "status": "passed",
        "check_count": 5,
        "failed_count": 0,
        "checks": [
            {"name": "remaining_task_lock_available", "passed": True},
            {"name": "remaining_route_seed_runs_8", "passed": True},
            {"name": "remaining_configs_8", "passed": True},
            {"name": "all_unique_route_assets_2_unchanged", "passed": True},
            {"name": "disk_floor", "passed": True},
        ],
        "route_count": 2,
        "seeds": [24002, 24003, 24004, 24005],
        "route_seed_run_count": 8,
        "row_order_sha256": _row_order_sha(routes),
        "theoretical_max_snapshots": 512,
        "pilot_route_denominator_retained": 2,
        "pilot_failures_retained": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "training_executed": False,
        "tuning_executed": False,
        "claim_authorized": False,
        "next_work_target": "v24_native_corpus_remaining_train_seeds_static_preflight_independent_review_only",
    }
    preflight_root = tmp_path / "remaining-preflight"
    preflight_root.mkdir()
    heads = (
        f"CAMP_HEAD={SOURCE_CAMP_HEAD}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256={corpus_sha}\n"
        f"SOURCE_CORPUS_REVIEW_ROOT_SHA256={corpus_review_sha}\n"
        f"SOURCE_PILOT_ROOT_SHA256={pilot_sha}\n"
        f"SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256={pilot_review_sha}\n"
    )
    files = {
        "HEADS": heads,
        "COMMAND": "v24 native corpus remaining-execution-preflight\n",
        "preflight.json": json.dumps(preflight),
        "preflight.md": "remaining static preflight\n",
        "stdout.txt": json.dumps(preflight) + "\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }
    for name, content in files.items():
        (preflight_root / name).write_text(content)
    preflight_sha = _seal(preflight_root)

    template = copy.deepcopy(json.loads(BASE_CONFIG.read_text(encoding="utf-8")))
    for owner, name in (
        ("fixed_dp", "checkpoint"),
        ("fixed_dp", "args_json"),
        ("selector", "atom_scales"),
        ("selector", "weights"),
    ):
        path = tmp_path / f"{owner}-{name}"
        path.write_text(f"{owner}-{name}")
        template[owner][name] = {"path": str(path), "sha256": _file_sha(path)}

    return {
        "preflight_root": preflight_root,
        "preflight_sha": preflight_sha,
        "corpus_root": corpus_root,
        "corpus_sha": corpus_sha,
        "corpus_review_root": corpus_review_root,
        "corpus_review_sha": corpus_review_sha,
        "pilot_root": pilot_root,
        "pilot_sha": pilot_sha,
        "pilot_review_root": pilot_review_root,
        "pilot_review_sha": pilot_review_sha,
        "template": template,
    }


def _review(tmp_path: Path, monkeypatch, fixture: dict) -> dict:
    from scripts.integrations import (
        review_diffusion_planner_v24_remaining_preflight as reviewer,
    )

    def fake_run(command, **kwargs):
        del kwargs
        if command[-1] != "HEAD":
            value = ""
        elif str(tmp_path / "dp") in command:
            value = FIXED_DP_HEAD
        else:
            value = REVIEWER_CAMP_HEAD
        return SimpleNamespace(stdout=value + ("\n" if value else ""))

    monkeypatch.setattr(reviewer.subprocess, "run", fake_run)
    return reviewer.review_remaining_preflight(
        preflight_root=fixture["preflight_root"],
        expected_preflight_root_sha256=fixture["preflight_sha"],
        corpus_root=fixture["corpus_root"],
        expected_corpus_root_sha256=fixture["corpus_sha"],
        corpus_review_root=fixture["corpus_review_root"],
        expected_corpus_review_root_sha256=fixture["corpus_review_sha"],
        pilot_root=fixture["pilot_root"],
        expected_pilot_root_sha256=fixture["pilot_sha"],
        pilot_review_root=fixture["pilot_review_root"],
        expected_pilot_review_root_sha256=fixture["pilot_review_sha"],
        template=fixture["template"],
        camp_repo=tmp_path / "camp",
        expected_reviewer_camp_head=REVIEWER_CAMP_HEAD,
        dp_repo=tmp_path / "dp",
        expected_source_camp_head=SOURCE_CAMP_HEAD,
        expected_route_count=2,
        expected_source_invalid_count=1,
        expected_source_map_count=2,
        expected_preflight_check_count=5,
    )


def test_remaining_preflight_independent_review_passes(
    tmp_path: Path, monkeypatch
) -> None:
    fixture = _fixture(tmp_path)
    result = _review(tmp_path, monkeypatch, fixture)

    assert result["status"] == "passed"
    assert result["failed_count"] == 0
    assert result["route_count"] == 2
    assert result["route_seed_run_count"] == 8
    assert result["source_invalid_route_count"] == 1
    assert result["validated_run_config_count"] == 8
    assert result["decision"]["remaining_execution_authorized"] is True
    assert result["decision"]["tuning_authorized"] is False
    assert result["decision"]["holdout_access_authorized"] is False


def test_remaining_preflight_independent_review_rejects_row_order_drift(
    tmp_path: Path, monkeypatch
) -> None:
    fixture = _fixture(tmp_path)
    path = fixture["preflight_root"] / "preflight.json"
    preflight = json.loads(path.read_text())
    preflight["row_order_sha256"] = _sha("drifted")
    path.write_text(json.dumps(preflight))
    fixture["preflight_sha"] = _seal(fixture["preflight_root"])

    result = _review(tmp_path, monkeypatch, fixture)

    assert result["status"] == "failed"
    assert result["decision"]["remaining_execution_authorized"] is False
    assert any("row_order" in name for name in result["failed_checks"])


def test_remaining_preflight_reviewer_does_not_import_executor() -> None:
    source = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v24_remaining_preflight.py"
    ).read_text(encoding="utf-8")

    assert "execute_diffusion_planner_v24_native_corpus import" not in source
    assert "_execution_preflight(" not in source


def test_remaining_preflight_independent_review_rejects_open_corpus_review(
    tmp_path: Path, monkeypatch
) -> None:
    fixture = _fixture(tmp_path)
    review_path = fixture["corpus_review_root"] / "review.json"
    review = json.loads(review_path.read_text())
    review["holdout_opened"] = True
    review_path.write_text(json.dumps(review))
    old_review_sha = fixture["corpus_review_sha"]
    fixture["corpus_review_sha"] = _seal(fixture["corpus_review_root"])

    heads_path = fixture["preflight_root"] / "HEADS"
    heads = heads_path.read_text().replace(old_review_sha, fixture["corpus_review_sha"])
    heads_path.write_text(heads)
    fixture["preflight_sha"] = _seal(fixture["preflight_root"])

    result = _review(tmp_path, monkeypatch, fixture)

    assert result["status"] == "failed"
    assert result["decision"]["remaining_execution_authorized"] is False
    assert "corpus_review:passed_closed" in result["failed_checks"]
