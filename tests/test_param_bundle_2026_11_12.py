# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.parambundle — パラメータの束(2026-11-12)。

調査 DEFS_IO_SURVEY.md §5.11 の「段 0 の受け入れ条件」①〜⑥をそのまま試験にし、加えて単位変換・YAML の罠・
複数形式の一致・各エラー・比較表・循環・include・巨大な直積・実在の op を通した実行を見る。

門は**中身を数える**(空を通さない): 返った dict の鍵の集合、行数、件数を具体的な値で固定する。
"""
from __future__ import annotations

import inspect
import io
import json
import os
import random
import re
import warnings
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

import fullseye as fs
from fullseye import parambundle as PB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RIG_TOML = """\
# rig.toml (人が書く。コメント可)
[camera]
fx = "1200 px"
fy = "1200 px"
cx = 640.0
cy = 480.0
dist = [-0.12, 0.03, 0.0, 0.0, 0.0]
[lens]
wavelength = "550 nm"
focal = "25 mm"
f_number = 4.0
[sensor]
pixel_pitch = "3.45 um"
"""

RIG_JSON = {
    "camera": {"fx": "1200 px", "fy": "1200 px", "cx": 640.0, "cy": 480.0, "dist": [-0.12, 0.03, 0.0, 0.0, 0.0]},
    "lens": {"wavelength": "550 nm", "focal": "25 mm", "f_number": 4.0},
    "sensor": {"pixel_pitch": "3.45 um"},
}

RIG_YAML = """\
# rig.yaml
camera:
  fx: 1200 px
  fy: 1200 px
  cx: 640.0
  cy: 480.0
  dist: [-0.12, 0.03, 0.0, 0.0, 0.0]
lens:
  wavelength: 550 nm
  focal: 25 mm
  f_number: 4.0
sensor:
  pixel_pitch: 3.45 um
