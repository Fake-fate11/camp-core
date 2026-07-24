from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from scripts.integrations import (
    run_diffusion_planner_v25_holdout_execution as holdout_runner,
)
from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_plan_dispatch import (
    NONFRESH_CANARY_SPLIT,
)
from camp_core.integrations.diffusion_planner_v25_upstream_authority_roles import (
    ROLE_SPECS,
    freeze_upstream_authority_role_contract,
    validate_upstream_authority_role_contract,
    verify_upstream_authority_role_contract,
)
from scripts.integrations.review_diffusion_planner_v25_b4_preopen import (
    _verify_upstream_role_contract_independent,
)
from scripts.integrations.review_diffusion_planner_v25_holdout_evaluation import (
    _calibration_freeze_binding_independent,
)
from scripts.integrations.review_diffusion_planner_v25_holdout_execution import (
    _verify_execution_upstream_authorities_independent,
)
from scripts.integrations.evaluate_diffusion_planner_v25_holdout import (
    _calibration_freeze_binding,
)
from scripts.integrations.run_diffusion_planner_v25_holdout_execution import (
    _verify_execution_upstream_authorities,
)


PayloadMutator = Callable[[str, dict[str, Any]], None]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _seal(
    root: Path,
    *,
    payload_file: str,
    payload: dict[str, Any],
    run_exit: int,
    include_run_exit: bool = True,
    canonical: bool = True,
) -> tuple[Path, str]:
    root.mkdir(parents=True)
    if canonical:
        _write_json(root / payload_file, payload)
    else:
        (root / payload_file).write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    (root / "HEADS").write_text("camp_head=" + "a" * 40 + "\n", "ascii")
    (root / "COMMAND").write_text("fixture\n", "utf-8")
    if include_run_exit:
        (root / "run.exit").write_text(f"{run_exit}\n", "ascii")
    return root.resolve(), seal_artifact(root, label=root.name)


def _binding(value: tuple[Path, str]) -> dict[str, str]:
    return {"path": str(value[0]), "root_sha256": value[1]}


