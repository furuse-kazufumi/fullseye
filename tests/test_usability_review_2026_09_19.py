# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-09-19 の外部ユーザビリティレビューで再現した不具合の回帰。

0.2.0 を core(`pip install fullseye`、693 op)と all(`fullseye[all]`、899 op)の 2 環境で
使い込んだ第三者レビュー(外部 AI、実行出力つき)を、1 件ずつこの木で再現してから直した
([[feedback_external_ai_verify]])。直したのは**バグ側**だけ:

* #1 / #2  backend 未導入の op が「unknown operator」になり、存在しない CLI を案内した
           → :class:`api.MissingBackendError`(索引の ``module`` / ``requires`` から不足 extra を言う)
* #4 / #5 / #6  ``run_pipeline`` の ``(name, {})`` / カンマ文字列 / 引数逆順が原因の読めない例外
           → :func:`api._normalise_stages`
* #7 / #8  全 NaN の otsu が numpy の RuntimeWarning で黙って全 0 / 定数画像の挙動が未記載
* N3 / #11 文字列配列が全 0(0.2.0)や生の UFuncTypeError、複素配列は虚部が黙って捨てられた
           → :func:`api._reject_untyped`(方針に依らず TypeError)
* #13  n-ary の形状不一致が numpy の broadcast エラーのまま台帳に残り、既定では第 1 入力が返った
* N5   Op が pickle できなかった → 名前で復元