"""

RIG_KEYS = ["camera.fx", "camera.fy", "camera.cx", "camera.cy", "camera.dist",
            "lens.wavelength", "lens.focal", "lens.f_number", "sensor.pixel_pitch"]


def _write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return str(path)


@pytest.fixture()
def rig(tmp_path):
    return fs.load_params(_write(tmp_path / "rig.toml", RIG_TOML))


# ---------------------------------------------------------------------------------------------
# 段 0 の受け入れ条件 ①〜⑥
# ---------------------------------------------------------------------------------------------
def test_accept_1_for_op_returns_only_K_and_dist(rig):
    kw = rig.for_op("undistort_image")
    assert sorted(kw) == ["K", "dist"]
    K = kw["K"]
    assert isinstance(K, np.ndarray) and K.shape == (3, 3)
    assert K.tolist() == [[1200.0, 0.0, 640.0], [0.0, 1200.0, 480.0], [0.0, 0.0, 1.0]]
    assert kw["dist"].tolist() == [-0.12, 0.03, 0.0, 0.0, 0.0]
    # 渡して実際に動く
    img = np.random.default_rng(0).random((48, 64))
    out = fs.undistort_image(img, **kw)
    assert out.shape == img.shape


def test_accept_2_unused_keys_refused_by_strict(rig):
    kw, rep = rig.for_op("undistort_image", report=True)
    assert sorted(rep.unused) == ["lens.f_number", "lens.focal", "lens.wavelength", "sensor.pixel_pitch"]
    with pytest.raises(PB.UnusedParams) as ei:
        rig.for_op("undistort_image", strict=True)
    msg = str(ei.value)
    for k in rep.unused:
        assert k in msg
    # fs.run_params も実行前に断る
    with pytest.raises(PB.UnusedParams):
        fs.run_params("undistort_image", np.zeros((8, 8)), params=rig, strict=True)


def test_accept_3_missing_error_has_three_parts(tmp_path):
    only_cam = fs.ParamBundle({"camera.fx": 1200, "camera.fy": 1200, "camera.cx": 640})   # cy が無い
    with pytest.raises(PB.MissingParam) as ei:
        only_cam.for_op("undistort_image")
    msg = str(ei.value)
    assert "undistort_image needs K, dist" in msg                          # 1. 必要な名前
    assert "camera.fx" in msg and "camera.cx" in msg                       # 2. 束に在る名前
    assert "p.K()" in msg and "fx, fy, cx, cy" in msg                      # 3. 導出の手がかり
    assert "missing: K, dist" in msg


def _fraction_um_from_nm(text):
    return float(Fraction(Decimal(text)) * Fraction(Decimal("1E-9")) / Fraction(Decimal("1E-6")))


def test_accept_4_nm_to_um_matches_decimal_baseline_on_100k_random():
    rng = random.Random(20261112)
    mism_naive = 0
    n = 100_000
    for _ in range(n):
        d = rng.randint(0, 3)
        v = round(rng.uniform(0.0, 2000.0), d)
        text = repr(v)
        want = _fraction_um_from_nm(text)
        q = PB.parse_quantity("%s nm" % text)
        assert q is not None and q.text == text
        got = q.to("um")
        assert got == want, (text, got, want)
        if v * 1e-3 != want:
            mism_naive += 1
    # 比べた意味がある: 素朴な v*1e-3 は実際に外す(調査の実測 23,496 / 100,000)
    assert mism_naive > 5_000


def test_accept_4_nm_to_um_through_for_op(tmp_path):
    p = fs.ParamBundle({"wavelength": "550 nm"})
    assert p.for_op("mtf_diffraction", data=["f_number"])["wavelength_um"] == 0.55
    rng = random.Random(7)
    for _ in range(300):
        text = repr(round(rng.uniform(100.0, 1600.0), rng.randint(0, 3)))
        got = fs.ParamBundle({"wavelength": "%s nm" % text}).for_op("mtf_diffraction", data=["f_number"])["wavelength_um"]
        assert got == _fraction_um_from_nm(text)


def test_accept_5_circular_reference_detected(tmp_path):
    f = _write(tmp_path / "loop.json", json.dumps({"a": {"$param": "b"}, "b": {"$param": "c"}, "c": {"$param": "a"}}))
    with pytest.raises(PB.ParamError, match="circular reference"):
        fs.load_params(f)
    f2 = _write(tmp_path / "self.toml", 'x = { ref = "x" }\n')
    with pytest.raises(PB.ParamError, match="circular reference"):
        fs.load_params(f2)


def test_accept_5_references_resolve_and_keep_origin(tmp_path):
    f = _write(tmp_path / "r.toml", '[camera]\nfx = "1200 px"\n[alt]\nfx = { ref = "camera.fx" }\n')
    p = fs.load_params(f)
    assert str(p["alt.fx"]) == "1200 px"
    o = p.origin("alt.fx")
    assert o.ref == "camera.fx" and o.source == "r.toml"
    # 文字列 "camera.fx" は参照ではない(文字列のまま)
    g = _write(tmp_path / "s.json", json.dumps({"note": "camera.fx"}))
    assert fs.load_params(g)["note"] == "camera.fx"
    # 未解決の参照は断る
    h = _write(tmp_path / "u.json", json.dumps({"a": {"$param": "nope"}}))
    with pytest.raises(PB.ParamError, match="does not resolve"):
        fs.load_params(h)


def test_accept_6_origin_path_for_all_formats_and_line_for_yaml(tmp_path):
    pytest.importorskip("yaml")
    t = fs.load_params(_write(tmp_path / "rig.toml", RIG_TOML))
    j = fs.load_params(_write(tmp_path / "rig.json", json.dumps(RIG_JSON)))
    y = fs.load_params(_write(tmp_path / "rig.yaml", RIG_YAML))
    for name, b in (("rig.toml", t), ("rig.json", j), ("rig.yaml", y)):
        o = b.origin("fx")
        assert o.source == name and o.key == "camera.fx"
    assert t.origin("fx").line is None and j.origin("fx").line is None      # 行は YAML だけ(正直に)
    assert y.origin("fx").line == 3                                          # 1 行目コメント・2 行目 camera:
    assert y.origin("pixel_pitch").line == 13
    assert [y.origin(k).line for k in RIG_KEYS] == [3, 4, 5, 6, 7, 9, 10, 11, 13]


# ---------------------------------------------------------------------------------------------
# 束の読み書き・形式の一致
# ---------------------------------------------------------------------------------------------
def test_same_bundle_from_toml_json_yaml(tmp_path):
    pytest.importorskip("yaml")
    t = fs.load_params(_write(tmp_path / "a.toml", RIG_TOML))
    j = fs.load_params(_write(tmp_path / "a.json", json.dumps(RIG_JSON)))
    y = fs.load_params(_write(tmp_path / "a.yaml", RIG_YAML))
    assert list(t) == list(j) == list(y) == RIG_KEYS
    assert t == j == y
    assert len(t) == 9
    assert t.diff(j) == {} and t.diff(y) == {}
    assert isinstance(t["lens.wavelength"], PB.Quantity) and t["lens.wavelength"].unit == "nm"


def test_access_styles_and_sections(rig):
    assert str(rig.fx) == "1200 px" and str(rig["camera.fx"]) == "1200 px" and str(rig.camera.fx) == "1200 px"
    assert rig.sections() == ["camera", "lens", "sensor"]
    assert sorted(rig.camera) == ["cx", "cy", "dist", "fx", "fy"]
    assert rig.camera.K().tolist() == rig.K("camera").tolist()
    assert "fx" in rig and "camera" in rig and "nope" not in rig
    with pytest.raises(KeyError):
        rig["nope"]
    with pytest.raises(AttributeError):
        _ = rig.nope
    assert rig.origin("camera.fx").source == "rig.toml"


def test_bundle_is_read_only_and_with_does_not_mutate(rig):
    with pytest.raises(AttributeError):
        rig.camera = 1
    with pytest.raises(AttributeError):
        rig.name = "x"
    before = dict(rig)
    r = rig.with_(**{"camera.fx": 820})
    assert dict(rig) == before and r["camera.fx"] == 820
    assert r.origin("camera.fx").source == "<code>" and rig.origin("camera.fx").source == "rig.toml"
    assert rig.diff(r) == {"camera.fx": (rig["camera.fx"], 820)}
    assert list(rig.diff(r)) == ["camera.fx"]


def test_merged_overlay_and_origin(tmp_path, rig):
    night = fs.load_params(_write(tmp_path / "night.toml", '[camera]\nfx = 900.0\n[lens]\nf_number = 2.0\nnew = true\n'))
    q = rig.merged(night)
    assert q["camera.fx"] == 900.0 and q["lens.f_number"] == 2.0 and q["lens.new"] is True
    assert q["camera.fy"] is rig["camera.fy"] or str(q["camera.fy"]) == "1200 px"
    assert q.origin("camera.fx").source == "night.toml" and q.origin("camera.fy").source == "rig.toml"
    assert len(q) == len(rig) + 1
    assert set(rig.diff(q)) == {"camera.fx", "lens.f_number", "lens.new"}


def test_save_params_json_roundtrip_atomic(tmp_path, rig):
    out = tmp_path / "saved.json"
    fs.save_params(rig, str(out))
    text = out.read_text(encoding="utf-8")
    d = json.loads(text)
    assert d["lens"]["wavelength"] == "550 nm" and d["camera"]["dist"] == [-0.12, 0.03, 0.0, 0.0, 0.0]
    again = fs.load_params(str(out))
    assert again == rig and len(again) == 9
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".params-")] == []      # 一時ファイルが残らない
    with pytest.raises(PB.ParamError, match="JSON only"):
        fs.save_params(rig, str(tmp_path / "x.toml"))
    with pytest.raises(PB.ParamError):
        fs.save_params(rig, str(tmp_path / "nodir" / "x.json"))
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        fs.ParamBundle({"a": float("nan")})
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        fs.ParamBundle({"a": float("inf")})


def test_json_gates(tmp_path):
    with pytest.raises(PB.ParamFileError, match="comments"):
        fs.load_params(_write(tmp_path / "c.json", '{"a": 1, // c\n "b": 2}'))
    with pytest.raises(PB.ParamFileError, match="duplicate key"):
        fs.load_params(_write(tmp_path / "d.json", '{"a": 1, "a": 2}'))
    with pytest.raises(PB.ParamFileError, match="constant"):
        fs.load_params(_write(tmp_path / "n.json", '{"a": NaN}'))
    with pytest.raises(PB.ParamFileError, match="JSONC / JSON5"):
        fs.load_params(_write(tmp_path / "x.jsonc", '{"a": 1}'))
    with pytest.raises(PB.ParamFileError, match="JSONC / JSON5"):
        fs.load_params(_write(tmp_path / "x.json5", '{"a": 1}'))
    with pytest.raises(PB.ParamFileError, match="null"):
        fs.load_params(_write(tmp_path / "z.json", '{"a": null}'))
    with pytest.raises(PB.ParamFileError, match="top level"):
        fs.load_params(_write(tmp_path / "l.json", '[1, 2]'))
    with pytest.raises(PB.ParamFileError, match="unknown extension"):
        fs.load_params(_write(tmp_path / "x.ini", "a=1"))
    with pytest.raises(PB.ParamFileError, match="not a file"):
        fs.load_params(str(tmp_path / "missing.json"))
    with pytest.raises(PB.ParamFileError, match="limit"):
        fs.load_params(_write(tmp_path / "big.json", '{"a": 1}'), max_bytes=3)
    with pytest.raises(PB.ParamFileError, match="inside an array"):
        fs.load_params(_write(tmp_path / "t.json", '{"a": [{"b": 1}]}'))
    with pytest.raises(PB.ParamFileError, match="invalid key"):
        fs.load_params(_write(tmp_path / "k.json", '{"a.b": 1}'))
    with pytest.raises(PB.ParamFileError, match="both a value and a section"):
        fs.ParamBundle({"a": 1, "a.b": 2})


def test_toml_gates(tmp_path):
    with pytest.raises(PB.ParamFileError, match="invalid TOML"):
        fs.load_params(_write(tmp_path / "dup.toml", "a = 1\na = 2\n"))
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        fs.load_params(_write(tmp_path / "inf.toml", "a = inf\n"))
    p = fs.load_params(_write(tmp_path / "ok.toml", "exposure_s = 1e-3\nd = 2026-11-12\n"))
    assert p["exposure_s"] == 0.001 and isinstance(p["exposure_s"], float)     # TOML は 1e-3 を float で読む
    assert p["d"] == "2026-11-12"                                               # 日付は文字列


# ---------------------------------------------------------------------------------------------
# YAML の罠
# ---------------------------------------------------------------------------------------------
def _yaml(tmp_path, text, name="t.yaml"):
    return fs.load_params(_write(tmp_path / name, text))


def test_yaml_12_core_schema_values(tmp_path):
    """素のスカラーは YAML 1.2 の core schema: true/false・0o10・1e3・-0.5・.5 が値になる。"""
    pytest.importorskip("yaml")
    p = _yaml(tmp_path, "a: true\nb: false\nc: 0o10\nd: 1e3\ne: -0.5\nf: .5\ng: 1.10\nh: 0x1F\ni: 12\nj: 1.0e-3\nk: 1e-3\n"
                        "s: hello\nq: 'no'\nq2: \"NO\"\nq3: '010'\nq4: '12:30:00'\nq5: 'yes'\nq6: '1e-3'\n")
    assert p["a"] is True and p["b"] is False
    assert p["c"] == 8 and isinstance(p["c"], int)
    assert p["d"] == 1000.0 and isinstance(p["d"], float)
    assert p["e"] == -0.5 and p["f"] == 0.5
    assert p["g"] == 1.1 and p["h"] == 31 and p["i"] == 12
    assert p["j"] == 0.001 and p["k"] == 0.001                              # 1e-3 は 1.2 で float
    assert p["s"] == "hello"
    # 引用符つきは文字列のまま通る
    assert [p[k] for k in ("q", "q2", "q3", "q4", "q5", "q6")] == ["no", "NO", "010", "12:30:00", "yes", "1e-3"]
    assert len(p) == 18


@pytest.mark.parametrize("text,word", [
    ("country: NO\n", "NO"), ("flag: no\n", "no"), ("a: yes\n", "yes"), ("a: Yes\n", "Yes"), ("a: YES\n", "YES"),
    ("a: on\n", "on"), ("a: Off\n", "Off"), ("a: OFF\n", "OFF"), ("a: y\n", "y"), ("a: N\n", "N"),
    ("oct: 010\n", "010"), ("a: 0777\n", "0777"), ("a: -012\n", "-012"),
    ("time: 12:30:00\n", "12:30:00"), ("a: 1:30\n", "1:30"), ("a: 0b101\n", "0b101"), ("a: 1_000\n", "1_000"),
    ("lst: [1, no]\n", "no"), ("s:\n  deep: off\n", "off"),
])
def test_yaml_11_ambiguous_plain_scalars_are_refused_with_line(tmp_path, text, word):
    pytest.importorskip("yaml")
    with pytest.raises(PB.ParamFileError) as ei:
        _yaml(tmp_path, "# c\n" + text)
    msg = str(ei.value)
    assert "line 2" in msg or "line 3" in msg                                # 行番号つき
    assert "quote it" in msg and ("plain %s" % word) in msg and "0o10" in msg


def test_yaml_ambiguous_key_is_refused_and_numeric_keys(tmp_path):
    pytest.importorskip("yaml")
    with pytest.raises(PB.ParamFileError, match="plain NO"):
        _yaml(tmp_path, "NO: x\n")
    with pytest.raises(PB.ParamFileError, match="not a string"):
        _yaml(tmp_path, "1: x\n")                                           # 数のキーは文字列でない
    assert _yaml(tmp_path, "'NO': x\n")["NO"] == "x"                         # 引用符ならキーにできる


def test_yaml_pitfalls(tmp_path):
    pytest.importorskip("yaml")
    # 数の欄に引用符つきの文字列は断る(どの形式でも)
    with pytest.raises(PB.ParamTypeError, match="numeric field"):
        _yaml(tmp_path, "exposure_s: '1e-3'\n")
    with pytest.raises(PB.ParamTypeError, match="boolean"):
        _yaml(tmp_path, "pixel_pitch_um: true\n")
    # null は値ではない
    for text in ("a: null\n", "a: ~\n", "a:\n"):
        with pytest.raises(PB.ParamFileError, match="null"):
            _yaml(tmp_path, text)
    # 重複キー(PyYAML は後勝ちで黙る)
    with pytest.raises(PB.ParamFileError, match="duplicate key 'a'"):
        _yaml(tmp_path, "a: 1\na: 2\n")
    with pytest.raises(PB.ParamFileError, match="duplicate key"):
        _yaml(tmp_path, "s:\n  x: 1\n  x: 2\n")
    # 日付は文字列へ
    assert _yaml(tmp_path, "d: 2026-11-12\nt: 2026-11-12 10:00:00\n")["d"] == "2026-11-12"
    with pytest.raises(PB.ParamFileError, match="invalid YAML"):
        _yaml(tmp_path, "a:\n\tb: 1\n")
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        _yaml(tmp_path, "a: .inf\n")
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        _yaml(tmp_path, "a: .nan\n")
    assert len(_yaml(tmp_path, "")) == 0


def test_yaml_never_runs_code(tmp_path):
    pytest.importorskip("yaml")
    marker = tmp_path / "ran.txt"
    evil = "x: !!python/object/apply:builtins.exec [\"open(%r,'w').write('ran')\"]\n" % str(marker)
    with pytest.raises(PB.ParamFileError, match="invalid YAML"):
        fs.load_params(_write(tmp_path / "evil.yaml", evil))
    assert not marker.exists()


def test_yaml_alias_bomb_and_recursion_refused(tmp_path):
    pytest.importorskip("yaml")
    lines = ["a0: &a0 [x, x, x, x, x, x, x, x, x, x]"]
    for i in range(1, 12):
        lines.append("a%d: &a%d [%s]" % (i, i, ", ".join(["*a%d" % (i - 1)] * 10)))
    with pytest.raises(PB.ParamFileError, match="alias bomb"):
        fs.load_params(_write(tmp_path / "bomb.yaml", "\n".join(lines) + "\n"))
    # 小さいアンカーは使える
    ok = fs.load_params(_write(tmp_path / "ok.yaml", "base: &b 1.5\nsigma: *b\n"))
    assert ok["sigma"] == 1.5 and ok["base"] == 1.5
    with pytest.raises(PB.ParamFileError):
        fs.load_params(_write(tmp_path / "rec.yaml", "a: &x [1, *x]\n"))
    deep = "a: " + "[" * 150 + "1" + "]" * 150 + "\n"
    with pytest.raises(PB.ParamFileError, match="deeper"):
        fs.load_params(_write(tmp_path / "deep.yaml", deep))


def test_yaml_source_never_uses_unsafe_loaders():
    """ソースの走査: ``yaml.load(`` と UnsafeLoader / FullLoader / ``yaml.unsafe_load`` を使っていない。"""
    src = io.open(os.path.join(ROOT, "fullseye", "parambundle.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    code_no_docs = re.sub(r'"""(.*?)"""', "", code, flags=re.S)
    assert "SafeLoader" in code_no_docs
    for bad in ("yaml.load(", "yaml.load_all(", "UnsafeLoader", "FullLoader", "unsafe_load", "yaml.Loader", "BaseLoader"):
        assert bad not in code_no_docs, bad
    # 他の出荷コードも(束の層に限らず)yaml.load を使っていない
    for name in ("parambundle.py",):
        assert "yaml.load(" not in io.open(os.path.join(ROOT, "fullseye", name), encoding="utf-8").read().replace('``yaml.load(``', "")


def test_yaml_missing_gives_install_hint(tmp_path, monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name == "yaml":
            raise ImportError("no yaml")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake)
    with pytest.raises(PB.ParamFileError, match=r"pip install \"fullseye\[yaml\]\""):
        fs.load_params(_write(tmp_path / "a.yaml", "a: 1\n"))


# ---------------------------------------------------------------------------------------------
# include
# ---------------------------------------------------------------------------------------------
def test_include_same_folder_and_below(tmp_path):
    (tmp_path / "sub").mkdir()
    _write(tmp_path / "base.toml", "[camera]\nfx = 1000.0\nfy = 1000.0\ncx = 1.0\ncy = 2.0\n")
    _write(tmp_path / "sub" / "lens.json", json.dumps({"lens": {"f_number": 2.8}}))
    main = _write(tmp_path / "main.toml", 'include = ["base.toml", "sub/lens.json"]\n[camera]\nfx = 1100.0\n')
    p = fs.load_params(main)
    assert p["camera.fx"] == 1100.0 and p["camera.fy"] == 1000.0 and p["lens.f_number"] == 2.8
    assert len(p) == 5 and "include" not in p
    assert p.origin("camera.fx").source == "main.toml"
    assert p.origin("camera.fy").source == "base.toml"
    assert p.origin("lens.f_number").source == "sub/lens.json"


def test_include_refuses_outside_absolute_and_cycles(tmp_path):
    inner = tmp_path / "inner"
    inner.mkdir()
    _write(tmp_path / "outside.toml", "x = 1\n")
    for bad, why in (('"../outside.toml"', "outside|'..'"), ('"%s"' % str(tmp_path / "outside.toml").replace("\\", "/"), "absolute"),
                     ('"/etc/passwd"', "absolute"), ('"C:/x.toml"', "absolute"), ('"sub/../../outside.toml"', "'..'"),
                     ('"~/x.toml"', "absolute")):
        f = _write(inner / "m.toml", "include = [%s]\n" % bad)
        with pytest.raises(PB.ParamFileError, match=why):
            fs.load_params(f)
    _write(inner / "a.toml", 'include = ["b.toml"]\n')
    _write(inner / "b.toml", 'include = ["a.toml"]\n')
    with pytest.raises(PB.ParamFileError, match="circular include"):
        fs.load_params(str(inner / "a.toml"))
    f = _write(inner / "n.toml", 'include = "base.toml"\n')
    with pytest.raises(PB.ParamFileError, match="list of file names"):
        fs.load_params(f)
    f = _write(inner / "o.toml", "include = [1]\n")
    with pytest.raises(PB.ParamFileError, match="non-empty strings"):
        fs.load_params(f)
    f = _write(inner / "p.toml", 'include = ["nothere.toml"]\n')
    with pytest.raises(PB.ParamFileError, match="not a file|cannot read"):
        fs.load_params(f)


def test_include_refuses_symlink_and_junction(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    _write(real / "t.toml", "x = 1\n")
    box = tmp_path / "box"
    box.mkdir()
    made = False
    try:
        os.symlink(str(real / "t.toml"), str(box / "link.toml"))
        made = True
        f = _write(box / "m.toml", 'include = ["link.toml"]\n')
        with pytest.raises(PB.ParamFileError, match="symbolic link|resolves elsewhere|outside"):
            fs.load_params(f)
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        import subprocess
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(box / "jn"), str(real)], capture_output=True)
        if r.returncode == 0:
            made = True
            f = _write(box / "m2.toml", 'include = ["jn/t.toml"]\n')
            with pytest.raises(PB.ParamFileError, match="symbolic link|resolves elsewhere|outside"):
                fs.load_params(f)
            os.rmdir(str(box / "jn"))
    if not made:
        pytest.skip("cannot create a symlink or junction here")


def test_include_depth_limit(tmp_path):
    n = PB.MAX_INCLUDE_DEPTH + 2
    for i in range(n):
        _write(tmp_path / ("f%d.toml" % i), ('include = ["f%d.toml"]\n' % (i + 1)) if i < n - 1 else "x = 1\n")
    with pytest.raises(PB.ParamFileError, match="deeper"):
        fs.load_params(str(tmp_path / "f0.toml"))


# ---------------------------------------------------------------------------------------------
# for_op: 単位・同義・エラー
# ---------------------------------------------------------------------------------------------
def test_unit_conversions_table_and_dimension_errors():
    assert PB.convert_number(Decimal("550"), "nm", "um") == 0.55
    assert PB.convert_number(Decimal("3.45"), "um", "mm") == 0.00345
    assert PB.convert_number(2, "m", "mm") == 2000.0
    assert PB.convert_number(1, "ms", "s") == 0.001
    assert PB.convert_number(Decimal("2.5"), "mhz", "khz") == 2500.0
    assert PB.convert_number(180, "deg", "rad") == pytest.approx(np.pi, abs=0) or abs(PB.convert_number(180, "deg", "rad") - np.pi) < 1e-15
    assert PB.convert_number(5, "um", "um") == 5 and isinstance(PB.convert_number(5, "um", "um"), int)
    with pytest.raises(PB.UnitMismatch):
        PB.convert_number(1, "mm", "ms")
    assert set(PB.UNITS) >= {"m", "cm", "mm", "um", "nm", "pm", "s", "ms", "us", "ns", "hz", "khz", "mhz", "ghz", "px", "deg", "rad"}
    assert PB.parse_quantity("0.55 \u00b5m").unit == "um" and PB.parse_quantity("45 \u00b0").unit == "deg"
    assert PB.parse_quantity("3 Mm") is None and PB.parse_quantity("550") is None and PB.parse_quantity("550 apples") is None
    assert PB.parse_quantity("1e-3 s").value == 0.001 and PB.parse_quantity("-2 mm").value == -2


def test_quantity_kept_as_written():
    p = fs.ParamBundle({"wavelength": "550 nm", "pitch": "0.55 um"})
    q = p["wavelength"]
    assert (q.value, q.unit, str(q)) == (550, "nm", "550 nm")
    assert p.to_dict()["wavelength"] == "550 nm"                             # 変換して書き戻さない
    assert fs.load_params and p.for_op("airy_radius_um")["wavelength_nm"] == 550    # nm → nm は無変換(int のまま)


def test_unit_mismatch_and_type_errors():
    p = fs.ParamBundle({"focal": "25 px"})
    with pytest.raises(PB.UnitMismatch, match="pixel"):
        p.for_op("depth_of_field", data=["f_number"])                       # focal_mm に px
    p2 = fs.ParamBundle({"focal": 25})                                      # 単位なしの数 → focal_mm に黙って入れない
    with pytest.raises(PB.UnitMismatch, match="no unit"):
        p2.for_op("depth_of_field", data=["f_number"])
    p3 = fs.ParamBundle({"focal_mm": 25})                                   # 名前が単位を持つ数は mm
    assert p3.for_op("depth_of_field", data=["f_number"]) == {"focal_mm": 25}
    p4 = fs.ParamBundle({"focal_length_mm": 25, "wavelength_nm": 600})      # 同義の綴り + 名前の単位
    assert p4.for_op("depth_of_field", data=["f_number"]) == {"focal_mm": 25}
    p5 = fs.ParamBundle({"airy_pattern.size": 3.5})
    with pytest.raises(PB.ParamTypeError, match="integer"):
        p5.for_op("airy_pattern")
    assert fs.ParamBundle({"airy_pattern.size": 32.0}).for_op("airy_pattern") == {"size": 32}
    p6 = fs.ParamBundle({"airy_pattern.size": "big"})
    with pytest.raises(PB.ParamTypeError, match="expects a number"):
        p6.for_op("airy_pattern")
    with pytest.raises(PB.ParamTypeError, match="boolean"):
        fs.ParamBundle({"wavelength_nm": True})
    with pytest.raises(PB.ParamTypeError, match="numeric field"):
        fs.ParamBundle({"exposure_s": "1e-3"})
    with pytest.raises(PB.UnitMismatch, match="bare number"):
        fs.ParamBundle({"focal": "5 mm"}).for_op("custom_op", fn=lambda focal: None)    # 単位の無い引数名に Quantity は渡さない
    with pytest.raises(PB.ParamError, match="unknown op"):
        fs.ParamBundle({}).for_op("no_such_op_xyz")


def test_synonym_table_is_single_source_and_unique():
    groups = PB.SYNONYM_GROUPS
    assert len(groups) == 7
    flat = [s for g in groups for s in g]
    assert len(flat) == len(set(flat)) == 21                                  # 同じ綴りが 2 つの群に入らない
    assert "pitch" not in flat and "f" not in flat                            # 衝突するので入れていない
    # 表の綴りはどれも op に写る
    p = fs.ParamBundle({"pixel_size": "3.45 um", "lambda": "0.55 um", "fno": 4.0})
    kw = p.for_op("airy_pattern", report=True)
    assert kw[0] == {"wavelength_um": 0.55, "f_number": 4.0, "pixel_pitch_um": 3.45}
    assert sorted(e.how for e in kw[1].entries) == ["exact", "synonym", "synonym"] or sorted(e.how for e in kw[1].entries) == ["synonym"] * 3


def test_synonym_ambiguity_refused_but_equal_values_allowed():
    p = fs.ParamBundle({"wavelength": "550 nm", "wl": "0.55 um"})              # 同じ値(単位違い)→ 1 つ
    assert p.for_op("mtf_diffraction", data=["f_number"]) == {"wavelength_um": 0.55}
    q = fs.ParamBundle({"wavelength": "550 nm", "wl": "600 nm"})
    with pytest.raises(PB.AmbiguousParam, match="different values"):
        q.for_op("mtf_diffraction", data=["f_number"])
    r = fs.ParamBundle({"camera.f_number": 2.0, "lens.f_number": 4.0})
    with pytest.raises(PB.AmbiguousParam, match="more than one"):
        r.for_op("mtf_diffraction", data=["wavelength_um"])
    # [op] の節が曖昧さを解く
    assert fs.ParamBundle({"camera.f_number": 2.0, "lens.f_number": 4.0, "mtf_diffraction.f_number": 8.0}).for_op(
        "mtf_diffraction", data=["wavelength_um"]) == {"f_number": 8.0}
    with pytest.raises(PB.AmbiguousParam):
        fs.ParamBundle({"a.fx": 1.0, "a.fy": 1.0, "a.cx": 1.0, "a.cy": 1.0, "b.fx": 1.0, "b.fy": 1.0, "b.cx": 1.0, "b.cy": 1.0}).K()
    assert fs.ParamBundle({"a.fx": 1.0, "a.fy": 2.0, "a.cx": 3.0, "a.cy": 4.0, "b.fx": 1.0, "b.fy": 1.0, "b.cx": 1.0, "b.cy": 1.0}).K("a").tolist()[1][1] == 2.0


def test_report_records_copy_convert_synonym_derive(rig):
    kw, rep = rig.for_op("depth_of_field", report=True, data=[])
    assert kw == {"focal_mm": 25, "f_number": 4.0}
    assert [(e.arg, e.how, e.converted) for e in rep.entries] == [("focal_mm", "synonym", False), ("f_number", "exact", False)]
    kw2, rep2 = rig.for_op("airy_pattern", report=True)
    assert kw2 == {"wavelength_um": 0.55, "f_number": 4.0, "pixel_pitch_um": 3.45}
    assert [e.arg for e in rep2.converted] == ["wavelength_um"] and rep2.converted[0].note == "nm -> um"
    assert [e.arg for e in rep2.synonyms] == ["wavelength_um", "pixel_pitch_um"]
    assert [e.arg for e in rep2.copied] == ["f_number"]
    assert sorted(rep2.unused) == ["camera.cx", "camera.cy", "camera.dist", "camera.fx", "camera.fy", "lens.focal"]
    kw3, rep3 = rig.for_op("undistort_image", report=True)
    assert [e.arg for e in rep3.derived] == ["K"] and rep3.derived[0].keys == ("camera.fx", "camera.fy", "camera.cx", "camera.cy")
    assert "unused" in rep2.text() and "wavelength_um" in rep2.text()


def test_bundle_unused_over_several_ops(rig):
    assert rig.unused(["undistort_image", "airy_pattern", "depth_of_field"]) == []
    assert rig.unused(["undistort_image"]) == ["lens.wavelength", "lens.focal", "lens.f_number", "sensor.pixel_pitch"]


def test_explicit_K_beats_derivation_and_arrays_become_ndarray():
    p = fs.ParamBundle({"camera.K": [[800, 0, 320], [0, 800, 240], [0, 0, 1]], "camera.dist": [0.0] * 5})
    kw = p.for_op("undistort_image")
    assert kw["K"].tolist() == [[800, 0, 320], [0, 800, 240], [0, 0, 1]] and kw["K"].dtype == np.float64
    kw2 = fs.ParamBundle({"image_size": [32, 48]}).for_op("distortion_map", data=["system"])
    assert kw2 == {"image_size": (32, 48)}                                     # 既定が tuple なら tuple


# ---------------------------------------------------------------------------------------------
# 比べる表
# ---------------------------------------------------------------------------------------------
def test_params_compare_table_marks_and_unit_equality(tmp_path):
    a = fs.ParamBundle({"lens.wavelength": "0.55 um", "lens.f": 4.0, "cam.fx": 1200, "only_a": 1}, name="A")
    b = fs.ParamBundle({"lens.wavelength": "550 nm", "lens.f": 4.0, "cam.fx": 820, "only_b": 2}, name="B")
    c = fs.ParamBundle({"lens.wavelength": "550 nm", "lens.f": 4, "cam.fx": 1200}, name="C")
    cmp = fs.params_compare([a, b, c])
    assert cmp.names == ("A", "B", "C")
    rows = {r.key: r for r in cmp}
    assert list(rows) == ["lens.wavelength", "lens.f", "cam.fx", "only_a", "only_b"] and len(cmp) == 5
    assert rows["lens.wavelength"].status == "same" and rows["lens.wavelength"].notation_differs      # "0.55 um" = "550 nm"
    assert rows["lens.f"].status == "same" and not rows["lens.f"].notation_differs                    # 4.0 == 4
    assert rows["cam.fx"].status == "differ"
    assert rows["only_a"].status == "partial" and rows["only_a"].values == (1, None, None)
    assert rows["only_b"].status == "partial" and rows["only_b"].values == (None, 2, None)
    assert cmp.counts() == {"same": 2, "differ": 1, "partial": 2}
    t = cmp.table()
    assert t[0] == ["key", "A", "B", "C", "status"] and len(t) == 6
    assert [r[-1] for r in t[1:]] == ["=~", "=", "!=", "?", "?"]
    assert "0.55 um" in cmp.text() and "550 nm" in cmp.text()
    # 単位が違えば違う(長さと時間)/ 数と単位つきは別物 / 真偽と数は別物
    d1 = fs.ParamBundle({"x": "1 mm", "y": 1, "z": True})
    d2 = fs.ParamBundle({"x": "1 ms", "y": "1 mm", "z": 1})
    assert [r.status for r in fs.params_compare([d1, d2])] == ["differ", "differ", "differ"]
    # 名前が重複したら番号で区別
    assert fs.params_compare([a, a]).names == ("A#1", "A#2")
    with pytest.raises(PB.ParamError):
        fs.params_compare([a])


def test_values_equal_edge_cases():
    q = PB.parse_quantity
    assert PB.values_equal(q("0.55 um"), q("550 nm")) and PB.values_equal(q("1 m"), q("1000 mm"))
    assert not PB.values_equal(q("0.55 um"), q("551 nm"))
    assert PB.values_equal(q("180 deg"), q("3.141592653589793 rad"))
    assert not PB.values_equal(q("180 deg"), q("3 rad"))
    assert PB.values_equal((1, q("1 mm")), (1.0, q("1000 um"))) and not PB.values_equal((1, 2), (1, 2, 3))
    assert PB.values_equal("a", "a") and not PB.values_equal("a", "b")


# ---------------------------------------------------------------------------------------------
# 走査
# ---------------------------------------------------------------------------------------------
def test_param_grid_product_zip_and_limits(rig):
    g = fs.param_grid(rig, **{"lens.f_number": [2, 4, 8], "sensor.pixel_pitch": ["3 um", "4 um"]})
    assert len(g) == 6 and isinstance(g[0], fs.ParamBundle)
    pts = g.points()
    assert pts[0] == {"lens.f_number": 2, "sensor.pixel_pitch": "3 um"} and pts[-1] == {"lens.f_number": 8, "sensor.pixel_pitch": "4 um"}
    assert len({tuple(sorted(p.items())) for p in pts}) == 6
    assert [b["lens.f_number"] for b in g] == [2, 2, 4, 4, 8, 8]
    assert str(g[1]["sensor.pixel_pitch"]) == "4 um" and g[1].origin("lens.f_number").source == "<code>"
    assert rig["lens.f_number"] == 4.0                                        # 元は不変
    z = fs.param_zip(rig, **{"lens.f_number": [2, 4, 8], "camera.cx": [1.0, 2.0, 3.0]})
    assert len(z) == 3 and z.points()[2] == {"lens.f_number": 8, "camera.cx": 3.0}
    with pytest.raises(PB.ParamError, match="equal length"):
        fs.param_zip(rig, allow_new=True, a=[1, 2], b=[1])
    with pytest.raises(PB.ParamError, match="empty"):
        fs.param_grid(rig, a=[])
    with pytest.raises(PB.ParamError, match="list of values"):
        fs.param_grid(rig, a="abc")
    with pytest.raises(PB.ParamError, match="at least one axis"):
        fs.param_grid(rig)
    with pytest.raises(PB.ParamFileError, match="non-finite"):
        fs.param_grid(rig, a=[1.0, float("nan")])


def test_param_grid_refuses_huge_product_before_building(rig):
    axes = {"axis%d" % i: list(range(10)) for i in range(7)}                  # 10^7 点
    with pytest.raises(PB.GridTooLarge) as ei:
        fs.param_grid(rig, allow_new=True, **axes)
    msg = str(ei.value)
    assert "10,000,000 points" in msg and "limit is 10,000" in msg and "MB" in msg and "10 x 10 x 10 x 10 x 10 x 10 x 10" in msg
    big = fs.param_grid(rig, max_points=10 ** 7, allow_new=True, **axes)                      # 引き上げれば遅延で作れる
    assert len(big) == 10 ** 7 and big[10 ** 7 - 1]["axis6"] == 9
    with pytest.raises(PB.GridTooLarge):
        fs.param_zip(rig, max_points=2, allow_new=True, a=[1, 2, 3])


def test_sweep_runs_real_op_and_records_rows(rig):
    g = fs.param_grid(rig, **{"lens.f_number": [2.8, 5.6, 11.0]})
    rows = fs.sweep(lambda b: fs.ledger.airy_pattern(**b.for_op("airy_pattern")), None, g, metric=lambda r: float(np.sum(r)))
    assert [r["index"] for r in rows] == [0, 1, 2] and all(r["error"] is None for r in rows)
    assert [r["lens.f_number"] for r in rows] == [2.8, 5.6, 11.0]
    assert len({r["value"] for r in rows}) == 3                              # f 値で結果が変わる(空を通さない)
    bad = fs.sweep(lambda b: 1 / 0, None, g, on_error="record")
    assert len(bad) == 3 and all("ZeroDivisionError" in r["error"] for r in bad)
    with pytest.raises(ZeroDivisionError):
        fs.sweep(lambda b: 1 / 0, None, g)
    # op 名で回す(波長・画素ピッチの束 → mtf の走査)
    base = fs.ParamBundle({"wavelength": "550 nm"})
    g2 = fs.param_grid(base, **{"wavelength": ["450 nm", "550 nm", "650 nm"]})
    rows2 = fs.sweep("mtf_diffraction", None, g2, metric=lambda r: float(np.asarray(r[1] if isinstance(r, tuple) else r).sum()),
                     f_number=5.6)
    assert len(rows2) == 3 and len({r["value"] for r in rows2}) == 3


# ---------------------------------------------------------------------------------------------
# 実在の op を通して for_op → 実行まで
# ---------------------------------------------------------------------------------------------
def _ledger_ops_with(arg):
    names = []
    for n in dir(fs.ledger):
        if n.startswith("_"):
            continue
        f = getattr(fs.ledger, n)
        try:
            if arg in inspect.signature(f).parameters:
                names.append(n)
        except (TypeError, ValueError):
            pass
    return names


def test_ledger_has_ops_for_each_kind_of_bundle_value():
    """試験が選ぶ op が台帳に実在し、ある程度の数ある(空の集合を通さない)。"""
    assert len(_ledger_ops_with("wavelength_um")) >= 15
    assert len(_ledger_ops_with("pixel_pitch_um")) >= 8
    assert len(_ledger_ops_with("wavelength_nm")) >= 8
    assert hasattr(fs, "undistort_image") and hasattr(fs, "project_points")


def test_every_wavelength_um_op_gets_converted_value_from_nm_bundle():
    ops = _ledger_ops_with("wavelength_um")
    p = fs.ParamBundle({"wavelength": "550 nm"})
    seen = 0
    for name in ops:
        sig = inspect.signature(getattr(fs.ledger, name))
        others = [a for a in sig.parameters if a != "wavelength_um"]
        kw = p.for_op(name, data=others)
        assert kw == {"wavelength_um": 0.55}, name
        seen += 1
    assert seen == len(ops) >= 15


def test_every_wavelength_nm_op_gets_converted_value_from_um_bundle():
    ops = _ledger_ops_with("wavelength_nm")
    p = fs.ParamBundle({"wavelength": "0.55 um"})
    for name in ops:
        others = [a for a in inspect.signature(getattr(fs.ledger, name)).parameters if a != "wavelength_nm"]
        assert p.for_op(name, data=others) == {"wavelength_nm": 550.0}, name
    assert len(ops) >= 8


def test_run_end_to_end_real_ops(rig):
    rng = np.random.default_rng(3)
    img = rng.random((40, 56))
    # 1. カメラ K を受ける op(facade)
    out = fs.run_params("undistort_image", img, params=rig, warn_unused=False)
    assert out.shape == img.shape and np.allclose(out, fs.undistort_image(img, rig.K("camera"), np.array([-0.12, 0.03, 0, 0, 0])))
    pts = np.array([[0.1, 0.2, 2.0], [0.0, 0.0, 1.0]])
    uv = fs.run_params("project_points", pts, params=rig, warn_unused=False)
    assert uv.shape == (2, 2) and np.allclose(uv[1], [640.0, 480.0])
    # 2. 波長・画素ピッチ・f 値を受ける op(台帳): 結果が直接呼びと一致
    psf = fs.run_params("airy_pattern", params=rig, warn_unused=False)
    assert np.array_equal(psf, fs.ledger.airy_pattern(wavelength_um=0.55, f_number=4.0, pixel_pitch_um=3.45))
    assert psf.shape == (64, 64) and float(psf.max()) > 0
    # 3. 画素ピッチを受ける op に前の結果を渡す(データは位置引数)
    mtf = fs.run_params("psf_to_mtf", psf, params=rig, warn_unused=False)
    ref = fs.ledger.psf_to_mtf(psf, pixel_pitch_um=3.45)
    assert str(type(mtf)) == str(type(ref))
    # 4. 波長を nm で受ける op
    r = fs.run_params("airy_radius_um", params=rig, warn_unused=False)
    assert r == fs.ledger.airy_radius_um(f_number=4.0, wavelength_nm=550.0)
    # 5. 焦点 mm を受ける op
    dof = fs.run_params("depth_of_field", params=rig, warn_unused=False)
    assert dof == fs.ledger.depth_of_field(focal_mm=25, f_number=4.0)
    # 6. 回折 MTF(波長 um + f 値)
    m = fs.run_params("mtf_diffraction", params=rig, warn_unused=False)
    n = fs.ledger.mtf_diffraction(f_number=4.0, wavelength_um=0.55)
    assert type(m) == type(n)
    # 7. 台帳の別の op: 薄レンズ(焦点 mm)
    assert fs.run_params("thin_lens", params=rig, warn_unused=False) == fs.ledger.thin_lens(focal_mm=25)
    # 8. 進化する 2-D op(apply の a/b つまみ)は [op].a / [op].b
    g = fs.run_params("gaussian", img, params=fs.ParamBundle({"gaussian.a": 0.7}))
    assert np.allclose(g, fs.apply(img, "gaussian", 0.7, 0.5))


def test_run_overrides_win_and_unused_warning(rig):
    img = np.random.default_rng(1).random((24, 24))
    with pytest.warns(PB.ParamWarning, match="lens.wavelength"):
        fs.run_params("undistort_image", img, params=rig)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fs.run_params("undistort_image", img, params=rig, warn_unused=False)
    K2 = np.array([[500.0, 0, 12], [0, 500.0, 12], [0, 0, 1]])
    a = fs.run_params("undistort_image", img, params=rig, warn_unused=False, K=K2)             # 明示の K が束より優先
    assert np.allclose(a, fs.undistort_image(img, K2, np.array([-0.12, 0.03, 0, 0, 0])))
    d = fs.run_params("depth_of_field", params={"focal": "50 mm", "f_number": 8.0})              # 辞書もそのまま束にできる
    assert d == fs.ledger.depth_of_field(focal_mm=50, f_number=8.0)
    with pytest.raises(PB.MissingParam):
        fs.run_params("undistort_image", img, params=None)
    f = fs.run_params("depth_of_field", params=None, focal_mm=50.0, f_number=8.0)
    assert f == d


def test_run_loads_a_path(tmp_path):
    f = _write(tmp_path / "rig.toml", RIG_TOML)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.run_params("undistort_image", np.zeros((16, 16)), params=f)
    assert out.shape == (16, 16)


# ---------------------------------------------------------------------------------------------
# 既存の契約を変えていない・公開の名前
# ---------------------------------------------------------------------------------------------
def test_public_names_and_existing_contracts_unchanged():
    names = ["ParamBundle", "load_params", "save_params", "params_compare", "param_grid", "param_zip", "sweep", "run_params",
             "ParamError", "MissingParam"]
    assert len(names) == 10
    for n in names:
        assert hasattr(fs, n) and n in fs.__all__, n
    assert "params" not in inspect.signature(fs.apply).parameters                   # fs.apply の契約を変えていない
    assert list(inspect.signature(fs.apply).parameters)[:4] == ["image", "name", "a", "b"]
    assert str(inspect.signature(fs.undistort_image)) == "(image, K, dist)"          # 既存 op の引数を変えていない
    assert fs.load_json is not fs.load_params and fs.load is not fs.load_params     # 画像 / jsonio の入口と衝突しない


def test_pyproject_declares_yaml_as_optional_extra_only():
    toml = io.open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    import tomllib
    meta = tomllib.loads(toml)["project"]
    assert meta["optional-dependencies"]["yaml"] == ["PyYAML>=6.0"]
    assert not any("yaml" in d.lower() for d in meta.get("dependencies", []))
    # 本体は PyYAML を top-level で import しない(無くても import fullseye が通る)
    src = io.open(os.path.join(ROOT, "fullseye", "parambundle.py"), encoding="utf-8").read()
    assert not re.search(r"^import yaml|^from yaml", src, re.M)


# ---------------------------------------------------------------------------------------------
# 文書の例が本当に動く
# ---------------------------------------------------------------------------------------------
def test_doc_first_example_runs(tmp_path):
    """docs/PARAM_BUNDLE.md の最初の例(rig.toml)をそのまま読んで undistort に渡せる。"""
    doc = io.open(os.path.join(ROOT, "docs", "PARAM_BUNDLE.md"), encoding="utf-8").read()
    blocks = re.findall(r"```toml\n(.*?)```", doc, re.S)
    assert len(blocks) == 1
    p = fs.load_params(_write(tmp_path / "rig.toml", blocks[0]))
    assert list(p) == RIG_KEYS and len(p) == 9
    kw = p.for_op("undistort_image")
    assert sorted(kw) == ["K", "dist"]
    assert fs.undistort_image(np.zeros((8, 8)), **kw).shape == (8, 8)
    # 文書が名前を挙げている公開名はすべて実在する
    for n in re.findall(r"fs\.(\w+)\(", doc):
        assert hasattr(fs, n) or hasattr(fs.ledger, n) or hasattr(fs.parambundle, n), n
    assert "SYNONYM_GROUPS" in doc and hasattr(fs.parambundle, "SYNONYM_GROUPS")


# ---------------------------------------------------------------------------------------------
# 検分の直し(2026-11-12): with_ の打ち間違い・空の for_op・次元違い
# ---------------------------------------------------------------------------------------------
def test_with_refuses_unknown_keys_and_added_is_the_explicit_way(rig):
    with pytest.raises(PB.ParamError, match=r"camera\.fxx.*did you mean camera\.fx"):
        rig.with_(**{"camera.fxx": 1})
    with pytest.raises(PB.ParamError, match="not in bundle"):
        rig.with_(brand_new=1)
    with pytest.raises(PB.ParamError):
        rig.with_(camera={"fx": 1, "zz": 2})                                  # 入れ子でも 1 つでも未知があれば断る
    r = rig.with_(**{"camera.fx": 820})                                       # 既にあるキーは従来どおり
    assert r["camera.fx"] == 820 and len(r) == len(rig)
    a = rig.added(**{"camera.k4": 0.5, "camera.fx": 700})                     # 明示なら足せる(上書きも可)
    assert a["camera.k4"] == 0.5 and a["camera.fx"] == 700 and len(a) == len(rig) + 1 and "camera.k4" not in rig
    assert a.origin("camera.k4").source == "<code>"


def test_param_grid_axis_typo_refused_unless_allow_new(rig):
    with pytest.raises(PB.ParamError, match=r"lens\.f_numbr.*did you mean lens\.f_number"):
        fs.param_grid(rig, **{"lens.f_numbr": [1, 2]})
    with pytest.raises(PB.ParamError, match="axis key"):
        fs.param_zip(rig, **{"lens.nope": [1, 2]})
    assert len(fs.param_grid(rig, allow_new=True, **{"lens.nope": [1, 2]})) == 2
    assert len(fs.param_grid(rig, **{"lens.f_number": [1, 2]})) == 2


def test_merged_new_keys_are_visible_in_compare(rig):
    extra = fs.ParamBundle({"camera.k4": 0.5}, name="extra")
    m = rig.merged(extra)
    row = fs.params_compare([rig, m])["camera.k4"]
    assert row.status == "partial" and row.values == (None, 0.5)             # 上に重ねた側にしか無いキーが見える


def test_for_op_empty_result_is_explained_and_can_be_refused():
    other = fs.ParamBundle({"unrelated.thing": 1, "camera.fx": 1200.0})
    assert other.for_op("depth_of_field") == {}                               # 既定はこれまでどおり返る
    kw, rep = other.for_op("depth_of_field", report=True)
    assert kw == {} and rep.entries == [] and rep.candidates == ["focal_mm", "f_number", "subject_mm", "coc_mm"]
    with pytest.raises(PB.MissingParam, match=r"no key of bundle <code> applies.*focal_mm.*unrelated\.thing") as ei:
        other.for_op("depth_of_field", require_any=True)
    assert "camera.fx" in str(ei.value)
    with pytest.raises(PB.MissingParam, match="applies to this op"):
        other.for_op("depth_of_field", strict=True)                           # strict は未使用キーより先にこれを言う
    # 何か 1 つでも当たれば require_any は通る
    assert fs.ParamBundle({"f_number": 8.0}).for_op("depth_of_field", require_any=True) == {"f_number": 8.0}
    # 探す引数が無い(全部データ扱い)ときは空でも断らない
    assert other.for_op("airy_pattern", data=["size", "wavelength_um", "f_number", "pixel_pitch_um"], require_any=True) == {}


def test_run_params_warns_when_nothing_was_passed():
    other = fs.ParamBundle({"unrelated.thing": 1})
    with pytest.warns(PB.ParamWarning, match="no key of bundle <code> applies to this op.*focal_mm"):
        out = fs.run_params("depth_of_field", params=other)
    assert out == fs.ledger.depth_of_field()                                  # 既定値で走る(警告つき)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fs.run_params("depth_of_field", params=other, warn_unused=False)      # 黙らせられる
        fs.run_params("depth_of_field", params=None)                          # 束なし(空)は警告しない
        fs.run_params("depth_of_field", params=other, warn_unused=False, focal_mm=50.0, f_number=8.0)
    with pytest.raises(PB.MissingParam):
        fs.run_params("depth_of_field", params=other, strict=True)


def test_quantity_of_wrong_dimension_is_refused_for_real_ops():
    """``wavelength: 550 ms``(時間)を波長の引数へ。実在の op(mtf_diffraction: wavelength_um, airy_radius_um: wavelength_nm)。"""
    bad = fs.ParamBundle({"wavelength": "550 ms", "f_number": 4.0})
    with pytest.raises(PB.UnitMismatch, match=r"wavelength = 550 ms is a time but wavelength_um needs a length \(um\)"):
        bad.for_op("mtf_diffraction")
    with pytest.raises(PB.UnitMismatch, match=r"is a time but wavelength_nm needs a length \(nm\)"):
        bad.for_op("airy_radius_um")
    with pytest.raises(PB.UnitMismatch, match="time"):
        fs.run_params("mtf_diffraction", params=bad)
    for unit in ("hz", "px", "deg"):
        with pytest.raises(PB.UnitMismatch):
            fs.ParamBundle({"wavelength": "5 %s" % unit}).for_op("mtf_diffraction", data=["f_number"])
    # 正しい次元は通る(対照)
    assert fs.ParamBundle({"wavelength": "550 nm"}).for_op("mtf_diffraction", data=["f_number"]) == {"wavelength_um": 0.55}