def _chain(
    root: Path,
    *,
    exit_overrides: dict[str, int | None] | None = None,
    payload_mutator: PayloadMutator | None = None,
    noncanonical_roles: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    exits = exit_overrides or {}
    noncanonical = noncanonical_roles or set()
    identity_b2 = "2" * 64
    identity_b3 = "3" * 64
    b2_failure = _seal(
        root / "embedded-b2-failure",
        payload_file="failure.json",
        payload={
            "schema_version": "camp_dp_v25_fresh_b2_execution_artifact_v2",
            "status": "failed_closed_fresh_b2_execution",
        },
        run_exit=1,
    )
    b3_failure = _seal(
        root / "embedded-b3-failure",
        payload_file="fatal.json",
        payload={
            "schema_version": "camp_dp_v25_holdout_artifact_fatal_v1",
            "status": "artifact_fatal",
            "holdout_identity_sha256": identity_b3,
        },
        run_exit=1,
    )
    b3_failure_review = _seal(
        root / "embedded-b3-failure-review",
        payload_file="report.json",
        payload={
            "schema_version": (
                "camp_dp_v25_holdout_execution_review_artifact_v1"
            ),
            "status": "passed_independent_holdout_artifact_fatal_review",
            "reviewed_root_sha256": b3_failure[1],
            "holdout_identity_sha256": identity_b3,
        },
        run_exit=0,
    )

    bindings: dict[str, dict[str, str]] = {}
    deferred = {
        "b2_consumed_failure",
        "b3_terminal_closeout",
        "calibration_recovery",
        "accepted_b3_preopen_review",
        "atom_mechanism_review",
        "b2_consumed_failure_review",
        "b3_terminal_closeout_review",
        "calibration_freeze_review",
        "calibration_preregistration_review",
        "calibration_recovery_review",
        "corrected_corpus_review",
        "production_equivalence_certificate_review",
        "storage_review",
        "training_review",
    }
    for role, spec in ROLE_SPECS.items():
        if role in deferred:
            continue
        payload = {
            "schema_version": spec["schema_version"],
            "status": spec["status"],
        }
        if payload_mutator is not None:
            payload_mutator(role, payload)
        expected_exit = exits.get(role, spec["run_exit"])
        artifact = _seal(
            root / role,
            payload_file=spec["payload_file"],
            payload=payload,
            run_exit=spec["run_exit"] if expected_exit is None else expected_exit,
            include_run_exit=expected_exit is not None,
            canonical=role not in noncanonical,
        )
        bindings[role] = _binding(artifact)

    closeouts = {
        "b2_consumed_failure": {
            "schema_version": ROLE_SPECS["b2_consumed_failure"][
                "schema_version"
            ],
            "status": ROLE_SPECS["b2_consumed_failure"]["status"],
            "failure_artifact": _binding(b2_failure),
            "holdout_identity": {
                "holdout_identity_sha256": identity_b2,
            },
        },
        "b3_terminal_closeout": {
            "schema_version": ROLE_SPECS["b3_terminal_closeout"][
                "schema_version"
            ],
            "status": ROLE_SPECS["b3_terminal_closeout"]["status"],
            "failure_artifact": _binding(b3_failure),
            "failure_review": _binding(b3_failure_review),
            "holdout_identity_sha256": identity_b3,
        },
    }
    for role, payload in closeouts.items():
        if payload_mutator is not None:
            payload_mutator(role, payload)
        artifact = _seal(
            root / role,
            payload_file=ROLE_SPECS[role]["payload_file"],
            payload=payload,
            run_exit=exits.get(role, 0) or 0,
            include_run_exit=exits.get(role, 0) is not None,
            canonical=role not in noncanonical,
        )
        bindings[role] = _binding(artifact)

    recovery_payload = {
        "schema_version": ROLE_SPECS["calibration_recovery"][
            "schema_version"
        ],
        "status": ROLE_SPECS["calibration_recovery"]["status"],
        "original_execution_artifact": bindings["calibration_raw"]["path"],
        "original_execution_root_sha256": bindings["calibration_raw"][
            "root_sha256"
        ],
        "original_execution_run_exit": 1,
    }
    if payload_mutator is not None:
        payload_mutator("calibration_recovery", recovery_payload)
    recovery = _seal(
        root / "calibration_recovery",
        payload_file="report.json",
        payload=recovery_payload,
        run_exit=exits.get("calibration_recovery", 0) or 0,
        include_run_exit=exits.get("calibration_recovery", 0) is not None,
        canonical="calibration_recovery" not in noncanonical,
    )
    bindings["calibration_recovery"] = _binding(recovery)

    review_pairs = {
        "accepted_b3_preopen_review": (
            "accepted_b3_preopen",
            None,
        ),
        "atom_mechanism_review": ("atom_mechanism", None),
        "b2_consumed_failure_review": (
            "b2_consumed_failure",
            identity_b2,
        ),
        "b3_terminal_closeout_review": (
            "b3_terminal_closeout",
            identity_b3,
        ),
        "calibration_freeze_review": ("calibration_freeze", None),
        "calibration_preregistration_review": (
            "calibration_preregistration",
            None,
        ),
        "corrected_corpus_review": ("corrected_corpus", None),
        "production_equivalence_certificate_review": (
            "production_equivalence_certificate",
            None,
        ),
        "storage_review": ("storage", None),
        "training_review": ("training", None),
    }
    for role, (source_role, identity) in review_pairs.items():
        spec = ROLE_SPECS[role]
        payload = {
            "schema_version": spec["schema_version"],
            "status": spec["status"],
            "reviewed_artifact": bindings[source_role]["path"],
            "reviewed_root_sha256": bindings[source_role]["root_sha256"],
        }
        if role == "accepted_b3_preopen_review":
            payload.pop("reviewed_artifact")
        if identity is not None:
            payload["holdout_identity_sha256"] = identity
        if payload_mutator is not None:
            payload_mutator(role, payload)
        expected_exit = exits.get(role, 0)
        artifact = _seal(
            root / role,
            payload_file=spec["payload_file"],
            payload=payload,
            run_exit=0 if expected_exit is None else expected_exit,
            include_run_exit=expected_exit is not None,
            canonical=role not in noncanonical,
        )
        bindings[role] = _binding(artifact)

    recovery_review_payload = {
        "schema_version": ROLE_SPECS["calibration_recovery_review"][
            "schema_version"
        ],
        "status": ROLE_SPECS["calibration_recovery_review"]["status"],
        "original_execution_artifact": bindings["calibration_raw"]["path"],
        "original_execution_root_sha256": bindings["calibration_raw"][
            "root_sha256"
        ],
        "original_execution_run_exit": 1,
        "reviewed_recovery_artifact": bindings["calibration_recovery"][
            "path"
        ],
        "reviewed_recovery_root_sha256": bindings["calibration_recovery"][
            "root_sha256"
        ],
    }
    if payload_mutator is not None:
        payload_mutator(
            "calibration_recovery_review", recovery_review_payload
        )
    expected_exit = exits.get("calibration_recovery_review", 0)
    recovery_review = _seal(
        root / "calibration_recovery_review",
        payload_file="report.json",
        payload=recovery_review_payload,
        run_exit=0 if expected_exit is None else expected_exit,
        include_run_exit=expected_exit is not None,
        canonical="calibration_recovery_review" not in noncanonical,
    )
    bindings["calibration_recovery_review"] = _binding(recovery_review)
    return bindings


def test_all_upstream_roles_freeze_and_independent_oracle_match(
    tmp_path: Path,
) -> None:
    bindings = _chain(tmp_path)
    contract = freeze_upstream_authority_role_contract(bindings)
    assert contract["role_count"] == 24
    assert validate_upstream_authority_role_contract(
        contract, bindings=bindings
    ) == contract
    assert verify_upstream_authority_role_contract(
        contract, bindings=bindings
    ) == contract
    _verify_upstream_role_contract_independent(contract, bindings=bindings)
    preopen = {
        "upstream_authority_role_contract": contract,
        "upstream_bindings": bindings,
    }
    _verify_execution_upstream_authorities(
        preopen=preopen, split="fresh_b4"
    )
    _verify_execution_upstream_authorities_independent(
        preopen=preopen, split="fresh_b4"
    )


def test_only_registered_legacy_roles_accept_noncanonical_sealed_json(
    tmp_path: Path,
) -> None:
    bindings = _chain(
        tmp_path / "accepted",
        noncanonical_roles={"corrected_corpus", "corrected_corpus_review"},
    )
    contract = freeze_upstream_authority_role_contract(bindings)
    verify_upstream_authority_role_contract(contract, bindings=bindings)
    _verify_upstream_role_contract_independent(contract, bindings=bindings)

    rejected = _chain(
        tmp_path / "rejected",
        noncanonical_roles={"training"},
    )
    with pytest.raises(ValueError, match="not canonical"):
        freeze_upstream_authority_role_contract(rejected)


@pytest.mark.parametrize("role", sorted(ROLE_SPECS))
def test_every_role_rejects_deletion_replacement_and_native_type_smuggling(
    tmp_path: Path,
    role: str,
) -> None:
    bindings = _chain(tmp_path)
    contract = freeze_upstream_authority_role_contract(bindings)

    deleted = copy.deepcopy(contract)
    deleted["roles"] = [
        row for row in deleted["roles"] if row["role"] != role
    ]
    with pytest.raises(ValueError):
        validate_upstream_authority_role_contract(
            deleted, bindings=bindings
        )
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities(
            preopen={
                "upstream_authority_role_contract": deleted,
                "upstream_bindings": bindings,
            },
            split="fresh_b4",
        )
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": deleted,
                "upstream_bindings": bindings,
            },
            split="fresh_b4",
        )

    replaced = copy.deepcopy(contract)
    row = next(item for item in replaced["roles"] if item["role"] == role)
    row["binding"]["root_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        validate_upstream_authority_role_contract(
            replaced, bindings=bindings
        )
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": replaced,
                "upstream_bindings": bindings,
            },
            split="fresh_b4",
        )

    smuggled = copy.deepcopy(contract)
    row = next(item for item in smuggled["roles"] if item["role"] == role)
    row["execution_terminal"]["run_exit"] = bool(
        row["execution_terminal"]["run_exit"]
    )
    with pytest.raises(ValueError):
        validate_upstream_authority_role_contract(
            smuggled, bindings=bindings
        )
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": smuggled,
                "upstream_bindings": bindings,
            },
            split="fresh_b4",
        )

    wrong_binding = copy.deepcopy(bindings)
    wrong_binding[role]["root_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": wrong_binding,
            },
            split="fresh_b4",
        )

    wrong_path = copy.deepcopy(bindings)
    wrong_path[role]["path"] = str((tmp_path / "missing").resolve())
    with pytest.raises((ValueError, FileNotFoundError)):
        _verify_execution_upstream_authorities(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": wrong_path,
            },
            split="fresh_b4",
        )
    with pytest.raises((ValueError, FileNotFoundError)):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": wrong_path,
            },
            split="fresh_b4",
        )


