from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v25_multiroute_review_recovery import (
    AUTHORITY_SHA256,
    SOURCE_ARTIFACTS,
    stage_authority_payload,
)
from camp_core.integrations.diffusion_planner_v25_multiroute_review_recovery_review import (
    review_stage_authority_literal,
)
from camp_core.integrations.diffusion_planner_v25_stage_orchestration import (
    execute_orchestration,
)


HEAD = "1" * 40


def _artifact(path: Path, label: str) -> str:
    path.mkdir()
    (path / "report.json").write_text(
        json.dumps({"label": label}, sort_keys=True) + "\n", encoding="utf-8"
    )
    return seal_artifact(path, label=label)


def _stub(path: Path) -> None:
    path.write_text(
        """
from pathlib import Path
import json
import sys
from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
mode=sys.argv[1]
marker=Path(sys.argv[2])
marker.write_text(mode,encoding="utf-8")
if mode.startswith("exit"):
    raise SystemExit(int(mode[4:]))
target=Path(sys.argv[3])
target.mkdir()
(target/"report.json").write_text(json.dumps({"status":"ok"})+"\\n",encoding="utf-8")
seal_artifact(target,label="stub")
""".lstrip(),
        encoding="utf-8",
    )


def _source_rows() -> list[dict]:
    return [
        {
            "role": role,
            "root_sha256": root,
            "schema_version": schema,
            "status": status,
        }
        for role, root, schema, status in SOURCE_ARTIFACTS
    ]


def test_producer_exit_17_prevents_reviewer_start(tmp_path: Path) -> None:
    stub = tmp_path / "stub.py"
    _stub(stub)
    producer_marker = tmp_path / "producer.marker"
    reviewer_marker = tmp_path / "reviewer.marker"
    root, result = execute_orchestration(
        output=tmp_path / "operation",
        mode="producer-and-reviewer",
        implementation_head=HEAD,
        authority_sha256=AUTHORITY_SHA256,
        expected_interpreter=sys.executable,
        cwd=tmp_path,
        source_dir=None,
        source_root=None,
        producer_command=[sys.executable, str(stub), "exit17", str(producer_marker)],
        producer_target_dir=tmp_path / "producer-artifact",
        reviewer_command=[sys.executable, str(stub), "success", str(reviewer_marker), str(tmp_path / "review-artifact")],
        reviewer_target_dir=tmp_path / "review-artifact",
    )
    assert len(root) == 64
    assert result["overall_exit_code"] == 17
    assert result["reviewer_started"] is False
    assert producer_marker.exists()
    assert not reviewer_marker.exists()


def test_reviewer_exit_23_is_overall_exit_23(tmp_path: Path) -> None:
    stub = tmp_path / "stub.py"
    _stub(stub)
    source_dir = tmp_path / "source"
    source_root = _artifact(source_dir, "source")
    reviewer_marker = tmp_path / "reviewer.marker"
    _, result = execute_orchestration(
        output=tmp_path / "operation",
        mode="review-only",
        implementation_head=HEAD,
        authority_sha256=AUTHORITY_SHA256,
        expected_interpreter=sys.executable,
        cwd=tmp_path,
        source_dir=source_dir,
        source_root=source_root,
        producer_command=None,
        producer_target_dir=None,
        reviewer_command=[sys.executable, str(stub), "exit23", str(reviewer_marker), "__SOURCE_ROOT__"],
        reviewer_target_dir=tmp_path / "review-artifact",
    )
    assert result["producer_skipped_reuse_sealed"] is True
    assert result["reviewer_started"] is True
    assert result["overall_exit_code"] == 23


def test_both_success_machine_root_matches_target_receipt(tmp_path: Path) -> None:
    stub = tmp_path / "stub.py"
    _stub(stub)
    source_dir = tmp_path / "source"
    source_root = _artifact(source_dir, "source")
    target = tmp_path / "review-artifact"
    operation = tmp_path / "operation"
    _, result = execute_orchestration(
        output=operation,
        mode="review-only",
        implementation_head=HEAD,
        authority_sha256=AUTHORITY_SHA256,
        expected_interpreter=sys.executable,
        cwd=tmp_path,
        source_dir=source_dir,
        source_root=source_root,
        producer_command=None,
        producer_target_dir=None,
        reviewer_command=[sys.executable, str(stub), "success", str(tmp_path / "reviewer.marker"), str(target), "__SOURCE_ROOT__"],
        reviewer_target_dir=target,
    )
    target_root = (target / "ROOT_SHA256SUMS").read_text().split()[0]
    assert result["overall_exit_code"] == 0
    assert result["reviewer_root_sha256"] == target_root
    assert (operation / "target_root.txt").read_text() == f"{target_root}\n"


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.__setitem__("evaluation_root_sha256", "0" * 64),
        lambda value: value.__setitem__("implementation_head", "2" * 40),
        lambda value: value.__setitem__(
            "correction_continuation", "0" * 64
        ),
        lambda value: value["exact_dirs"].__setitem__(
            "evaluation_review", "/root/autodl-tmp/drifted"
        ),
    ),
)
def test_critical_root_head_continuation_and_exact_dir_mutations_fail(
    mutation,
) -> None:
    value = stage_authority_payload(HEAD, _source_rows())
    assert review_stage_authority_literal(value) == value
    changed = copy.deepcopy(value)
    mutation(changed)
    with pytest.raises(ValueError):
        review_stage_authority_literal(changed)
