"""Regression gate for the HALCON operator disposition map (dispositions.py).

The disposition map is the project's honest-disclosure ledger: every one of the
2313 real HALCON operators gets a truthful status. The classifier used a naive
`substr in name` test that produced *false* "needs a trained model" labels — most
egregiously "pose", which flagged transpose / compose / decompose and every
pose-tuple / quaternion / hom-mat *algebra* op as a trained model. These tests
lock the honest behaviour: pure algebra/plumbing is never called a model, genuine
learned/proprietary ops still are, and classical 3D geometry is named honestly.
"""
from __future__ import annotations

import dispositions as D

# Algebra / plumbing ops the old "pose"/"bundle" substrings falsely flagged as
# "needs a trained model". None of these involves any training whatsoever.
NOT_MODEL_NAMES = [
    "transpose_matrix", "transpose_matrix_mod", "decompose_matrix",
    "orthogonal_decompose_matrix", "compose3", "compose7", "decompose4",
    "compose_funct_1d", "pose_average", "pose_compose", "pose_invert",
    "vector_to_pose", "pose_to_hom_mat3d", "quat_compose", "dual_quat_compose",
    "hom_mat2d_compose", "hom_mat3d_transpose", "convert_pose_type",
    "get_circle_pose", "read_pose", "write_pose", "serialize_pose",
    "bundle_adjust_mosaic",
]

# Genuinely learned / proprietary ops that MUST stay flagged as models.
MODEL_NAMES = [
    "classify_image_class_gmm", "classify_image_class_svm",
    "classify_image_class_mlp", "classify_image_class_knn",
    "do_ocr_single", "do_ocr_multi_class_mlp", "create_deep_counting_model",
    "train_dl_model_batch", "read_ocr_class_svm",
]

# Classical 3D/stereo/calibration geometry: out of scope (no parity op), but they
# are NOT trained models — the honest reason must say so.
GEOMETRIC_NAMES = ["binocular_disparity", "photometric_stereo", "camera_calibration"]

VALID_STATUS = {
    "implemented", "needs_new_capability", "nary_multiinput",
    "out_of_scope_model", "out_of_scope_plumbing",
}


def test_is_model_name_ignores_algebra_and_plumbing():
    for name in NOT_MODEL_NAMES:
        assert not D._is_model_name(name), f"{name} wrongly flagged as a model by name"


def test_is_model_name_catches_learned_ops():
    for name in MODEL_NAMES:
        assert D._is_model_name(name), f"{name} should be flagged as a model by name"


def test_pose_is_not_a_model_token():
    # The exact bug: "pose" as a raw substring caught transpose/compose/decompose.
    assert not D._is_model_name("transpose_matrix")
    assert not D._is_model_name("compose5")
    assert not D._is_model_name("decompose_matrix")
    # ...and a bare pose op is classical algebra, never a model.
    assert not D._is_model_name("pose_average")


def _disp_map():
    return D.build()["dispositions"]


def test_every_operator_has_a_truthful_status():
    out = D.build()
    assert out["n_total"] == out["n_dispositioned"] == 2313
    for name, v in out["dispositions"].items():
        assert v["status"] in VALID_STATUS, f"{name}: bad status {v['status']}"
        assert v["reason"], f"{name}: empty reason"


def test_algebra_and_plumbing_never_labeled_model():
    disp = _disp_map()
    for name in NOT_MODEL_NAMES:
        assert name in disp, f"{name} missing from graph — check name"
        assert disp[name]["status"] != "out_of_scope_model", (
            f"{name} is algebra/plumbing but labeled a trained-model op")


def test_genuine_model_ops_stay_model():
    disp = _disp_map()
    for name in MODEL_NAMES:
        if name in disp:  # some names are version-specific; skip if absent
            assert disp[name]["status"] == "out_of_scope_model", (
                f"{name} should remain out_of_scope_model")


def test_classical_geometry_reason_is_honest():
    disp = _disp_map()
    for name in GEOMETRIC_NAMES:
        assert disp[name]["status"] == "out_of_scope_model"
        reason = disp[name]["reason"]
        assert "classical 3D" in reason, f"{name}: reason should not claim a trained model"
        assert "trained model" not in reason, f"{name}: classical geometry is not a trained model"


def test_pure_algebra_chapters_never_model():
    """Ops living ONLY in pure-algebra chapters (Transformations / Matrix) — pose,
    quaternion, hom-mat, transpose, (de)compose algebra — must never be labeled as
    needing a trained model. This is the clean invariant the old "pose" substring
    violated (it flagged 47 such algebra ops as models)."""
    import json
    import os
    with open(os.path.join(D.HERE, "data", "halcon_graph.json"), encoding="utf-8") as f:
        graph = json.load(f)
    nodes = graph["nodes"]
    disp = _disp_map()
    PURE_ALGEBRA_CH = {"Transformations", "Matrix"}
    offenders = [
        name for name, v in disp.items()
        if v["status"] == "out_of_scope_model"
        and (chs := set(nodes[name].get("chapters") or [])) and chs <= PURE_ALGEBRA_CH
    ]
    assert not offenders, f"pure-algebra ops mislabeled as trained models: {offenders}"