@pytest.mark.parametrize("role", sorted(ROLE_SPECS))
def test_every_role_rejects_native_exit_and_payload_status_mutation(
    tmp_path: Path,
    role: str,
) -> None:
    valid_bindings = _chain(tmp_path / "valid")
    contract = freeze_upstream_authority_role_contract(valid_bindings)
    wrong_exit = 0 if ROLE_SPECS[role]["run_exit"] == 1 else 1
    mutated_exit = _chain(
        tmp_path / "exit",
        exit_overrides={role: wrong_exit},
    )
    with pytest.raises((ValueError, FileNotFoundError)):
        freeze_upstream_authority_role_contract(mutated_exit)
    with pytest.raises((ValueError, FileNotFoundError)):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": mutated_exit,
            },
            split="fresh_b4",
        )

    def mutate(current_role: str, payload: dict[str, Any]) -> None:
        if current_role == role:
            payload["status"] = "unexpected_status"

    mutated_status = _chain(
        tmp_path / "status",
        payload_mutator=mutate,
    )
    with pytest.raises(ValueError):
        freeze_upstream_authority_role_contract(mutated_status)
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": mutated_status,
            },
            split="fresh_b4",
        )


def test_unknown_extra_duplicate_mode_and_status_are_rejected(
    tmp_path: Path,
) -> None:
    bindings = _chain(tmp_path)
    contract = freeze_upstream_authority_role_contract(bindings)
    cases = []

    extra = dict(bindings)
    extra["unknown"] = next(iter(bindings.values()))
    with pytest.raises(ValueError):
        validate_upstream_authority_role_contract(contract, bindings=extra)
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": extra,
            },
            split="fresh_b4",
        )
    with pytest.raises(ValueError):
        _verify_execution_upstream_authorities_independent(
            preopen={
                "upstream_authority_role_contract": contract,
                "upstream_bindings": extra,
            },
            split="fresh_b4",
        )

    duplicate = copy.deepcopy(contract)
    duplicate["roles"][-1] = copy.deepcopy(duplicate["roles"][0])
    cases.append(duplicate)

    wrong_mode = copy.deepcopy(contract)
    wrong_mode["roles"][0]["authority_disposition"]["mode"] = (
        "accepted_via_recovery"
    )
    cases.append(wrong_mode)

    wrong_status = copy.deepcopy(contract)
    wrong_status["roles"][0]["execution_terminal"]["status"] = "passed"
    cases.append(wrong_status)

    for changed in cases:
        with pytest.raises(ValueError):
            validate_upstream_authority_role_contract(
                changed, bindings=bindings
            )
        with pytest.raises(ValueError):
            _verify_execution_upstream_authorities_independent(
                preopen={
                    "upstream_authority_role_contract": changed,
                    "upstream_bindings": bindings,
                },
                split="fresh_b4",
            )


