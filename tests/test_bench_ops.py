# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ベンチ harness(tools/bench_ops.py)の契約テスト。

harness そのものが壊れると、以降の高速化がすべて「測れているつもり」になる。
ここで固定するのは **測定値の大小ではなく harness の契約**(実行時間や Mpx/s は
熱状態で 1.7 倍動くので、絶対値は一切 assert しない — docs/design/
PERF_MEMORY_VIDEO_SURVEY.md §5.1):

  1. 3 op × 64² × repeat 1 のスモークが走り、行に必要な列が全部載る(5 s 未満)。
  2. ベースライン比較が **2 倍の合成退行を検出**し、同値なら通る(境界も固定)。
  3. 未知の op 名は **近い名前を挙げて例外**(fail-closed。黙って 0 件にしない)。
  4. 入力に **ノイズ画像が必ず在る**(median/percentile は内容で 10 倍変わるので、
     ノイズ無しだけで測ると最悪側を見逃す)。CLI もノイズ抜きの --images を拒否する。
"""
from __future__ import annotations

import copy
import json
import time

import numpy as np
import pytest

pytest.importorskip("scipy")

from tools import bench_ops as B

SMOKE_OPS = ["gaussian", "threshold", "invert"]
SIZE64 = [(64, 64, "64")]


@pytest.fixture(scope="module")
def smoke_report():
    """3 op × 64² × repeat 1 の実 run。5 s 未満で終わることも契約(CI で毎回回すため)。"""
    t0 = time.perf_counter()
    rep = B.run(SMOKE_OPS, SIZE64, ["float64"], ["noisy"], warm=1, repeat=1, verbose=False)
    rep["_wall_s"] = time.perf_counter() - t0
    return rep


# --------------------------------------------------------------------------- #
# 1. スモーク                                                                   #
# --------------------------------------------------------------------------- #
def test_smoke_run_measures_every_op(smoke_report):
    rows = smoke_report["rows"]
    assert len(rows) == len(SMOKE_OPS)
    assert [r["name"] for r in rows] == SMOKE_OPS
    assert smoke_report["summary"]["errors"] == 0, [r.get("error") for r in rows]
    assert smoke_report["summary"]["measured"] == len(SMOKE_OPS)


def test_smoke_run_is_fast_enough_for_ci(smoke_report):
    """< 5 s。遅くなったら harness が重くなった合図(op が遅いのとは別問題)。"""
    assert smoke_report["_wall_s"] < 5.0, "smoke took %.2f s" % smoke_report["_wall_s"]


def test_row_carries_the_full_contract_record(smoke_report):
    """1 行に「速度」だけでなく「メモリ」と「契約」が載る(速いが壊れているを検出するため)。"""
    for r in smoke_report["rows"]:
        for field in ("key", "name", "size", "dtype", "image", "ms", "mpx_s",
                      "tm_peak_x", "rss_peak_x", "out_dtype", "out_shape",
                      "fallbacks", "input_mutated", "shares_mem", "module"):
            assert field in r, "%s missing %r" % (r["name"], field)
        assert r["ms"] > 0.0
        assert r["fallbacks"] == 0, (r["name"], r["fallback_msg"])
        assert r["input_mutated"] is False, "%s mutated its input" % r["name"]
        assert r["out_shape"] == [64, 64]


def test_header_is_honest_about_the_thermal_caveat(smoke_report):
    h = smoke_report["header"]
    assert h["warm"] == 1 and h["repeat"] == 1 and h["device"] == "cpu"
    assert {"python", "numpy", "scipy", "cv2"} <= set(h["versions"])
    assert h["cpu"] and h["date"] and h["platform"]
    assert "thermally steady" in h["caveat"]


def test_row_key_is_a_stable_string():
    assert B.row_key("gaussian", "2048", "float64") == "gaussian|2048|float64"
    assert B.row_key("gaussian", "2048", "float64", "noisy") == "gaussian|2048|float64"
    # 既定でない画像種だけが 4 番目の成分を足す = 既定キーは画像種を増やしても不変
    assert B.row_key("median", "2048", "float64", "quantised") == "median|2048|float64|quantised"


# --------------------------------------------------------------------------- #
# 2. ベースライン比較                                                           #
# --------------------------------------------------------------------------- #
def _baseline_of(report):
    return B.baseline_from(report)["metrics"]


def test_baseline_passes_when_identical(smoke_report):
    base = _baseline_of(smoke_report)
    cmp_ = B.compare_baseline(smoke_report, base, tolerance=0.30)
    assert cmp_["compared"] == len(SMOKE_OPS)
    assert cmp_["regressions"] == []
    assert cmp_["missing"] == [] and cmp_["vanished"] == []


def test_baseline_detects_a_synthetic_2x_regression(smoke_report):
    """ベースラインの半分の時間 = 今回 2 倍遅い、を全行で検出する。"""
    base = _baseline_of(smoke_report)
    half = {k: dict(v, ms=v["ms"] / 2.0) for k, v in base.items()}
    cmp_ = B.compare_baseline(smoke_report, half, tolerance=0.30)
    assert len(cmp_["regressions"]) == len(SMOKE_OPS)
    for item in cmp_["regressions"]:
        assert item["ratio"] == pytest.approx(2.0, rel=1e-6)
    assert "REGRESSIONS" in B.format_comparison(cmp_)


def test_tolerance_gates_around_the_threshold(smoke_report):
    """許容幅の内側は通し、外側は落とす(30 % の幅が本当に効いていることを固定)。"""
    base = _baseline_of(smoke_report)
    inside = {k: dict(v, ms=v["ms"] / 1.25) for k, v in base.items()}      # 1.25x 遅い
    assert B.compare_baseline(smoke_report, inside, tolerance=0.30)["regressions"] == []
    outside = {k: dict(v, ms=v["ms"] / 1.40) for k, v in base.items()}     # 1.40x 遅い
    assert len(B.compare_baseline(smoke_report, outside, tolerance=0.30)["regressions"]) == len(SMOKE_OPS)
    # 幅を広げれば同じ 1.40x が通る = tolerance が実際に読まれている
    assert B.compare_baseline(smoke_report, outside, tolerance=0.50)["regressions"] == []


def test_baseline_reports_keys_that_vanished(smoke_report):
    """ベースラインに在って今回測れなかった行を数える(黙って「退行ゼロ」にしない)。"""
    base = dict(_baseline_of(smoke_report))
    base["ghost_op|64|float64"] = {"ms": 1.0, "mpx_s": 4.0, "tm_peak_x": 1.0,
                                   "out_dtype": "float64", "fallbacks": 0}
    cmp_ = B.compare_baseline(smoke_report, base, tolerance=0.30)
    assert cmp_["vanished"] == ["ghost_op|64|float64"]
    assert cmp_["regressions"] == []


def test_baseline_flags_a_changed_output_dtype(smoke_report):
    """速くなっても out dtype が変わったら別物 — 表に出す(uint8 で黙って壊れる系の見張り)。"""
    base = {k: dict(v, out_dtype="uint8") for k, v in _baseline_of(smoke_report).items()}
    cmp_ = B.compare_baseline(smoke_report, base, tolerance=0.30)
    assert len(cmp_["dtype_changed"]) == len(SMOKE_OPS)
    assert "OUTPUT DTYPE CHANGED" in B.format_comparison(cmp_)


def test_baseline_roundtrips_through_json(tmp_path, smoke_report):
    p = tmp_path / "baseline.json"
    p.write_text(json.dumps(B.baseline_from(smoke_report), default=str), encoding="utf-8")
    loaded = B.load_baseline(str(p))
    assert set(loaded) == {r["key"] for r in smoke_report["rows"]}
    assert B.compare_baseline(smoke_report, loaded, tolerance=0.30)["regressions"] == []
    # full report 形式(rows つき)も読める
    p2 = tmp_path / "report.json"
    p2.write_text(json.dumps(smoke_report, default=str), encoding="utf-8")
    assert set(B.load_baseline(str(p2))) == set(loaded)


def test_load_baseline_rejects_a_foreign_json(tmp_path):
    p = tmp_path / "not_a_baseline.json"
    p.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="not a bench_ops baseline"):
        B.load_baseline(str(p))


# --------------------------------------------------------------------------- #
# 3. fail-closed: 未知の op                                                     #
# --------------------------------------------------------------------------- #
def test_unknown_op_raises_and_lists_near_matches():
    with pytest.raises(ValueError) as ei:
        B.resolve_ops(["gaussain"])                     # typo of "gaussian"
    msg = str(ei.value)
    assert "unknown op name" in msg and "gaussian" in msg


def test_unknown_op_never_silently_shrinks_the_set():
    with pytest.raises(ValueError):
        B.resolve_ops(["gaussian", "definitely_not_an_op_xyz"])
    assert B.resolve_ops(["gaussian", "median"]) == ["gaussian", "median"]


def test_unknown_set_raises():
    with pytest.raises(ValueError, match="unknown set"):
        B.resolve_set("nope")


def test_a_set_degrades_over_absent_optional_backends():
    """セットは任意バックエンド(cv_/sk_/xkor_)を含む。無いものは **打ち間違いではない** ので
    落とさず、代わりに「測らなかった名前」を返す(黙って縮めない)。"""
    known = set(B.registry_names())
    for name in B.SETS:
        present, absent = B.resolve_set(name)
        assert present, name
        assert set(present) <= known
        assert set(absent).isdisjoint(known)
        assert set(present) | set(absent) == set(B.SETS[name])


def test_cli_returns_2_on_an_unknown_op(capsys):
    assert B.main(["--ops", "gaussain", "--sizes", "64"]) == 2
    assert "unknown op name" in capsys.readouterr().err


def test_the_core_set_is_fully_present_without_optional_backends():
    """core セットは numpy+scipy だけで全件測れる(= 任意依存に隠れた欠測が無い)。"""
    present, absent = B.resolve_set("core")
    assert absent == [], "core set names rotted out of the registry: %s" % absent
    assert len(present) == len(B.CORE_OPS)


def test_video_set_is_present_and_measures_per_frame():
    """--set video は videostream の op を streaming 経路で per-frame 計測する。"""
    present, absent = B.resolve_set("video")
    assert absent == [] and len(present) == len(B.VIDEO_OPS)
    rep = B.run(["frame_difference_causal", "deflicker"], [(48, 64, "48x64")],
                ["float64"], ["noisy"], warm=0, repeat=1, verbose=False)
    assert rep["summary"]["errors"] == 0, [r.get("error") for r in rep["rows"]]
    for r in rep["rows"]:
        assert r["streaming"] is True and r["kind"] == "video"
        assert r["frames"] == B.VIDEO_FRAMES and r["ms_frame"] > 0.0 and r["fps"] > 0.0
        assert r["out_dtype"] == "float64" and r["module"] == "videostream"
        assert r["fallbacks"] == 0


# --------------------------------------------------------------------------- #
# 4. 入力: ノイズ画像が必ず在る                                                  #
# --------------------------------------------------------------------------- #
def test_the_noisy_image_is_present_and_is_actually_noisy():
    assert "noisy" in B.DEFAULT_IMAGES
    noisy = B.scene(64, 64, "noisy")
    quant = B.scene(64, 64, "quantised")
    const = B.scene(64, 64, "constant")
    assert noisy.dtype == np.float64 and noisy.shape == (64, 64)
    assert 0.0 <= noisy.min() and noisy.max() <= 1.0
    # ノイズ画は同値が少なく、量子化画は 16 階調しかない = median の 10 倍差の源
    assert np.unique(noisy).size > 10 * np.unique(quant).size
    assert np.unique(quant).size <= 16
    assert np.unique(const).size == 1


def test_scene_is_deterministic():
    assert np.array_equal(B.scene(48, 48, "noisy"), B.scene(48, 48, "noisy"))
    assert np.array_equal(B.input_for("image", "noisy", 32, 32, "uint8"),
                          B.input_for("image", "noisy", 32, 32, "uint8"))


def test_scene_rejects_an_unknown_kind():
    with pytest.raises(ValueError, match="unknown image kind"):
        B.scene(16, 16, "sparkly")


def test_cli_refuses_to_drop_the_noisy_image(capsys):
    """ノイズ抜きのベンチは median の最悪側を隠すので CLI が拒否する。"""
    assert B.main(["--ops", "gaussian", "--sizes", "64", "--images", "quantised"]) == 2
    assert "noisy image is mandatory" in capsys.readouterr().err


def test_input_for_matches_the_op_sort():
    reg = B.input_for("region", "noisy", 32, 32, "float64")
    assert set(np.unique(reg)) <= {0.0, 1.0}
    assert B.input_for("color", "noisy", 32, 32, "float64").shape == (32, 32, 3)
    assert B.input_for("image", "noisy", 32, 32, "uint8").dtype == np.uint8


# --------------------------------------------------------------------------- #
# 5. twin 対応(発明ではなく registry の HALCON 名から引く)                       #
# --------------------------------------------------------------------------- #
def test_cv_twin_comes_from_the_registry_halcon_alias():
    pytest.importorskip("cv2")
    assert B.cv_twin("gaussian")[0] == "cv_gaussian"
    assert B.cv_twin("median")[0] == "cv_median"
    # edges_image は cv_scharr(image)と cv_canny(region)が名乗る -> sort で解く
    assert B.cv_twin("canny")[0] == "cv_canny"
    assert B.cv_twin("identity")[0] is None or B.cv_twin("identity")[0].startswith("cv_")


def test_ratio_vs_core_is_emitted_inside_one_run():
    """cv2 twin の効きは **同じ run の中**で比べる(run 跨ぎは熱ぶれ 1.7 倍に埋もれる)。"""
    pytest.importorskip("cv2")
    rep = B.run(["gaussian", "cv_gaussian"], [(64, 64, "64")], ["float64"], ["noisy"],
                warm=1, repeat=1, verbose=False)
    core, twin = rep["rows"]
    assert core["twin"] == "cv_gaussian"
    assert twin["core_ref"] == "gaussian"
    assert twin["ratio_vs_core"] == pytest.approx(core["ms"] / twin["ms"], abs=1e-3)  # 3 桁丸め
    assert core["twin_ratio_vs_core"] == twin["ratio_vs_core"]


# --------------------------------------------------------------------------- #
# 6. CLI の入出力                                                               #
# --------------------------------------------------------------------------- #
def test_cli_writes_report_and_baseline_then_exits_1_on_regression(tmp_path, capsys):
    out = tmp_path / "bench.json"
    base = tmp_path / "base.json"
    rc = B.main(["--ops", "gaussian,invert", "--sizes", "64", "--dtypes", "float64",
                 "--images", "noisy", "--repeat", "1", "--quiet",
                 "--out", str(out), "--write-baseline", str(base)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert len(report["rows"]) == 2 and "caveat" in report["header"]
    stored = json.loads(base.read_text(encoding="utf-8"))
    assert set(stored["metrics"]) == {"gaussian|64|float64", "invert|64|float64"}

    # 記録した ms を 1/20 に書き換える = 今回が 20 倍遅い -> exit 1。
    # (1/2 では 64² の ~0.05 ms 計測が 2 回目に warm で半分以下になり得て、
    #  フルスイート中に rc 0 になった = 2026-09-03 実測。閾値の検査は
    #  test_baseline_compare_* が固定値でやるので、ここは経路の検査に徹する)
    for v in stored["metrics"].values():
        v["ms"] = v["ms"] / 20.0
    base.write_text(json.dumps(stored), encoding="utf-8")
    rc = B.main(["--ops", "gaussian,invert", "--sizes", "64", "--dtypes", "float64",
                 "--images", "noisy", "--repeat", "1", "--quiet",
                 "--out", str(out), "--baseline", str(base), "--tolerance", "0.30"])
    assert rc == 1
    assert "REGRESSIONS" in capsys.readouterr().out
    assert json.loads(out.read_text(encoding="utf-8"))["comparison"]["regressions"]


def test_cli_reports_a_missing_baseline_file(tmp_path, capsys):
    rc = B.main(["--ops", "gaussian", "--sizes", "64", "--repeat", "1", "--quiet",
                 "--images", "noisy", "--out", str(tmp_path / "o.json"),
                 "--baseline", str(tmp_path / "nope.json")])
    assert rc == 2
    assert "cannot read baseline" in capsys.readouterr().err


def test_parse_size_and_dtype():
    assert B.parse_size("512") == (512, 512, "512")
    assert B.parse_size("1080p") == (1080, 1920, "1080p")
    assert B.parse_size("1920x1080") == (1080, 1920, "1920x1080")
    assert B.parse_dtype("f64") == "float64" and B.parse_dtype("u8") == "uint8"
    with pytest.raises(ValueError):
        B.parse_dtype("float16")
    with pytest.raises(ValueError):
        B.parse_size("0")


def test_heavy_ops_are_skipped_with_a_reason_not_dropped():
    """時間予算外の op は **行ごと消さず** 理由つきで残す(消すと未実行が発見ゼロに化ける)。"""
    row = B.bench_row("shape_locate", (2048, 2048, "2048"), "float64", "noisy",
                      warm=0, repeat=1, device="cpu", rss_read=None, accel_map={},
                      template_cache={})
    assert "skipped" in row and "ms" not in row
    assert "heavy op" in row["skipped"]


def test_an_op_error_is_recorded_on_the_row_not_swallowed(monkeypatch):
    """op が落ちても run は続き、行に error が残り、summary が件数を数える。"""
    def boom(*a, **k):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(B.api, "apply", boom)
    rep = B.run(["gaussian"], SIZE64, ["float64"], ["noisy"], warm=1, repeat=1, verbose=False)
    assert rep["summary"]["errors"] == 1
    assert "synthetic failure" in rep["rows"][0]["error"]
    assert rep["summary"]["error_names"] == ["gaussian"]


def test_report_is_json_serialisable(smoke_report):
    json.loads(json.dumps(copy.deepcopy(smoke_report), default=str))
