# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drawlist(蓄積 → フラッシュ)の規律を機械で固定する。

この層の主張は 4 つで、そのそれぞれに検査がある:

1. **足すだけ** ―― 即時描画と蓄積描画が **画素完全一致**する
   (:func:`test_deferred_matches_immediate_bit_for_bit`)。ここが崩れると、既存の
   展示 141 点の SHA-256 が変わりうる。
2. **絵になる前に検査できる** ―― 文字のはみ出し・画像外・未知の役割名を、
   ラスタ化せずに、**どのコマンドか**を添えて捕まえる。
3. **構造で差分が取れる** ―― JSON 往復が完全一致し、差分が「何が変わったか」で出る。
4. **別解像度へ流せる** ―― ``scale`` した列の結果が、拡大した結果と再標本化の
   誤差の範囲で一致する(誤差は数字で出す)。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import drawlist as DL                                    # noqa: E402
import imagedraw as ID                                   # noqa: E402
from drawlist import DrawList, DrawListError             # noqa: E402
from drawstyle import DrawStyle                          # noqa: E402

H, W = 120, 160
POLY = [[20.0, 20.0], [140.0, 30.0], [120.0, 100.0], [30.0, 90.0]]


def _sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


def _scene(dl: DrawList) -> DrawList:
    """検査を通る、代表的な図形をひと通り含む場面。"""
    dl.line((5, 5), (150, 110), color="wrong", width=2)
    dl.circle((80, 60), 30, color="right", width=3)
    dl.markers([[20, 20], [60, 40], [140, 100]], color=0.9, size=5)
    dl.polyline(POLY, color="emphasis", width=1, closed=True)
    return dl


# --------------------------------------------------------------------------- #
# 1. 足すだけ ―― 即時方式と画素が完全に一致する                                  #
# --------------------------------------------------------------------------- #
def test_deferred_matches_immediate_bit_for_bit():
    """同じ描画を即時方式と蓄積方式で行い、**1 画素も違わない**ことを固定する。

    これが「蓄積は足すだけで、既存の図は 1 ビットも変わらない」の証明になる。
    """
    img_now = ID.new_canvas((H, W, 3))
    img_now = ID.draw_line(img_now, (5, 5), (150, 110), color="wrong", width=2)
    img_now = ID.draw_circle(img_now, (80, 60), 30, color="right", width=3)
    img_now = ID.draw_markers(img_now, [[20, 20], [60, 40], [140, 100]], color=0.9, size=5)
    img_now = ID.draw_polyline(img_now, POLY, color="emphasis", width=1, closed=True)

    img_later = _scene(DrawList((H, W, 3))).flush()

    assert img_later.shape == img_now.shape
    assert img_later.dtype == img_now.dtype
    assert np.array_equal(img_later, img_now), (
        "deferred flush differs from the immediate calls; max |diff| = "
        f"{np.abs(img_later - img_now).max()}")
    assert _sha(img_later) == _sha(img_now)


def test_deferred_matches_immediate_with_a_style_value():
    """``DrawStyle`` を積んでも即時方式と一致する(スタイルは往復しても値のまま)。"""
    st = DrawStyle(color="wrong", width=2, line_style="dashed")
    now = ID.draw_polyline(ID.new_canvas((H, W, 3)), POLY, closed=True, style=st)
    later = DrawList((H, W, 3)).polyline(POLY, closed=True, style=st).flush()
    assert np.array_equal(now, later)


def test_flush_does_not_destroy_the_base_image():
    base = ID.new_canvas((H, W, 3), color=0.25)
    keep = base.copy()
    DrawList((H, W, 3)).line((5, 5), (150, 110), color=1.0).flush(base=base)
    assert np.array_equal(base, keep)


def test_flushing_twice_gives_the_same_bytes():
    """同じコマンド列 → 同じバイト列(2 回流して SHA-256 一致)。"""
    dl = _scene(DrawList((H, W, 3)))
    a, b = dl.flush(), dl.flush()
    assert _sha(a) == _sha(b)
    # 別インスタンスで組み直しても同じ(モジュールに状態が残っていない)
    assert _sha(_scene(DrawList((H, W, 3))).flush()) == _sha(a)