@pytest.mark.parametrize(
    ("role", "exit_value"),
    [
        ("calibration_raw", 0),
        ("calibration_raw", 2),
        ("calibration_raw", None),
        ("calibration_recovery", 1),
        ("calibration_recovery_review", 1),
    ],
)
def test_recovery_terminal_exit_mutations_fail_closed(
    tmp_path: Path,
    role: str,
    exit_value: int | None,
) -> None:
    bindings = _chain(tmp_path, exit_overrides={role: exit_value})
    with pytest.raises((ValueError, FileNotFoundError)):
        freeze_upstream_authority_role_contract(bindings)


@pytest.mark.parametrize(
    ("role", "field", "replacement"),
    [
        ("calibration_recovery", "original_execution_artifact", "/wrong"),
        (
            "calibration_recovery",
            "original_execution_root_sha256",
            "f" * 64,
        ),
        ("calibration_recovery", "original_execution_run_exit", True),
        (
            "calibration_recovery_review",
            "original_execution_root_sha256",
            "e" * 64,
        ),
        (
            "calibration_recovery_review",
            "reviewed_recovery_root_sha256",
            "d" * 64,
        ),
    ],
)
def test_recovery_crosschain_and_type_mutations_fail_closed(
    tmp_path: Path,
    role: str,
    field: str,
    replacement: Any,
) -> None:
    def mutate(current_role: str, payload: dict[str, Any]) -> None:
        if current_role == role:
            payload[field] = replacement

    bindings = _chain(tmp_path, payload_mutator=mutate)
    with pytest.raises(ValueError):
        freeze_upstream_authority_role_contract(bindings)