設計判断として**変えなかった**もの(理由は docs/hardening/unknown-operator-hides-missing-backend.md):
既定 ``on_error="fallback"`` / dtype 変換の警告は op ごとに 1 度(台帳には全部残る)/ float32 の昇格は
記録しない / 公開名の数 / docstring 被覆の測り方 / import 時間 / a, b の引数名。
"""
from __future__ import annotations

import os
import pickle
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import ops  # noqa: E402
import fullseye as fs  # noqa: E402

IMG = np.random.default_rng(0).random((32, 32))


# ------------------------------------------------------------------ #1 / #2: 「無い」と「入っていない」を分ける
def test_unknown_operator_message_names_a_real_cli_and_op_find():
    with pytest.raises(KeyError) as ei:
        fs.apply(IMG, "no_such_op_xyz")
    msg = str(ei.value)
    assert "fullseye has no_such_op_xyz" in msg, msg          # 実在する console_script
    assert "op_find" in msg and "op_names" in msg, msg
    assert not isinstance(ei.value, fs.MissingBackendError)   # 本当に無い名前は素の KeyError


def test_missing_backend_error_is_a_keyerror_and_names_the_missing_extra(monkeypatch):
    fake = {"fake_sk_op": {"name": "fake_sk_op", "tier": "registry", "module": "backends_ski2",
                           "requires": ["skimage", "definitely_missing_mod_xyz"]}}
    monkeypatch.setattr(api, "_SHIPPED_INDEX_CACHE", fake)
    with pytest.raises(fs.MissingBackendError) as ei:
        fs.apply(IMG, "fake_sk_op")
    msg = str(ei.value)
    assert isinstance(ei.value, KeyError)                     # 既存の except KeyError も捕まえる
    assert "backends_ski2" in msg and "definitely_missing_mod_xyz" in msg, msg
    assert "pip install" in msg and "unknown operator" not in msg, msg
    with pytest.raises(fs.MissingBackendError):                # pipeline も同じ門を通る
        fs.run_pipeline(IMG, ["gaussian", "fake_sk_op"])


def test_missing_backend_error_points_at_failed_backends_when_imports_are_present(monkeypatch):
    fake = {"ghost_op": {"name": "ghost_op", "tier": "registry", "module": "backends_ghost", "requires": []}}
    monkeypatch.setattr(api, "_SHIPPED_INDEX_CACHE", fake)
    monkeypatch.setattr(ops, "FAILED_BACKENDS", [("backends_ghost", "ImportError: boom")], raising=False)
    with pytest.raises(fs.MissingBackendError, match="boom"):
        fs.apply(IMG, "ghost_op")


def test_missing_backend_error_is_on_the_facade():
    assert fs.MissingBackendError is api.MissingBackendError
    assert "MissingBackendError" in fs.__all__


def test_shipped_index_is_readable_and_carries_module_and_requires():
    table = api._shipped_index()
    assert len(table) > 900
    row = table["otsu"]
    assert row["module"] == "ops" and row["requires"] == []


def test_op_index_rows_carry_module_and_requires():
    import imgevolve as IE
    rows = [r for r in IE._build_op_index()["ops"] if r["tier"] == "registry"]
    assert rows
    assert all(isinstance(r.get("module"), str) and isinstance(r.get("requires"), list) for r in rows)
    by = {r["name"]: r for r in rows}
    assert by["otsu"]["module"] == "ops" and by["otsu"]["requires"] == []
    if "sk_canny" in by:
        assert "skimage" in by["sk_canny"]["requires"], by["sk_canny"]
    for r in rows:                                            # requires は必ず OPTIONAL_DEPS の語彙
        assert set(r["requires"]) <= set(ops.OPTIONAL_DEPS), r


def test_module_requirements_is_static_and_sees_lazy_imports():
    # backends_ski2 は build() の**中で** skimage を import する —— 実行せず AST で拾えること
    assert "skimage" in ops.module_requirements("backends_ski2")
    assert ops.module_requirements("ops") == []
    assert ops.module_requirements("no_such_module_xyz") == []
    assert set(ops.OP_MODULE) == {o.name for o in ops.REGISTRY}   # 全 op に出自がある


def test_optional_deps_table_matches_pyproject_extras():
    tomllib = pytest.importorskip("tomllib")
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        extras = tomllib.load(f)["project"]["optional-dependencies"]
    for imp, (pip, extra) in ops.OPTIONAL_DEPS.items():
        assert extra in extras, (imp, extra)
        assert any(req.lower().startswith(pip.lower()) for req in extras[extra]), (imp, pip, extras[extra])
        in_all = any(req.lower().startswith(pip.lower()) for req in extras["all"])
        assert in_all == (imp in ops.OPTIONAL_IN_ALL), (imp, pip, in_all)


# ------------------------------------------------------------------ #4 / #5 / #6: run_pipeline の書き方
def test_run_pipeline_accepts_dict_knobs_comma_string_and_dict_stages():
    ref = fs.run_pipeline(IMG, [("gaussian", 0.3, 0.5), ("otsu", 0.5, 0.5)])
    assert np.array_equal(fs.run_pipeline(IMG, [("gaussian", {"a": 0.3}), ("otsu", {})]), ref)
    assert np.array_equal(fs.run_pipeline(IMG, [{"op": "gaussian", "a": 0.3}, {"name": "otsu"}]), ref)
    assert np.array_equal(fs.run_pipeline(IMG, [("gaussian", 0.3), "otsu"]), ref)
    shared = fs.run_pipeline(IMG, ["gaussian", "otsu"], a=0.3)
    assert np.array_equal(fs.run_pipeline(IMG, "gaussian, otsu", a=0.3), shared)   # CLI と同じカンマ区切り


def test_run_pipeline_bad_forms_say_why():
    with pytest.raises(TypeError, match="swapped"):
        fs.run_pipeline([("gaussian",), ("otsu",)], IMG)
    with pytest.raises(TypeError, match="swapped"):
        fs.run_pipeline("gaussian,otsu", IMG)
    with pytest.raises(TypeError, match="unknown knob"):
        fs.run_pipeline(IMG, [("gaussian", {"sigma": 2})])
    with pytest.raises(TypeError, match="unknown key"):
        fs.run_pipeline(IMG, [{"op": "gaussian", "sigma": 2}])
    with pytest.raises(TypeError, match="must be numbers"):
        fs.run_pipeline(IMG, [("gaussian", {"a": "x"})])
    with pytest.raises(TypeError, match="expected"):
        fs.run_pipeline(IMG, [("gaussian", "0.3")])
    with pytest.raises(TypeError, match="stage 0"):
        fs.run_pipeline(IMG, [(0.3, "gaussian")])
    with pytest.raises(TypeError, match="stage 1"):
        fs.run_pipeline(IMG, ["gaussian", 42])
    with pytest.raises(KeyError, match="unknown operator 'nope'"):
        fs.run_pipeline(IMG, "gaussian,nope")                 # 1 文字ずつでなく語として引く


# ------------------------------------------------------------------ #7 / #8: otsu の判別できない入力
def test_otsu_all_nan_is_an_explicit_error_not_a_numpy_runtime_warning():
    nan = np.full((8, 8), np.nan)
    with pytest.raises(ValueError, match="no finite pixel"):
        fs.apply(nan, "otsu", on_error="raise")
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)           # numpy の All-NaN slice が出たら落ちる
        warnings.simplefilter("ignore", fs.FullseyeFallbackWarning)   # 台帳の 1 度目の警告は別物
        out = fs.apply(nan, "otsu")
    assert out.shape == (8, 8) and set(np.unique(out)) <= {0.0, 1.0}
    assert any(e["name"] == "otsu" and "no finite pixel" in e["error"] for e in fs.fallbacks())
    x = IMG.copy()
    x[::3] = np.nan                                             # 一部の NaN は今までどおり通す
    assert set(np.unique(fs.apply(x, "otsu", on_error="raise"))) <= {0.0, 1.0}


def test_otsu_constant_image_behaviour_is_pinned_and_documented():
    assert np.all(fs.apply(np.full((8, 8), 0.5), "otsu") == 1.0)   # 山が無い: 0 より大きい定数は全部前景
    assert np.all(fs.apply(np.zeros((8, 8)), "otsu") == 0.0)
    assert "定数画像" in (ops._otsu.__doc__ or "") and "NaN" in (ops._otsu.__doc__ or "")


# ------------------------------------------------------------------ N3 / #11: 変換の定義が無い入力は方針に依らず止める
def test_non_numeric_arrays_are_refused_under_every_policy():
    s = np.array([["a"] * 4] * 4)
    for pol in ("fallback", "warn", "raise"):
        with pytest.raises(TypeError, match="numeric"):
            fs.apply(s, "sobel_amp", on_error=pol)
    with pytest.raises(TypeError, match="numeric"):
        fs.apply(s, "reg_erode")                                  # region 入力でも(coerce の clip より前)
    with pytest.raises(TypeError, match="numeric"):
        fs.run_pipeline(s, "gaussian,otsu")
    with pytest.raises(TypeError, match="numeric"):
        fs.apply([IMG, s], "add_image")                           # n-ary の各入力にも
    with pytest.raises(TypeError, match="numeric"):
        fs.apply(np.array([[None] * 4] * 4), "sobel_amp")         # object dtype


def test_complex_input_to_a_real_op_is_refused_not_silently_realised():
    z = IMG + 1j * IMG[::-1]
    for pol in ("fallback", "raise"):
        with pytest.raises(TypeError, match="imaginary"):
            fs.apply(z, "sobel_amp", on_error=pol)
    with pytest.raises(TypeError, match="imaginary"):
        fs.run_pipeline(z, ["gaussian"])
    with warnings.catch_warnings():
        warnings.simplefilter("error")                              # ComplexWarning も出ないこと
        fs.apply(z, "identity")                                     # in_sort any は複素をそのまま通す
        for o in [o for o in ops.REGISTRY if o.in_sort == "cimage"][:1]:
            fs.apply(z, o.name)                                     # 複素場の op は受ける


def test_dtype_conversions_are_all_recorded_even_though_only_the_first_warns():
    # #12(外部レビュー)は「uint8 だけ警告」に見えたが、警告は op ごとに 1 度で台帳には全部残る
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for arr in ((IMG * 255).astype(np.uint8), (IMG * 10).astype(np.int32), IMG > 0.5):
            fs.apply(arr, "median_image")
    recs = [e["error"] for e in fs.fallbacks() if e["name"] == "median_image"]
    assert any("uint8" in r for r in recs) and any("int32" in r for r in recs) and any("bool" in r for r in recs), recs
    fs.clear_fallbacks()
    fs.apply(IMG.astype(np.float32), "median_image", on_error="raise")
    assert not fs.fallbacks()                                       # float32 → float64 は無損失の昇格: 記録しない


# ------------------------------------------------------------------ #13: n-ary の形状不一致
def test_nary_shape_mismatch_says_what_is_needed():
    b = np.random.default_rng(1).random((32, 16))
    with pytest.raises(ValueError, match="share one shape"):
        fs.apply([IMG, b], "add_image", on_error="raise")
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply([IMG, b], "add_image")
    assert out.shape == IMG.shape and np.array_equal(out, IMG)     # 既定: 第 1 入力がそのまま(文書どおり)
    assert any("share one shape" in e["error"] for e in fs.fallbacks())
    ok = fs.apply([IMG, IMG], "add_image", on_error="raise")
    assert ok.shape == IMG.shape


# ------------------------------------------------------------------ N5: Op は名前で pickle
def test_op_objects_pickle_by_name():
    op = next(o for o in ops.REGISTRY if o.name == "otsu")
    assert pickle.loads(pickle.dumps(op)) is op
    with pytest.raises(KeyError, match="not registered"):
        ops._op_from_name("no_such_op_xyz")


def test_aliases_resolve_regardless_of_case_and_hyphens():
    # GenSpark N50: HALCON のリファレンスは GAUSS_FILTER のように大文字で書かれる
    assert api.find_op("GAUSS_FILTER") is api.find_op("gauss_filter")
    assert api.find_op("Gauss-Filter") is api.find_op("gauss_filter")
    assert api.find_op("  Gaussian ") is api.find_op("gaussian")
    assert api.find_op("NO_SUCH_OP_XYZ") is None
    out = fs.apply(IMG, "GAUSS_FILTER")
    assert np.allclose(out, fs.apply(IMG, "gaussian"))
