"""Wave-0 safety gate — proves the evolutionary north-star is UNCHANGED.

These three additive Wave-0 changes must never move the current evolutionary
behavior in this (all-backends-installed) environment:

  (1) stable op slots + name-pinned champion records (ops.SLOTS / pipeline_stages
      / decode_by_names) — index-based decode() left byte-identical,
  (2) a third LOCKED holdout in evolve.run, evaluated exactly once, selection
      unchanged (train-only),
  (3) Problem.from_pairs — real (input, target) frames can drive evolution.

The gate: a fixed set of genomes must decode to the SAME pipeline_str across every
start sort, and the denoise/edge champions must score IDENTICALLY, versus values
captured from the PRE-CHANGE code (embedded below as PINS). The strict pins are
guarded by a registry fingerprint: on an install with a different backend set the
candidate counts differ, so the index-based pins are skipped (honestly — they are
install-specific) while the install-independent invariants still run.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

import evolve
import ops
import problems

# Captured from the pre-change code in the all-backends environment (see
# scratchpad/snap_before.json). If these ever change, an "additive" edit silently
# altered decode/selection — the gate has caught a north-star regression.
PINS = json.loads(r"""
{"cand_counts": {"image": 378, "region": 96, "feature": 1, "contour": 30, "match": 1, "volume": 9, "any": 1},
 "genomes": [[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
             [1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0],
             [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5],
             [0.0,0.058823529411764705,0.11764705882352941,0.17647058823529413,0.23529411764705882,
              0.29411764705882354,0.35294117647058826,0.4117647058823529,0.47058823529411764,
              0.5294117647058824,0.5882352941176471,0.6470588235294118,0.7058823529411765,
              0.7647058823529411,0.8235294117647058,0.8823529411764706,0.9411764705882353,1.0],
             [0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,
              0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999,0.999999]],
 "pins": [
   {"image":"identity","region":"identity","feature":"identity","contour":"identity","match":"identity","volume":"identity","any":"identity"},
   {"image":"xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00)",
    "region":"xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00)",
    "feature":"identity","contour":"contour_point_num_xld(a=1.00,b=1.00)","match":"identity",
    "volume":"vol_count(a=1.00,b=1.00)","any":"identity"},
   {"image":"h_threshold(a=0.50,b=0.50) -> eccentricity(a=0.50,b=0.50)","region":"eccentricity(a=0.50,b=0.50)",
    "feature":"identity",
    "contour":"close_contours_xld(a=0.50,b=0.50) -> close_contours_xld(a=0.50,b=0.50) -> close_contours_xld(a=0.50,b=0.50) -> close_contours_xld(a=0.50,b=0.50) -> close_contours_xld(a=0.50,b=0.50) -> close_contours_xld(a=0.50,b=0.50)",
    "match":"identity",
    "volume":"vol_dilate(a=0.50,b=0.50) -> vol_dilate(a=0.50,b=0.50) -> vol_dilate(a=0.50,b=0.50) -> vol_dilate(a=0.50,b=0.50) -> vol_dilate(a=0.50,b=0.50) -> vol_dilate(a=0.50,b=0.50)",
    "any":"identity"},
   {"image":"sk_lbp(a=0.24,b=0.29) -> mean_image(a=0.41,b=0.47) -> local_max(a=0.59,b=0.65) -> get_region_thickness(a=0.76,b=0.82)",
    "region":"sk_medial(a=0.24,b=0.29) -> closing_rectangle1(a=0.41,b=0.47) -> roundness(a=0.59,b=0.65)",
    "feature":"identity","contour":"count_contours(a=0.24,b=0.29)","match":"identity",
    "volume":"vol_gaussian(a=0.24,b=0.29) -> vol_erode(a=0.41,b=0.47) -> vol_dilate(a=0.59,b=0.65) -> vol_mip(a=0.76,b=0.82) -> xsitk_curv_aniso_diff(a=0.94,b=1.00)",
    "any":"identity"},
   {"image":"xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00) -> xkor_dog(a=1.00,b=1.00)",
    "region":"xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00) -> xsk3_rank_majority(a=1.00,b=1.00)",
    "feature":"identity","contour":"contour_point_num_xld(a=1.00,b=1.00)","match":"identity",
    "volume":"vol_count(a=1.00,b=1.00)","any":"identity"}],
 "denoise": {"pipeline":"xkor_gaussian(a=0.36,b=0.32) -> sk_blur_effect(a=0.64,b=0.20)","train":13.0059,"holdout":13.3463},
 "edge": {"pipeline":"xpil_autocontrast(a=0.78,b=0.61) -> xsp_savgol(a=0.35,b=0.60) -> cos_image(a=0.97,b=0.45) -> gray_range_rect(a=0.68,b=0.00) -> xpil_smooth_more(a=0.57,b=0.22) -> gray_erosion_shape(a=0.66,b=0.73)","train":0.6302,"holdout":0.5235}}
""")

SORTS = ["image", "region", "feature", "contour", "match", "volume", "any"]

# The index-based pins are only valid for the exact backend set they were captured
# on. Fingerprint the registry so a different install skips them cleanly.
_FINGERPRINT_OK = all(len(ops._candidates(s)) == PINS["cand_counts"][s] for s in SORTS)
_skip_install = pytest.mark.skipif(
    not _FINGERPRINT_OK,
    reason="registry candidate counts differ from the pinned all-backends install; "
           "index-based pins are install-specific (name-pinned invariants still run)")


# --------------------------------------------------------------------------- #
# Install-independent invariants (always run).                                #
# --------------------------------------------------------------------------- #
def test_slots_are_registration_order():
    """SLOTS freezes each op's registration-order index. A handful of names occur
    twice (core + a backend override); like RT/_BY_NAME, SLOTS resolves a name to
    its LAST (canonical) occurrence — the exact op that actually executes. And
    _candidates(sort) is the registration-order filter of REGISTRY (object order
    preserved), which is what decode() indexes into."""
    assert ops.SLOTS == {op.name: i for i, op in enumerate(ops.REGISTRY)}
    # SLOTS points at the canonical op the name resolves to (matches _BY_NAME/RT).
    for name, i in ops.SLOTS.items():
        assert ops.REGISTRY[i].name == name
        assert ops._BY_NAME[name] is ops.REGISTRY[i]
    # _candidates preserves REGISTRY order (deterministic within an install).
    for sort in SORTS:
        expected = [op for op in ops.REGISTRY if op.in_sort in (sort, ops.ANY)]
        assert ops._candidates(sort) == expected


def test_decode_is_deterministic_across_sorts():
    """A fixed genome decodes to byte-identical stages on repeat — the property
    the holdout scoring's reproducibility rests on."""
    for g in PINS["genomes"]:
        for sort in SORTS:
            s1 = [(s.op, s.a, s.b, s.sort) for s in ops.decode(g, sort)]
            s2 = [(s.op, s.a, s.b, s.sort) for s in ops.decode(g, sort)]
            assert s1 == s2


def test_decode_by_names_roundtrip_reconstructs_pipeline():
    """pipeline_stages() -> decode_by_names() rebuilds the exact same pipeline
    (name-pinned, index-independent) and runs to identical output."""
    img = np.clip(np.random.default_rng(1).random((32, 32)), 0, 1)
    for g in PINS["genomes"]:
        specs = ops.pipeline_stages(g, "image")
        rebuilt = ops.decode_by_names(specs)
        # same string form as the index-based decode (identity dropped)
        assert ops.stages_str(rebuilt) == ops.pipeline_str(g, "image")
        # and identical numeric result when executed
        a = ops.run_genome(g, img, "image")
        b = ops.run_stages(rebuilt, img)
        assert np.array_equal(np.asarray(a, np.float64), np.asarray(b, np.float64))


# --------------------------------------------------------------------------- #
# Strict pins (guarded by the all-backends fingerprint).                      #
# --------------------------------------------------------------------------- #
@_skip_install
def test_pipeline_str_pinned_for_fixed_genomes_and_sorts():
    """>=5 fixed genomes x every start sort: pipeline_str is byte-identical to the
    pre-change capture. This is the decode-did-not-move gate."""
    assert len(PINS["genomes"]) >= 5
    for g, pin in zip(PINS["genomes"], PINS["pins"]):
        for sort in SORTS:
            assert ops.pipeline_str(g, sort) == pin[sort], f"decode moved for sort {sort}"


# --------------------------------------------------------------------------- #
# North-star champions (evolve once, reuse).                                  #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def denoise_champ(tmp_path_factory):
    wd = tmp_path_factory.mktemp("wave0_denoise")
    return evolve.run("denoise", workdir=str(wd), gens=8, pop=12, seed=0, verbose=False)


@pytest.fixture(scope="module")
def edge_champ(tmp_path_factory):
    wd = tmp_path_factory.mktemp("wave0_edge")
    return evolve.run("edge", workdir=str(wd), gens=8, pop=12, seed=4, verbose=False)


@_skip_install
def test_north_star_denoise_champion_unchanged(denoise_champ):
    assert denoise_champ["pipeline"] == PINS["denoise"]["pipeline"]
    assert denoise_champ["train"] == PINS["denoise"]["train"]
    assert denoise_champ["holdout"] == PINS["denoise"]["holdout"]


@_skip_install
def test_north_star_edge_champion_unchanged(edge_champ):
    assert edge_champ["pipeline"] == PINS["edge"]["pipeline"]
    assert edge_champ["train"] == PINS["edge"]["train"]
    assert edge_champ["holdout"] == PINS["edge"]["holdout"]


# --------------------------------------------------------------------------- #
# (1) name-pinned champion record round-trips.                                #
# --------------------------------------------------------------------------- #
def test_champion_carries_name_pinned_record_and_roundtrips(denoise_champ):
    assert "pipeline_stages" in denoise_champ and denoise_champ["pipeline_stages"]
    rebuilt = ops.decode_by_names(denoise_champ["pipeline_stages"])
    assert ops.stages_str(rebuilt) == denoise_champ["pipeline"]
    # executes to the same result as the index-based genome decode
    img = np.clip(np.random.default_rng(2).random((48, 48)), 0, 1)
    g = np.asarray(denoise_champ["genome"], np.float64)
    assert np.array_equal(ops.run_genome(g, img, "image"), ops.run_stages(rebuilt, img))


# --------------------------------------------------------------------------- #
# (2) locked holdout evaluated exactly once; selection unchanged.             #
# --------------------------------------------------------------------------- #
def test_locked_holdout_is_recorded_and_recomputable(denoise_champ):
    assert "locked_holdout" in denoise_champ
    # It must equal a fresh score on the seed+20000 split — proof it is a real
    # single evaluation of that third split, recorded once.
    prob = problems.PROBLEMS["denoise"]
    cfg = denoise_champ["config"]
    n_locked = cfg.get("n_locked", cfg["n_holdout"])
    locked = prob.make(n_locked, cfg["size"], cfg["seed"] + 20_000)
    recomputed = round(prob.score(np.asarray(denoise_champ["genome"], np.float64), locked), 4)
    assert recomputed == denoise_champ["locked_holdout"]


def test_locked_split_is_distinct_from_train_and_holdout():
    prob = problems.PROBLEMS["denoise"]
    tr = prob.make(14, 64, 0)
    ho = prob.make(8, 64, 10_000)
    lk = prob.make(8, 64, 20_000)
    assert not np.array_equal(lk["input"], tr["input"][: lk["input"].shape[0]])
    assert not np.array_equal(lk["input"], ho["input"])


@_skip_install
def test_adding_locked_split_did_not_move_selection(denoise_champ):
    """Selection stays train-only: the champion train score is unchanged versus
    the pinned pre-change value even though a third split was added."""
    assert denoise_champ["train"] == PINS["denoise"]["train"]


# --------------------------------------------------------------------------- #
# (3) Problem.from_pairs — real frames drive evolution.                       #
# --------------------------------------------------------------------------- #
def test_from_pairs_make_score_and_evolve_accepts_it(tmp_path):
    rng = np.random.default_rng(7)
    clean = np.stack([np.clip(rng.random((32, 32)), 0, 1) for _ in range(6)])
    noisy = np.clip(clean + rng.normal(0, 0.15, clean.shape), 0, 1)
    prob = problems.Problem.from_pairs(noisy, clean, name="realpairs", unit="dB PSNR")

    # make/score work
    data = prob.make(4, 0, 0)
    assert data["input"].shape[0] == 4 and data["items"].shape[0] == 4
    g = rng.random(ops.GENOME_LEN)
    assert isinstance(prob.score(g, data), float)

    # evolve.run accepts a Problem instance (not just a registered name)
    champ = evolve.run(prob, workdir=str(tmp_path), gens=3, pop=6, seed=0, verbose=False)
    assert champ["problem"] == "realpairs"
    assert "pipeline_stages" in champ and "locked_holdout" in champ
    # reproducible given seed
    champ2 = evolve.run(prob, workdir=str(tmp_path / "b"), gens=3, pop=6, seed=0, verbose=False)
    assert champ["genome"] == champ2["genome"] and champ["train"] == champ2["train"]


def test_from_pairs_scalar_targets_and_default_metric(tmp_path):
    rng = np.random.default_rng(9)
    imgs = np.stack([np.clip(rng.random((24, 24)), 0, 1) for _ in range(4)])
    counts = np.array([1.0, 2.0, 3.0, 4.0])  # scalar targets -> 1/(1+err) default
    prob = problems.Problem.from_pairs(imgs, counts, name="cnt")
    data = prob.make(4, 0, 0)
    assert 0.0 <= prob.score(rng.random(ops.GENOME_LEN), data) <= 1.0


def test_from_pairs_rejects_empty_or_mismatched():
    with pytest.raises(ValueError):
        problems.Problem.from_pairs(np.zeros((0, 8, 8)), np.zeros((0, 8, 8)))
    with pytest.raises(ValueError):
        problems.Problem.from_pairs(np.zeros((3, 8, 8)), np.zeros((2, 8, 8)))