@pytest.mark.parametrize(
    ("role", "field"),
    [
        ("b2_consumed_failure", "failure_artifact"),
        ("b3_terminal_closeout", "failure_artifact"),
        ("b3_terminal_closeout", "failure_review"),
        ("b2_consumed_failure_review", "holdout_identity_sha256"),
        ("b3_terminal_closeout_review", "reviewed_root_sha256"),
    ],
)
def test_closeout_missing_or_crosslinked_fields_fail_closed(
    tmp_path: Path,
    role: str,
    field: str,
) -> None:
    def mutate(current_role: str, payload: dict[str, Any]) -> None:
        if current_role == role:
            payload.pop(field, None)

    bindings = _chain(tmp_path, payload_mutator=mutate)
    with pytest.raises(ValueError):
        freeze_upstream_authority_role_contract(bindings)


def test_nonfresh_canary_keeps_explicit_all_success_policy(
    tmp_path: Path,
) -> None:
    upstream = _seal(
        tmp_path / "upstream",
        payload_file="report.json",
        payload={"schema_version": "fixture", "status": "passed"},
        run_exit=0,
    )
    source = _seal(
        tmp_path / "source",
        payload_file="report.json",
        payload={"schema_version": "fixture", "status": "passed"},
        run_exit=0,
    )
    preopen = {
        "upstream_bindings": {"upstream": _binding(upstream)},
        "source_fixture_bindings": {"source": _binding(source)},
    }
    _verify_execution_upstream_authorities(
        preopen=preopen,
        split=NONFRESH_CANARY_SPLIT,
    )
    _verify_execution_upstream_authorities_independent(
        preopen=preopen,
        split=NONFRESH_CANARY_SPLIT,
    )

    failed = _seal(
        tmp_path / "failed",
        payload_file="report.json",
        payload={"schema_version": "fixture", "status": "failed"},
        run_exit=1,
    )
    preopen["source_fixture_bindings"]["source"] = _binding(failed)
    with pytest.raises(ValueError, match="did not pass"):
        _verify_execution_upstream_authorities(
            preopen=preopen,
            split=NONFRESH_CANARY_SPLIT,
        )
    with pytest.raises(ValueError, match="failed"):
        _verify_execution_upstream_authorities_independent(
            preopen=preopen,
            split=NONFRESH_CANARY_SPLIT,
        )


