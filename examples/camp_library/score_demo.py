"""Score synthetic atoms without training, downloading data, or changing weights.

This is an API example, not a physical driving scenario or an evaluation result.
Run after installing camp_core from the repository root.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from camp_core import dp
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    V26_CAMP_ATOM_NAMES,
    build_camp_atom_artifact,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle", type=Path,
        default=Path(__file__).resolve().parents[2] / "artifacts/camp_v26_k8_50k",
    )
    args = parser.parse_args()

    selector = dp.load(args.bundle)
    candidate_count = 8
    raw_values = np.arange(candidate_count, dtype=np.float64)[::-1]
    atoms = build_camp_atom_artifact(
        {name: raw_values.copy() for name in V26_CAMP_ATOM_NAMES},
        {name: "observed" for name in V26_CAMP_ATOM_NAMES},
    )
    # Distinct payloads make unchanged-row selection visible. These arrays are
    # deliberately only API fixtures; no dynamics or outcome metric is claimed.
    candidates = np.arange(candidate_count * 80 * 4).reshape(candidate_count, 80, 4)
    selected, result = selector.pipeline.fixed.select_candidates(candidates, atoms, None)
    np.testing.assert_array_equal(selected, candidates[result.selected_row])
    print(json.dumps({
        "example": "synthetic_atom_scoring_only",
        "candidate_count": candidate_count,
        "selected_row": int(result.selected_row),
        "candidate_scores": result.candidate_scores.tolist(),
        "selected_candidate_unchanged": True,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