# --------------------------------------------------------------------------- #
# 2. z 順                                                                      #
# --------------------------------------------------------------------------- #
def test_z_order_decides_who_is_on_top():
    """z の上下を入れ替えると、重なった画素の色が入れ替わる。"""
    red, blue = (0.9, 0.1, 0.1), (0.1, 0.1, 0.9)
    a = (DrawList((H, W, 3))
         .circle((80, 60), 30, color=red, fill=True, z=0.0)
         .circle((90, 60), 30, color=blue, fill=True, z=1.0)).flush()
    b = (DrawList((H, W, 3))
         .circle((80, 60), 30, color=red, fill=True, z=1.0)
         .circle((90, 60), 30, color=blue, fill=True, z=0.0)).flush()
    overlap = (85, 60)                                    # 両方の円に入る点 (x, y)
    px_a, px_b = a[overlap[1], overlap[0]], b[overlap[1], overlap[0]]
    assert np.allclose(px_a, blue), f"z=1 の青が上に来ていない: {px_a}"
    assert np.allclose(px_b, red), f"z=1 の赤が上に来ていない: {px_b}"
    assert not np.array_equal(a, b)


def test_equal_z_keeps_insertion_order():
    """同じ z なら **積んだ順**。安定ソートであることを画素で確かめる。"""
    red, blue = (0.9, 0.1, 0.1), (0.1, 0.1, 0.9)
    img = (DrawList((H, W, 3))
           .circle((80, 60), 30, color=red, fill=True, z=2.5)
           .circle((80, 60), 30, color=blue, fill=True, z=2.5)).flush()
    assert np.allclose(img[60, 80], blue)


def test_non_finite_z_is_refused_with_the_command_index():
    dl = DrawList((H, W, 3)).line((5, 5), (10, 10), color=1.0)
    dl.circle((80, 60), 10, color=1.0, z=float("nan"))
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.index == 1 and e.value.code == "z_not_finite"
    assert "command[1]" in str(e.value) and "circle" in str(e.value)


# --------------------------------------------------------------------------- #
# 3. フラッシュ前検査(絵にする前に捕まえる)                                     #
# --------------------------------------------------------------------------- #
def test_text_that_cannot_fit_is_caught_before_rasterising():
    """文字のはみ出しは **画素からは判定できない**が、列の上では計算できる。"""
    dl = DrawList((H, W, 3))
    dl.text_box((10, 10), "この文字列は画像の幅にはどうやっても収まらない長さです", font_size=14)
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.code == "text_does_not_fit" and e.value.index == 0
    assert "command[0]" in str(e.value) and "text_box" in str(e.value)


def test_text_running_off_the_right_edge_is_caught():
    dl = DrawList((H, W, 3)).text_box((140, 10), "hello world", font_size=12)
    issues = [i for i in dl.inspect() if i["code"] == "text_does_not_fit"]
    assert len(issues) == 1
    assert "right" in issues[0]["message"]


def test_a_text_box_that_fits_is_drawn_through_the_handler():
    """収まる文字は素通しし、委譲先(ここでは差し替えたハンドラ)へ渡る。"""
    seen = {}

    def handler(img, xy=None, text=None, font_size=None, **kw):
        seen.update(xy=xy, text=text, font_size=font_size)
        out = np.array(img)
        out[int(xy[1]), int(xy[0])] = 1.0
        return out

    dl = DrawList((H, W, 3), handlers={"text_box": handler})
    dl.text_box((10, 10), "ok", font_size=12)
    img = dl.flush()
    assert seen == {"xy": [10.0, 10.0], "text": "ok", "font_size": 12.0}
    assert np.allclose(img[10, 10], 1.0)


def test_drawing_outside_the_image_is_refused():
    dl = DrawList((H, W, 3)).line((5, 5), (500, 500), color=1.0)
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.code == "out_of_bounds" and e.value.index == 0
    # allow_clip=True なら警告へ降りて、描ける(ラスタ層のクランプに任せる)
    dl2 = DrawList((H, W, 3), allow_clip=True).line((5, 5), (500, 500), color=1.0)
    assert dl2.flush().shape == (H, W, 3)
    assert any(i["code"] == "out_of_bounds" and i["severity"] == "warning"
               for i in dl2.inspect())


