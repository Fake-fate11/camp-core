import json
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    CAMPDPRerankingPipeline,
    CAMPReranker,
    V26_CAMP_ATOM_NAMES,
    V26_DP_MASKED_TOKEN_TYPES,
    build_camp_atom_artifact,
    masked_mean_scene_embedding,
)


def _patterns():
    for value in range(24):
        pattern = ["observed"] * len(V26_CAMP_ATOM_NAMES)
        for bit in range(5):
            if value & (1 << bit):
                pattern[bit] = "not_applicable"
        yield tuple(pattern)


def _checkpoint(path, *, scene):
    arrays = {}
    for index, pattern in enumerate(_patterns()):
        active = tuple(i for i, status in enumerate(pattern) if status == "observed")
        width = 257 if scene else 2
        theta = np.zeros((len(active), width), dtype=np.float64)
        if active:
            theta[0, -1] = 1.0
            if scene and len(active) > 1:
                theta[1, 0] = 0.5
        suffix = f"{index:03d}"
        arrays[f"theta_{suffix}"] = theta
        arrays[f"active_global_indices_{suffix}"] = np.asarray(active, dtype=np.int64)
        arrays[f"status_pattern_{suffix}"] = np.asarray(pattern, dtype="U32")
    np.savez(path, **arrays)
    return path


def _scales(path):
    path.write_text(
        json.dumps(
            {
                "global_atom_names": list(V26_CAMP_ATOM_NAMES),
                "atom_rows": [
                    {"atom_name": name, "scale": 2.0}
                    for name in V26_CAMP_ATOM_NAMES
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _artifact(raw=None):
    if raw is None:
        raw = np.zeros((8, len(V26_CAMP_ATOM_NAMES)), dtype=np.float64)
    return {
        "bank_atom_names": list(V26_CAMP_ATOM_NAMES),
        "atom_states": [
            {"name": name, "status": "observed"} for name in V26_CAMP_ATOM_NAMES
        ],
        "observed_atom_names": list(V26_CAMP_ATOM_NAMES),
        "observed_global_atom_indices": list(range(len(V26_CAMP_ATOM_NAMES))),
        "candidate_atoms_raw": raw,
    }


def test_fixed_camp_reranks_and_returns_unchanged_candidate(tmp_path):
    checkpoint = _checkpoint(tmp_path / "fixed.npz", scene=False)
    reranker = CAMPReranker(checkpoint, _scales(tmp_path / "scales.json"))
    raw = np.zeros((8, len(V26_CAMP_ATOM_NAMES)), dtype=np.float64)
    raw[:, 0] = np.asarray([4.0, 2.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0])
    candidates = np.arange(8 * 80 * 4, dtype=np.float64).reshape(8, 80, 4)

    selected, result = reranker.select_candidates(candidates, _artifact(raw))

    assert reranker.model_kind == "fixed"
    assert result.selected_row == 1
    np.testing.assert_array_equal(selected, candidates[1])
    np.testing.assert_allclose(result.candidate_scores, raw[:, 0] / 2.0)
    assert result.continuous_scene_representation_read is False


def test_atom_builder_keeps_missing_endpoints_out_of_numeric_matrix():
    statuses = {name: "observed" for name in V26_CAMP_ATOM_NAMES}
    statuses[V26_CAMP_ATOM_NAMES[3]] = "typed_missing"
    statuses[V26_CAMP_ATOM_NAMES[6]] = "not_applicable"
    values = {
        name: np.arange(8, dtype=np.float64)
        for name, status in statuses.items()
        if status == "observed"
    }

    artifact = build_camp_atom_artifact(values, statuses)

    assert artifact["candidate_atoms_raw"].shape == (8, 14)
    assert V26_CAMP_ATOM_NAMES[3] not in artifact["observed_atom_names"]
    assert V26_CAMP_ATOM_NAMES[6] not in artifact["observed_atom_names"]


def test_scene_camp_uses_masked_mean256_and_lowest_row_tie_break(tmp_path):
    checkpoint = _checkpoint(tmp_path / "scene.npz", scene=True)
    reranker = CAMPReranker(checkpoint, _scales(tmp_path / "scales.json"))
    tokens = np.vstack(
        (np.zeros((1, 256), dtype=np.float64), np.full((1, 256), 2.0))
    )
    masks = {
        name: np.asarray([[name != V26_DP_MASKED_TOKEN_TYPES[-1]]], dtype=bool)
        for name in V26_DP_MASKED_TOKEN_TYPES
    }
    masks[V26_DP_MASKED_TOKEN_TYPES[-2]] = np.asarray([[False]], dtype=bool)
    tokens = np.vstack((np.zeros((8, 256)), tokens))
    embedding = masked_mean_scene_embedding(tokens, masks)
    np.testing.assert_allclose(embedding, np.ones(256))

    result = reranker.rerank_artifact(_artifact(), embedding)

    assert reranker.model_kind == "scene"
    assert reranker.scene_embedding_dimension == 256
    assert result.selected_row == 0
    assert result.continuous_scene_representation_read is True


def test_pipeline_directory_loads_final_bundle_names(tmp_path):
    _checkpoint(tmp_path / "fixed_weight_camp.npz", scene=False)
    _checkpoint(tmp_path / "scene_conditioned_camp.npz", scene=True)
    _scales(tmp_path / "atom_scales.json")
    pipeline = CAMPDPRerankingPipeline.from_directory(tmp_path)
    candidates = np.zeros((8, 80, 4), dtype=np.float64)

    selected, result = pipeline.select(
        mode="fixed",
        candidates=candidates,
        artifact=_artifact(),
    )

    assert result.selected_row == 0
    np.testing.assert_array_equal(selected, candidates[0])


def test_checked_in_50k_bundle_loads():
    root = Path(__file__).resolve().parents[2]
    pipeline = CAMPDPRerankingPipeline.from_directory(
        root / "artifacts" / "camp_v26_k8_50k"
    )

    assert pipeline.fixed.model_kind == "fixed"
    assert pipeline.scene.model_kind == "scene"
    assert pipeline.scene.scene_embedding_dimension == 256
    fixed = pipeline.fixed.rerank_artifact(_artifact())
    scene = pipeline.scene.rerank_artifact(_artifact(), np.zeros(256))
    assert fixed.selected_row == 0
    assert scene.selected_row == 0
    assert np.all(np.isfinite(fixed.active_weights))
    assert np.all(np.isfinite(scene.active_weights))