def test_evaluators_select_only_calibration_freeze_not_blanket_upstreams(
    tmp_path: Path,
) -> None:
    calibration = {
        "path": str((tmp_path / "calibration").resolve()),
        "root_sha256": "a" * 64,
    }
    preopen = {
        "upstream_bindings": {
            "calibration_freeze": calibration,
            "calibration_raw": {
                "path": str((tmp_path / "failed-raw").resolve()),
                "root_sha256": "b" * 64,
            },
        }
    }
    assert _calibration_freeze_binding(preopen) == calibration
    assert _calibration_freeze_binding_independent(preopen) == calibration

    for changed in (
        {"upstream_bindings": {}},
        {
            "upstream_bindings": {
                "calibration_freeze": {
                    "path": "relative",
                    "root_sha256": "a" * 64,
                }
            }
        },
        {
            "upstream_bindings": {
                "calibration_freeze": {
                    "path": calibration["path"],
                    "root_sha256": True,
                }
            }
        },
    ):
        with pytest.raises(ValueError):
            _calibration_freeze_binding(changed)
        with pytest.raises(ValueError):
            _calibration_freeze_binding_independent(changed)


def test_runner_qualification_reports_zero_exposure_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "execution"
    release = {
        "implementation_source_head": "1" * 40,
        "pointer_head_at_release": "2" * 40,
        "fixed_dp_head": "3" * 40,
        "critical_implementation_manifest_sha256": "4" * 64,
        "preopen_authority": {
            "path": str((tmp_path / "preopen").resolve()),
            "root_sha256": "5" * 64,
        },
        "preopen_review": {
            "path": str((tmp_path / "preopen-review").resolve()),
            "root_sha256": "6" * 64,
        },
        "holdout_identity": {
            "holdout_identity_sha256": "7" * 64,
            "execution_plan_sha256": "a" * 64,
        },
        "experiment_protocol": {"experiment_protocol_sha256": "8" * 64},
    }
    qualified = {
        "release": release,
        "preopen": {
            "upstream_authority_role_contract": {
                "contract_sha256": "9" * 64,
            }
        },
        "plan": {"execution_plan_sha256": "a" * 64},
        "output": output.resolve(),
        "operational_attempt_preexisting": False,
        "operational_identity_preexisting": False,
        "scientific_ledger_preexisting": False,
        "operational_availability": {
            "new_attempt_allowed": True,
            "prior_pre_exposure_failure": None,
        },
    }
    monkeypatch.setattr(
        holdout_runner,
        "_qualify_inputs",
        lambda **_kwargs: qualified,
    )
    result = holdout_runner.qualify(
        probe_template=tmp_path / "probe.json",
        probe_template_sha256="b" * 64,
        controller_decision_artifact=tmp_path / "controller",
        controller_decision_root_sha256="c" * 64,
        opening_release_artifact=tmp_path / "release",
        opening_release_root_sha256="d" * 64,
        dp_repo=tmp_path / "dp",
        output_dir=output,
        device="cuda",
    )
    assert result["status"] == (
        "passed_no_side_effect_holdout_runner_qualification"
    )
    for field in (
        "operational_attempt_created",
        "operational_identity_created",
        "scientific_ledger_created",
        "authorized_output_created",
        "model_loaded",
        "dp_loaded",
        "simulator_loaded",
        "forward_executed",
        "fresh_opened",
    ):
        assert result[field] is False
    assert result["outcome_fields_consumed"] == []
    assert result["pre_exposure_operational_availability"] == {
        "new_attempt_allowed": True,
        "prior_pre_exposure_failure": None,
    }
    assert not output.exists()