def test_unknown_colour_role_is_refused_with_the_command_index():
    dl = DrawList((H, W, 3)).circle((80, 60), 10, color="mostly_right")
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.code == "unknown_role" and e.value.index == 0
    assert "mostly_right" in str(e.value)


def test_unknown_command_kind_is_refused():
    dl = DrawList((H, W, 3)).add("draw_a_nice_thing", 0.0, pos=[1, 1])
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.code == "unknown_command" and e.value.index == 0


def test_label_collision_and_low_contrast_are_warnings_not_errors():
    """絵を見ないと気づけない 2 件 ―― 既定では通し、``strict`` で止める。"""
    dl = DrawList((H, W, 3), handlers={"text_box": lambda img, **kw: img})
    dl.text_box((10, 10), "alpha", font_size=12)
    dl.text_box((14, 12), "beta", font_size=12)            # 箱が重なる
    dl.text_box((10, 60), "ghost", font_size=12, text_color=0.10, box_color=0.12)
    codes = {i["code"] for i in dl.inspect()}
    assert "label_collision" in codes and "low_contrast" in codes
    assert all(i["severity"] == "warning" for i in dl.inspect())
    dl.flush()                                             # 既定は通る
    with pytest.raises(DrawListError) as e:
        dl.flush(strict=True)
    assert e.value.code in ("label_collision", "low_contrast")


def test_check_codes_documents_every_code_the_inspector_emits():
    """検査が出すコードは全部 :meth:`DrawList.check_codes` に説明がある。"""
    dl = DrawList((10, 10), handlers={"text_box": lambda img, **kw: img}, allow_clip=True)
    dl.text_box((0, 0), "far too long a label for ten pixels", font_size=8)
    dl.text_box((0, 0), "x", font_size=8)
    dl.add("nope", 0.0)
    dl.circle((99, 99), 50, color="not_a_role")
    dl.line((0, 0), (5, 5), color=0.5, z=float("inf"))
    emitted = {i["code"] for i in dl.inspect()}
    assert emitted <= set(DrawList.check_codes()), emitted - set(DrawList.check_codes())
    assert len(emitted) >= 5


# --------------------------------------------------------------------------- #
# 4. 遅延解決(層がまだ無くても、その op だけが落ちる)                            #
# --------------------------------------------------------------------------- #
def test_a_missing_layer_fails_only_that_command_and_says_so(monkeypatch):
    """まだ着地していない層のコマンドは、**その op だけ**が明示エラーになる。

    ここでは「委譲先の層がまだ無い」状況を、存在しないモジュールを指す種別を
    一時的に足して作る(``monkeypatch`` なので試験の後で必ず元に戻る)。
    """
    monkeypatch.setitem(DL.COMMAND_SPECS, "not_yet_a_layer",
                        DL.CommandSpec("not_yet_a_layer", "layer_that_does_not_exist",
                                       ("draw_something",)))
    dl = DrawList((H, W, 3))
    dl.line((5, 5), (100, 100), color=1.0)
    dl.add("not_yet_a_layer", 0.0, radius=3)
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.code == "handler_missing" and e.value.index == 1
    assert "layer_that_does_not_exist" in str(e.value) and "handlers=" in str(e.value)
    # 同じ列でも、その op を外せば残りは描ける(落ちるのは 1 コマンドだけ)
    ok = DrawList((H, W, 3)).line((5, 5), (100, 100), color=1.0).flush()
    assert ok.max() > 0


def test_the_named_layers_resolve_to_the_real_functions():
    """委譲表が **実在の関数**を指していること(名前の当て推量が残っていない)。"""
    dl = DrawList((H, W, 3))
    for kind, spec in sorted(DL.COMMAND_SPECS.items()):
        fn = dl.resolve(kind)
        assert callable(fn), kind
        assert fn.__module__ in (spec.module, "fullseye", "api"), (kind, fn.__module__)


def test_deferred_matches_immediate_across_all_three_layers():
    """3 つの層(プリミティブ・図注・2-D グラフィックス)を跨いでも画素が完全一致する。

    ここまで一致するなら、蓄積方式は既存の図の作り方を **置き換えず足している**
    と言い切れる。
    """
    import annotate as A
    import gfx2d as G

    now = ID.new_canvas((H, W, 3), color=0.3)
    now = ID.draw_circle(now, (80, 60), 24, color="reference", fill=True)
    now = A.arrow(now, (10, 10), (100, 100))
    now = A.text_box(now, "hi there", (10, 10), font_size=12)
    now = G.vignette(now, strength=0.5)

    dl = DrawList((H, W, 3), background=0.3)
    dl.circle((80, 60), 24, color="reference", fill=True, z=0.0)
    dl.arrow((10, 10), (100, 100), z=1.0)
    dl.text_box((10, 10), "hi there", font_size=12, z=2.0)
    dl.vignette(z=3.0, strength=0.5)
    later = dl.flush()

    assert np.array_equal(now, later), f"max|diff| = {np.abs(now - later).max()}"
    assert _sha(now) == _sha(later)


def test_the_default_text_metric_uses_the_real_measurer_when_available():
    """文字の当たり判定は、実測が使えるなら見積りではなく **実測**を使う。"""
    import annotate as A

    modelled = DL.default_text_metrics("hello world", 14.0)
    measured = DL.measured_text_metrics("hello world", 14.0)
    real = A.measure_text("hello world", font_size=14)
    assert measured == (float(real["width"]), float(real["height"]))
    assert measured != modelled                            # 実測と見積りは別物


def test_handlers_take_priority_over_the_named_layers():
    calls = []

    def fake_line(img, **kw):
        calls.append(kw)
        return img

    DrawList((H, W, 3), handlers={"line": fake_line}).line((1, 1), (2, 2), color=1.0).flush()
    assert calls and calls[0]["color"] == 1.0


def test_a_failing_handler_is_reported_with_its_command_index():
    def boom(img, **kw):
        raise RuntimeError("no")

    dl = DrawList((H, W, 3), handlers={"vignette": boom})
    dl.line((1, 1), (2, 2), color=1.0)
    dl.add("vignette", 0.0, strength=0.5)
    with pytest.raises(DrawListError) as e:
        dl.flush()
    assert e.value.index == 1 and e.value.code == "handler_failed"
    assert "RuntimeError" in str(e.value)


def test_resolution_happens_at_flush_not_at_import():
    """import 時に層を固定していない(モジュールの名前空間に層が入っていない)。"""
    for layer in ("imagedraw", "annotate", "gfx2d", "drawstyle", "palette"):
        assert not hasattr(DL, layer), f"drawlist が import 時に {layer} を抱えている"


# --------------------------------------------------------------------------- #
# 5. JSON 往復と構造の差分                                                      #
# --------------------------------------------------------------------------- #
def test_json_round_trip_is_exact():
    """往復でコマンド列が **完全一致**する(タプル/numpy/DrawStyle を含めて)。"""
    dl = _scene(DrawList((H, W, 3), background=(0.1, 0.1, 0.12)))
    dl.contour({"cs": [np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 20.0]])]}, color="neutral")
    dl.polyline(np.asarray(POLY), closed=True,
                style=DrawStyle(color="baseline", width=2, line_style=(6.0, 3.0)))
    back = DrawList.from_json(dl.to_json())
    assert back.commands == dl.commands
    assert back.shape == dl.shape
    assert back.to_json() == dl.to_json()
    # 往復した列を流しても同じ絵になる
    assert _sha(back.flush()) == _sha(dl.flush())


def test_json_is_plain_data():
    dl = _scene(DrawList((H, W, 3)))
    d = json.loads(dl.to_json())
    assert d["version"] == 1 and d["shape"] == [H, W, 3]
    assert [c["kind"] for c in d["commands"]] == ["line", "circle", "markers", "polyline"]


def test_from_json_refuses_a_broken_payload():
    with pytest.raises(DrawListError):
        DrawList.from_json(json.dumps({"shape": [4, 4], "commands": []}))          # version 無し
    with pytest.raises(DrawListError):
        DrawList.from_json(json.dumps({"version": 1, "shape": [4, 4],
                                       "commands": [{"kind": "line"}]}))           # 形が違う


def test_structural_diff_says_which_command_changed_and_how():
    """ハッシュは「変わった」しか言わないが、差分は「何が」まで言う。"""
    a = DrawList((H, W, 3), handlers={"text_box": lambda img, **kw: img})
    a.line((5, 5), (100, 100), color="wrong", width=2)
    a.text_box((10, 10), "before", font_size=12)
    b = DrawList.from_json(a.to_json())
    b._cmds[1]["args"]["text"] = "after"

    recs = DL.diff_command_lists(a, b)
    assert len(recs) == 1
    assert recs[0] == {"index": 1, "change": "changed", "kind": "text_box",
                       "field": "args.text", "old": "before", "new": "after"}
    assert DL.format_diff(recs) == ["command[1] text_box: args.text 'before' -> 'after'"]


def test_structural_diff_reports_added_removed_and_shape():
    a = DrawList((H, W, 3)).line((5, 5), (100, 100), color=1.0)
    b = DrawList((H, W // 2, 3)).line((5, 5), (100, 100), color=1.0)
    b.circle((40, 40), 10, color=1.0)
    changes = {(r["change"], r["field"]) for r in DL.diff_command_lists(a, b)}
    assert ("changed", "shape") in changes
    assert ("added", "") in changes
    assert {r["change"] for r in DL.diff_command_lists(b, a)} >= {"removed"}


# --------------------------------------------------------------------------- #
# 6. 別解像度へ流す                                                            #
# --------------------------------------------------------------------------- #
def test_scale_multiplies_geometry_but_not_colours_or_z():
    dl = DrawList((H, W, 3))
    dl.circle((80, 60), 30, color="right", width=3, fill=True, z=2.0)
    big = dl.scale(2.0)
    assert big.shape == (2 * H, 2 * W, 3)
    a = big.commands[0]["args"]
    assert a["center"] == [160.0, 120.0] and a["radius"] == 60.0 and a["width"] == 6.0
    assert a["color"] == "right" and a["fill"] is True
    assert big.commands[0]["z"] == 2.0
    assert dl.commands[0]["args"]["radius"] == 30.0        # 元の列は変わらない


def test_scale_divides_the_per_pixel_physical_scale():
    """``units_per_pixel`` は倍率で **割る**。掛けると図の寸法表示が静かに嘘になる。

    2 倍の解像度で描けば 1 画素が表す物理長は半分になる。バーの物理長
    (``length``)は世界の量なので変わらない。
    """
    dl = DrawList((H, W, 3)).scalebar(50.0, 0.8, thickness=5, xy=(20, 100))
    big = dl.scale(2.0).commands[0]["args"]
    assert big["length"] == 50.0                           # 物理量は不変
    assert big["units_per_pixel"] == pytest.approx(0.4)    # 画素あたりは半分
    assert big["thickness"] == 10.0 and big["xy"] == [40.0, 200.0]
    # 図に出る「バーの画素長」= length / units_per_pixel は倍になる(= 正しい)
    assert (50.0 / 0.8) * 2 == pytest.approx(big["length"] / big["units_per_pixel"])


def test_scale_refuses_a_factor_that_leaves_no_pixels():
    with pytest.raises(ValueError):
        DrawList((4, 4)).scale(0.0)
    with pytest.raises(ValueError):
        DrawList((4, 4)).scale(0.1)


def test_scale_is_consistent_with_resampling_the_flushed_image():
    """2 倍の列を流した絵 ≈ 1 倍を流して 2 倍に拡大した絵(誤差は数字で出す)。

    完全一致はしない ―― 拡大は元の標本しか持たないのに対し、2 倍で描いた線は
    2 倍の解像度で改めて標本化されるので、輪郭の 1 画素幅の縁がずれる。ここで
    固定するのは「その差が **縁だけ**に留まる」ことである。
    """
    dl = DrawList((H, W, 3))
    dl.circle((80, 60), 30, color=(0.2, 0.6, 0.9), fill=True)
    dl.polyline(POLY, color=(0.9, 0.5, 0.1), width=3, closed=True)

    small = dl.flush()
    big = dl.scale(2.0).flush()
    up = np.repeat(np.repeat(small, 2, axis=0), 2, axis=1)

    assert up.shape == big.shape
    diff = np.abs(up - big)
    mean_abs = float(diff.mean())
    frac = float((diff.max(axis=2) > 1e-9).mean())
    print(f"\nscale consistency: mean|diff| = {mean_abs:.5f}, "
          f"differing pixels = {frac * 100:.2f} %")
    assert mean_abs < 0.02, f"mean |diff| = {mean_abs}"
    assert frac < 0.06, f"differing pixels = {frac}"


# --------------------------------------------------------------------------- #
# 7. 状態を持たないこと                                                        #
# --------------------------------------------------------------------------- #
def test_the_module_keeps_no_mutable_drawing_state():
    """モジュールに可変の描画状態を置いていない(並行する生成器がレースしない)。"""
    before = json.dumps({k: [v.kind, v.module, list(v.candidates), list(v.points),
                             list(v.lengths), list(v.paths)]
                         for k, v in sorted(DL.COMMAND_SPECS.items())})
    dl = _scene(DrawList((H, W, 3)))
    dl.flush()
    dl.scale(2.0).flush()
    after = json.dumps({k: [v.kind, v.module, list(v.candidates), list(v.points),
                            list(v.lengths), list(v.paths)]
                        for k, v in sorted(DL.COMMAND_SPECS.items())})
    assert before == after
    # 描画状態を持ちうる型がモジュール属性に無いこと
    import contextvars
    assert not [n for n, v in vars(DL).items()
                if isinstance(v, contextvars.ContextVar)]


def test_two_lists_do_not_leak_into_each_other():
    a = DrawList((H, W, 3))
    b = DrawList((H, W, 3))
    a.line((5, 5), (100, 100), color=1.0)
    assert len(b) == 0
    assert _sha(b.flush()) == _sha(ID.new_canvas((H, W, 3)))


def test_commands_property_is_a_copy():
    dl = _scene(DrawList((H, W, 3)))
    got = dl.commands
    got[0]["args"]["color"] = "tampered"
    assert dl.commands[0]["args"]["color"] == "wrong"


# --------------------------------------------------------------------------- #
# 8. 入力の検証                                                                #
# --------------------------------------------------------------------------- #
def test_shape_is_validated_like_the_raster_layer():
    for bad in [(0, 10), (10,), (10, 10, 10, 10), (10.5, 10), (True, 4)]:
        with pytest.raises(ValueError):
            DrawList(bad)


def test_non_serialisable_arguments_are_refused_at_append_time():
    """絵になる前どころか、**積む時点で**列が JSON でなくなることを止める。"""
    with pytest.raises(TypeError):
        DrawList((H, W, 3)).add("line", 0.0, p0=object(), p1=(1, 1))


def test_text_metrics_can_be_replaced_by_a_real_measurer():
    """既定の字送り比は見積り。本物の計測関数を渡せばそちらが効く。"""
    dl = DrawList((H, W, 3), text_metrics=lambda t, s: (1000.0, 1000.0))
    dl.text_box((1, 1), "x", font_size=4)
    assert [i["code"] for i in dl.inspect()] == ["text_does_not_fit"]
    ok = DrawList((H, W, 3), text_metrics=lambda t, s: (1.0, 1.0),
                  handlers={"text_box": lambda img, **kw: img})
    ok.text_box((1, 1), "x" * 500, font_size=4)
    assert ok.inspect() == []


def test_default_text_metrics_matches_the_documented_model():
    w, h = DL.default_text_metrics("abcd", 10.0)
    assert w == pytest.approx(DL.TEXT_ADVANCE_RATIO * 10.0 * 4)
    assert h == pytest.approx(10.0)
    w2, h2 = DL.default_text_metrics("ab\ncdef", 10.0)
    assert w2 == pytest.approx(DL.TEXT_ADVANCE_RATIO * 10.0 * 4) and h2 == pytest.approx(20.0)


def test_flush_buffer_is_the_same_operation_under_another_name():
    dl = _scene(DrawList((H, W, 3)))
    assert _sha(dl.flush_buffer()) == _sha(dl.flush())
    assert _sha(DL.flush_buffer(dl)) == _sha(dl.flush())


if __name__ == "__main__":                                 # pragma: no cover
    pytest.main([__file__, "-q"])
