# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""グリフ照合の門 —— 「認識せずに、指定した字と合っているか測る」が成り立つ条件を固定する。

ここで守るのは 5 つ:

1. **描けない字で豆腐を返さない**(欠字は例外にする)。
2. **距離は平均でなく分位点**(部首を共有する取り違えが平均では消える)。
3. **閾値は書体雑音から導く**(勘で置かない)。
4. **太さで比べない**(骨格で比べる)。
5. **色が多峰なら「できない」と返す**(縁取り文字を黙って汚さない)。
"""
from __future__ import annotations

import os

import numpy as np
import pytest

pytest.importorskip("PIL")
pytest.importorskip("skimage")

import glyphops  # noqa: E402

#: 床を測るのに使う字。常用で、画数の幅があるものを混ぜる。
_CHARS = "電気設備点検中工事徐行願立入禁止関係者以外非常口避難場所"


@pytest.fixture(scope="module")
def fonts():
    fs = glyphops.available_fonts()
    if len(fs) < 2:
        pytest.skip(f"CJK フォントが {len(fs)} 本しかない(床は書体の散らばりなので 2 本要る)")
    return fs


def test_a_font_that_cannot_draw_the_character_raises_instead_of_drawing_tofu(fonts):
    """★「フォントを開けた」は「その字が描けた」ではない。

    欠字は例外を出さず ``.notdef``(□)という**正当な絵**を返す。実測では
    ``mingliub.ttc`` の index 0 が全部の漢字を豆腐にしていて、気づいたのは
    ``山`` と ``直`` の統計が**完全に一致**したからだった。黙って □ を返すと、
    下流の距離が「それらしい値」になって嘘をつく。
    """
    import os
    tofu = r"C:\Windows\Fonts\mingliub.ttc"
    if not os.path.exists(tofu):
        pytest.skip("豆腐を返すフォントがこの環境に無い")
    with pytest.raises(ValueError):
        glyphops.render_glyph("電", tofu)
    assert tofu not in glyphops.available_fonts(), "描けないフォントが候補に残っている"


def test_the_distance_must_be_a_high_quantile_not_the_mean(fonts):
    """★平均では**部首を共有する取り違え**が消える。

    ``検``→``横`` は木偏を共有するので、違いは骨格の一部に集中する。平均を取ると
    書体雑音の床より下に沈み、**原理的に検出できなくなる**。分位点なら残る。
    """
    a = glyphops.render_glyph("検", fonts[0], 160)
    b = glyphops.render_glyph("横", fonts[0], 160)
    mean_like = glyphops.glyph_distance(a, b, 160, quantile=0.5)
    tail = glyphops.glyph_distance(a, b, 160, quantile=0.99)
    assert tail > 3.0 * mean_like, (
        f"分位点が平均を引き離せていない(平均側 {mean_like:.4f} / 99% {tail:.4f}) —— "
        "この比が縮むと、部首を共有する取り違えが床の下に沈む")


def test_the_threshold_comes_from_the_typeface_noise_not_from_a_guess(fonts):
    """床は**同じ字を別の書体で描いた距離**から出す。別字はその上に来ること。"""
    nf = glyphops.typeface_noise_floor(_CHARS, fonts, size=160, out=160)
    assert nf["n_fonts"] == len(fonts) and nf["n_pairs"] > 0
    assert 0.0 < nf["median"] < nf["floor"] <= nf["max"]
    gs = {c: glyphops.render_glyph(c, fonts[0], 160) for c in _CHARS}
    cl = list(_CHARS)
    sig = np.array([glyphops.glyph_distance(gs[cl[i]], gs[cl[j]], 160)
                    for i in range(len(cl)) for j in range(i + 1, len(cl))])
    below = float((sig < nf["floor"]).mean())
    assert below <= 0.02, (
        f"別字の {below:.1%} が書体雑音の床({nf['floor']:.4f})より下 —— "
        "床が高すぎるか、距離が形の違いを拾えていない")


def test_only_one_font_cannot_show_the_floor(fonts):
    """★書体 1 本では床は測れない(散らばりが無い)。黙って 0 を返さず断ること。"""
    with pytest.raises(RuntimeError):
        glyphops.typeface_noise_floor("電", fonts[:1])


def test_the_comparison_does_not_depend_on_stroke_weight(fonts):
    """★生の重なりは**線の太さに支配される**。骨格で比べれば太らせても壊れない。

    書体間でインク率が 0.053〜0.157(約 3 倍)違い、太さ込みで比べたときは
    「同一地域の書体差 > 同一書体の地域差」という**結論の反転**が起きた。
    """
    from scipy import ndimage
    g = glyphops.render_glyph("電", fonts[0], 160)
    fat = ndimage.grey_dilation(g, size=7)      # 5 ではインク率 1.45 倍で前提に届かない
    assert fat.mean() > 1.5 * g.mean(), "太らせたつもりが太っていない(前提が崩れている)"
    d_same = glyphops.glyph_distance(g, fat, 160)
    d_other = glyphops.glyph_distance(g, glyphops.render_glyph("窆", fonts[0], 160), 160)
    assert d_same < 0.5 * d_other, (
        f"太さの違い {d_same:.4f} が別字の違い {d_other:.4f} に匹敵している —— "
        "太さを落とせていない")


def test_a_subset_is_not_the_same_shape(fonts):
    """★片方向の距離では ``口`` が ``回`` の部分集合として距離 0 になる。対称で測ること。"""
    d = glyphops.glyph_distance(glyphops.render_glyph("口", fonts[0], 160),
                                glyphops.render_glyph("回", fonts[0], 160), 160)
    nf = glyphops.typeface_noise_floor("口回田日目", fonts, size=160, out=160)
    assert d > nf["floor"], f"口 と 回 の距離 {d:.4f} が床 {nf['floor']:.4f} 以下"


def test_normalisation_keeps_the_aspect_ratio():
    """★縦横比を潰すと「細長い字」と「正方の字」が同じ形になる。"""
    tall = np.zeros((80, 20)); tall[5:75, 5:15] = 1.0
    wide = np.zeros((20, 80)); wide[5:15, 5:75] = 1.0
    nt, nw = glyphops.normalise_glyph(tall), glyphops.normalise_glyph(wide)
    ht = nt.any(axis=1).sum() / max(1, nt.any(axis=0).sum())
    hw = nw.any(axis=1).sum() / max(1, nw.any(axis=0).sum())
    assert ht > 2.0 and hw < 0.5, (ht, hw)


def test_outlined_text_is_refused_rather_than_silently_repainted():
    """★縁取り文字では色が多峰になる。ここで「できない」と返せないと**確実に汚す**。"""
    img = np.zeros((64, 64, 3)); img[..., :] = 0.9          # 明るい地
    mask = np.zeros((64, 64), bool); mask[24:40, 24:40] = True
    plain = img.copy(); plain[mask] = 0.1                    # 黒い字
    ok = glyphops.ink_colors(plain, mask)
    assert ok["unimodal"] and ok["fg"].mean() < 0.3 and ok["bg"].mean() > 0.7

    outlined = plain.copy()
    from scipy import ndimage
    ring = ndimage.binary_dilation(mask, np.ones((7, 7))) & ~mask
    outlined[ring] = [0.95, 0.2, 0.2]                        # 赤い縁取り
    bad = glyphops.ink_colors(outlined, mask)
    assert not bad["unimodal"], "縁取りを単峰と判定した —— このまま塗ると縁を潰す"


def test_edge_width_does_not_invent_structure_in_a_flat_image():
    """★一様な入力では丸め屑が比に化ける。床は**相対量**で置くこと。"""
    flat = np.full((64, 64), 0.5)
    assert float(glyphops.edge_transition_width(flat).max()) == 0.0
    rng = np.random.default_rng(20260917)
    almost = flat + rng.normal(0, 1e-12, flat.shape)
    assert float(glyphops.edge_transition_width(almost).max()) == 0.0

    step = np.zeros((64, 64)); step[:, 32:] = 1.0
    w_sharp = float(np.median(glyphops.edge_transition_width(step)[:, 28:36]))
    from scipy import ndimage
    w_soft = float(np.median(glyphops.edge_transition_width(
        ndimage.gaussian_filter(step, 2.0))[:, 28:36]))
    assert w_soft > w_sharp + 1.0, (
        f"ぼけた段差 {w_soft:.2f} が鋭い段差 {w_sharp:.2f} より広くない —— "
        "遷移幅が実効 PSF を測れていない")


def _painted(ch, fonts, size=96, fg=(0.10, 0.10, 0.11), bg=(0.88, 0.80, 0.43)):
    """看板を模した 1 マス —— 単色の地に単色の字。"""
    a = glyphops.normalise_glyph(glyphops.render_glyph(ch, fonts[0], 160), size).astype(float)
    img = np.empty((size, size, 3))
    img[:] = np.asarray(bg)
    img[a > 0.5] = np.asarray(fg)
    return img, a > 0.5


def test_replacing_a_wrong_character_makes_it_match_the_intended_one(fonts):
    """★置換の本体 —— 直した後が**直す前より指定の字に近い**こと。

    ここが通らないと、検出だけして直せない道具になる。近さは
    :func:`glyph_distance` で測り、書体雑音の床を基準に判定する。
    """
    wrong, mask = _painted("横", fonts)                 # 本当は 検 と書きたかった
    out, err = glyphops.replace_glyph(wrong, mask, "検", fonts[0])
    assert err is None, err
    want = glyphops.normalise_glyph(glyphops.render_glyph("検", fonts[0], 160), 96)

    def _ink(rgb):
        return rgb.mean(axis=-1) < 0.5                  # 暗い側が字

    d_before = glyphops.glyph_distance(_ink(wrong).astype(float), want.astype(float), 96)
    d_after = glyphops.glyph_distance(_ink(out).astype(float), want.astype(float), 96)
    nf = glyphops.typeface_noise_floor("検横模様", fonts, size=160, out=96)
    assert d_after < d_before, f"置換しても近づいていない({d_before:.4f} -> {d_after:.4f})"
    assert d_after <= nf["floor"], (
        f"置換後の距離 {d_after:.4f} が書体雑音の床 {nf['floor']:.4f} を超えている")


def test_replacement_refuses_outlined_text_instead_of_wrecking_it(fonts):
    """★縁取りは**断る**。塗ってしまうと縁を潰して、直す前より悪くなる。"""
    from scipy import ndimage
    img, mask = _painted("横", fonts)
    ring = ndimage.binary_dilation(mask, np.ones((7, 7))) & ~mask
    img[ring] = [0.95, 0.2, 0.2]
    out, err = glyphops.replace_glyph(img, mask, "検", fonts[0])
    assert out is None and err and "単峰" in err, (out is None, err)


def test_the_replaced_stroke_weight_follows_the_surroundings(fonts):
    """★書体は選べないが**太さは合わせられる**。合わせないと直した字だけ浮く。"""
    from scipy import ndimage
    thin = glyphops.normalise_glyph(glyphops.render_glyph("検", fonts[0], 160), 96)
    bold = ndimage.binary_dilation(thin, np.ones((5, 5)))
    t_thin, t_bold = glyphops.stroke_thickness(thin), glyphops.stroke_thickness(bold)
    assert t_bold > t_thin + 1.0, (t_thin, t_bold)
    matched = glyphops.match_stroke_weight(thin.astype(float), t_bold)
    t_matched = glyphops.stroke_thickness(matched > 0.5)
    assert abs(t_matched - t_bold) <= 2.0, (
        f"太さを合わせられていない(目標 {t_bold:.1f} / 結果 {t_matched:.1f})")
    # 細くする方向には動かさない(収縮は画をちぎる)
    assert glyphops.match_stroke_weight(bold.astype(float), t_thin) is not None
    assert np.array_equal(glyphops.match_stroke_weight(bold.astype(float), t_thin),
                          bold.astype(float))


def test_one_font_can_still_give_a_floor_but_a_narrower_one(fonts):
    """★書体 1 本の環境でも床は測れる —— ただし**狭い**ことを明示すること。

    素の Linux には CJK が 1 本しか入らないことがある(2026-09-17、CI が
    ``fonts-noto-cjk`` だけで PoC が丸ごと skip して落ちた)。そこでは
    ぼけ・線幅・回転・再標本化という**既知の妨害**で同じ字を揺らして床を作る。
    測っているものが違うので ``source`` で区別し、**書体の床より狭い**ことを
    固定する —— 狭い床で「誤検出ゼロ」を主張すると嘘になる。
    """
    nf1 = glyphops.rendering_noise_floor(_CHARS, fonts[0], size=160, out=160)
    assert nf1["source"] == "nuisance" and nf1["n_fonts"] == 1
    assert 0.0 < nf1["median"] < nf1["floor"] <= nf1["max"]
    nf2 = glyphops.typeface_noise_floor(_CHARS, fonts, size=160, out=160)
    assert nf1["floor"] < nf2["floor"], (
        f"妨害の床 {nf1['floor']:.4f} が書体の床 {nf2['floor']:.4f} 以上 —— "
        "妨害が書体差より大きいなら、妨害の選び方を疑う")
    # 別字はどちらの床も超えること(狭い床でも見逃しは増えない)
    d = glyphops.glyph_distance(glyphops.render_glyph("検", fonts[0], 160),
                                glyphops.render_glyph("横", fonts[0], 160), 160)
    assert d > nf1["floor"]


# --------------------------------------------------------------------------- #
# JSON 一枚で受ける入口(correct_spec)                                          #
# --------------------------------------------------------------------------- #
def _sign(fonts, text="電気設備", broken_at=2, wrong="誤"):
    """1 行の掲示を作り、``broken_at`` の字を別の字に差し替える。"""
    from PIL import Image, ImageDraw, ImageFont
    size, pad = 96, 24
    chars = list(text)
    shown = list(chars)
    shown[broken_at] = wrong
    f = ImageFont.truetype(fonts[0], size)
    W = pad * 2 + size * len(chars)
    H = pad * 2 + size
    im = Image.new("RGB", (W, H), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(shown):
        d.text((pad + i * size, pad), c, font=f, fill=(20, 20, 20))
    rgb = np.asarray(im, np.float64) / 255.0
    # ★bbox は**描いた後のインクから**取る。PIL の text() は書体の ascent 分だけ
    #   下げて描くので、指定した座標をそのまま bbox にすると字が縦にはみ出し、
    #   無事な字まで「遠い」と出る(実測 0.058〜0.110、床 0.058)。
    g = rgb.mean(axis=-1)
    ys, xs = np.nonzero(g < 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    spec = {"items": [{"text": text, "bbox": [int(x0), int(y0),
                                              int(x1 - x0), int(y1 - y0)]}]}
    return rgb, spec


def test_the_json_entry_point_finds_and_replaces_only_the_wrong_character(fonts):
    """★入口の本体 —— 壊れた 1 字だけが replaced、残りは ok。

    これが割れたら、入口が「全部直したつもりで無事な字も塗り替えている」か
    「壊れた字を見落としている」のどちらかで、どちらも黙って壊す。
    """
    rgb, spec = _sign(fonts)
    out, rep = glyphops.correct_spec(rgb, spec)
    cells = rep["items"][0]["cells"]
    assert [c["status"] for c in cells] == ["ok", "ok", "replaced", "ok"], \
        [(c["char"], c["status"], c.get("distance_before")) for c in cells]
    fixed = cells[2]
    assert fixed["distance_after"] < fixed["distance_before"], fixed
    assert fixed["distance_after"] <= rep["threshold"], fixed
    assert not np.array_equal(out, rgb), "置換したのに画像が変わっていない"


def test_a_replacement_that_does_not_verify_is_rolled_back(fonts):
    """★検証を通らない修正は**残さない**。

    閾値を 0 にすると、どの置換も「まだ遠い」と判定される。そのとき画像は
    **1 画素も変わってはいけない** —— 通らなかった修正を残すと、
    使う側は「直った」と誤解する。
    """
    rgb, spec = _sign(fonts)
    spec = dict(spec, policy={"threshold": 0.0})
    out, rep = glyphops.correct_spec(rgb, spec)
    kinds = {c["status"] for c in rep["items"][0]["cells"]}
    assert "failed_verification" in kinds, kinds
    assert np.array_equal(out, rgb), "検証を通らなかった置換が画像に残っている"


def test_codepoints_that_disagree_with_the_text_are_refused_at_the_door(fonts):
    """★指示書の食い違いは入口で止める。片方だけ直された指示が回ってくると、
    静かに違う字へ置き換わる —— 例外にして気づかせる。"""
    rgb, spec = _sign(fonts)
    spec["items"][0]["codepoints"] = ["U+96FB", "U+6C34", "U+8A2D", "U+5099"]  # 気 -> 水
    with pytest.raises(ValueError, match="codepoints"):
        glyphops.correct_spec(rgb, spec)


def test_the_report_says_where_the_threshold_came_from(fonts):
    """床の由来(書体の散らばり / 既知の妨害 / 指定)を報告に書く。
    測っているものが違うので、同じ数字として扱ってはいけない。"""
    rgb, spec = _sign(fonts)
    _, rep = glyphops.correct_spec(rgb, spec)
    assert rep["floor_source"] in ("typeface", "rendering"), rep
    _, rep2 = glyphops.correct_spec(rgb, dict(spec, policy={"threshold": 0.05}))
    assert rep2["floor_source"] == "policy" and rep2["threshold"] == 0.05


def test_ink_polarity_is_decided_by_the_border_not_by_majority(fonts):
    """★インクが多数派でも白黒を反転させない。

    行に密着した帯では字が 57 % を占めることがある(実測)。「インクは少数派」と
    決め打つと帯ごと反転し、距離が 0.025 -> 0.121 に跳ねた。**外周は背景**で決める。
    """
    g = np.zeros((40, 100))          # 黒が 60 %、外周は黒(= 背景が黒)
    g[:, :60] = 0.0
    g[:, 60:] = 1.0
    m = glyphops._ink_mask(g)
    assert m[:, 60:].mean() > 0.9 and m[:, :60].mean() < 0.1, \
        "外周(黒)を背景と読めていない"
    assert m.mean() < 0.5


def test_cells_snap_to_the_valleys_between_characters(fonts):
    """等分だけだと切れ目が字に食い込む。谷に吸着していることを固定する。"""
    ink = np.zeros((20, 100), bool)
    for x0 in (2, 40, 72):           # 不等間隔に 3 つ置く
        ink[5:15, x0:x0 + 20] = True
    spans = glyphops.split_cells(ink, 3)
    assert len(spans) == 3
    prof = ink.sum(axis=0)
    for a, b in spans[:-1]:
        assert prof[b - 1] == 0 or prof[min(b, 99)] == 0, \
            f"切れ目 {b} がインクの上にある(prof={prof[max(0, b - 2):b + 2]})"

# --------------------------------------------------------------------------- #
# 実写の版面 —— 板を見つけて起こす(find_plate)                                #
# --------------------------------------------------------------------------- #
# ★ここで検査するのは **閉形式で言い切れること** だけにしてある。
#   端から端まで(受理率・誤検出)の証拠は repo の外の実写 12 枚で取った
#   (**repo の外**に置いた実写一式、正本 = glyph コーパスの curated/140)。
#   合成の場面を 1 枚こしらえて「動いた」と言うのは**やめた** —— 候補の生成は
#   局所標準偏差の分位点で切るので背景が**ざらついている**ことを要求し、四隅の
#   精密化は背景の勾配が**小さい**ことを要求する。実写はその両方を満たすが、
#   素朴な合成(一様乱数の背景)はどちらか片方しか満たせず、合成で緑にすると
#   「合成に合わせた実装」になってしまう。


def _bordered_quad(n=360, shift=22.0):
    """平らな地に、**既知の四隅**の暗い縁を描いた四辺形。返り (画像, 四隅)。"""
    from skimage.draw import polygon, polygon_perimeter
    img = np.full((n, n), 0.90)
    truth = np.array([[70.0, 60.0 + shift], [290.0, 60.0], [290.0 - shift, 300.0],
                      [70.0 + shift * 0.4, 300.0 - shift * 0.4]], np.float64)
    rr, cc = polygon(truth[:, 1], truth[:, 0], img.shape)
    img[rr, cc] = 0.97
    for d in range(5):
        q = truth + (truth.mean(axis=0) - truth) * (d * 0.004)
        rr, cc = polygon_perimeter(q[:, 1], q[:, 0], img.shape, clip=True)
        img[rr, cc] = 0.06
    return img, truth


def test_the_plate_corners_snap_to_the_dark_border():
    """粗い箱をわざと内側に縮めて渡しても、四隅は**縁に乗る**。

    平滑領域の外接箱は、局所標準偏差のしきい値が文字の近くで板を削るので内側に
    寄る。だから四隅は箱ではなく**縁の直線 4 本の交点**で取る。ここでは真の四隅が
    分かっている図形で、縮めた箱から出発して戻ってこられるかを測る(実測 3.9 px)。
    """
    img, truth = _bordered_quad()
    quad = glyphops._refine_quad(img, (slice(95, 285), slice(95, 275)))
    assert quad is not None, "縁がはっきりしている図形で四隅が取れない"
    err = min(float(np.max(np.linalg.norm(np.roll(quad, k, axis=0) - truth, axis=1)))
              for k in range(4))
    assert err < 8.0, "四隅が縁に乗っていない(最大ずれ %.1f px)" % err


def test_a_picture_without_a_plate_is_refused_with_a_reason():
    """板が無ければ ``None`` と理由を返す。**黙って何かを返さない。**"""
    rng = np.random.default_rng(3)
    for name, v in (("一様乱数", np.stack([rng.random((200, 200))] * 3, axis=-1)),
                    ("空フレーム", np.full((160, 160, 3), 0.5))):
        plate, report = glyphops.find_plate(v)
        assert plate is None, "%s から板を取ってしまった" % name
        assert report["status"] in ("no_candidate", "no_quad"), report
        assert report.get("reason"), "断ったのに理由が無い(%s)" % name


def test_find_plate_takes_rgb_only_and_is_deterministic():
    img, _ = _bordered_quad()
    rgb = np.stack([img] * 3, axis=-1)
    with pytest.raises(ValueError):
        glyphops.find_plate(img)                      # 2-D は入口で拒否
    a, ra = glyphops.find_plate(rgb)
    b, rb = glyphops.find_plate(rgb)
    assert ra == rb, "報告が実行ごとに変わる"
    if a is None:
        assert b is None
    else:
        assert np.array_equal(a, b), "同じ入力で起こした絵が変わる"


# --------------------------------------------------------------------------- #
# 行ごと描き直す(policy.mode = "rewrite_line")                                 #
# --------------------------------------------------------------------------- #
def test_rewrite_line_redraws_every_cell_and_touches_nothing_outside_the_bbox(fonts):
    """意図した文字列で行を丸ごと描き直す。bbox の外は 1 画素も変えない。"""
    rgb, spec = _sign(fonts)                            # 「設」を「誤」にした掲示
    bbox = spec["items"][0]["bbox"]
    spec["policy"] = {"mode": "rewrite_line"}
    out, rep = glyphops.correct_spec(rgb, spec)
    assert rep["mode"] == "rewrite_line"
    it = rep["items"][0]
    assert it["status"] == "rewritten", it
    assert [c["status"] for c in it["cells"]] == ["rewritten"] * 4
    # 壊れていた字の distance_before は無事な字より大きい(情報として残る)
    d = [c.get("distance_before", 0.0) for c in it["cells"]]
    assert d[2] > max(d[0], d[1], d[3]), d
    # bbox の外は不変
    x, y, w, h = bbox
    mask = np.ones(rgb.shape[:2], bool)
    mask[y:y + h, x:x + w] = False
    assert np.array_equal(out[mask], rgb[mask]), "bbox の外を変えた"
    # 描き直した行を取り直すと、壊れていた「設」が参照に近づいている
    ink = glyphops._ink_mask(out[y:y + h, x:x + w].mean(axis=-1))
    spans = glyphops.split_cells(ink, 4)
    after = min(glyphops.glyph_distance(ink[:, spans[2][0]:spans[2][1]].astype(float),
                                        glyphops.render_glyph("設", f, 160), 160) for f in fonts)
    assert after < d[2], "描き直しても「設」が参照に近づかない (%.4f -> %.4f)" % (d[2], after)


def test_rewrite_line_default_mode_is_repair_flagged_and_bad_mode_is_refused(fonts):
    rgb, spec = _sign(fonts)
    _, rep = glyphops.correct_spec(rgb, spec)
    assert rep["mode"] == "repair_flagged"
    spec["policy"] = {"mode": "repaint_everything"}
    with pytest.raises(ValueError):
        glyphops.correct_spec(rgb, spec)


def test_rewrite_line_refuses_multimodal_colours_instead_of_smearing(fonts):
    """縁取り(2 色の字)は描かずに断る。黙って汚さない。"""
    from scipy import ndimage
    rgb, spec = _sign(fonts, wrong="設")                # 壊れていない掲示
    x, y, w, h = spec["items"][0]["bbox"]
    crop = rgb[y:y + h, x:x + w]
    ink = glyphops._ink_mask(crop.mean(axis=-1))
    # 字の縁 5 画素を赤く塗って縁取りにする(2 画素では細すぎて単峰と読まれる)
    edge = ndimage.binary_dilation(ink, iterations=5) & ~ink
    crop[edge] = (0.9, 0.1, 0.1)
    spec["policy"] = {"mode": "rewrite_line"}
    out, rep = glyphops.correct_spec(rgb, spec)
    it = rep["items"][0]
    assert it["status"] == "skipped" and "単峰" in it["reason"], it
    assert np.array_equal(out, rgb), "断ったのに画像を変えた"


# --------------------------------------------------------------------------- #
# 誤字か別物か / 理由の語彙                                                      #
# --------------------------------------------------------------------------- #
def test_a_single_wrong_character_is_a_typo_and_an_unrelated_string_is_not(fonts):
    """★「元の字が指示と全く関係ない」を報告で区別する(2026-09-18、ユーザー指摘)。

    1 字だけ違う掲示は ``typo``、意図した文字列と無関係な 4 字が書かれた掲示は
    ``unrelated``。境は :data:`MISMATCH_RATIO`(壊れたマスの距離の中央値 ÷ 床)。
    描き直しはどちらも成功するので、この枝が無いと呼ぶ側は気づけない。
    """
    rgb, spec = _sign(fonts)                          # 電気設「誤」備 → 1 字だけ違う
    _, rep = glyphops.correct_spec(rgb, spec)
    it = rep["items"][0]
    assert it["mismatch"] == "typo", (it["mismatch"], it.get("mismatch_fraction"))
    assert it["mismatch_fraction"] < glyphops.MISMATCH_FRACTION, it["mismatch_fraction"]
    # ★比(中央値 ÷ 床)は環境で動く(Windows 3 書体 1.90 / CI noto-cjk 2.45)ので、
    #   境にしないし、ここでも値を断言しない。載っていることだけ見る。
    assert it["mismatch_ratio"] > 1.0

    # 板には「本日休業」、指示は「電気設備」—— 4 字とも無関係。
    rgb2, spec2 = _sign(fonts, text="本日休業", broken_at=0, wrong="本")
    spec2["items"][0]["text"] = "電気設備"
    spec2["policy"] = {"mode": "rewrite_line"}
    _, rep2 = glyphops.correct_spec(rgb2, spec2)
    it2 = rep2["items"][0]
    assert it2["status"] == "rewritten"               # 描き直し自体は成功する
    assert it2["mismatch"] == "unrelated", (it2["mismatch"], it2.get("mismatch_fraction"),
                                             it2.get("mismatch_distance"))
    assert it2["mismatch_fraction"] >= glyphops.MISMATCH_FRACTION
    assert it2["mismatch_distance"] >= glyphops.MISMATCH_DISTANCE
    # 同じ環境の中では順序が保たれる: 別物の距離 > 誤字の距離。
    assert it2["mismatch_distance"] > it["mismatch_distance"]

    # 全部無事なら none。
    rgb3, spec3 = _sign(fonts, broken_at=0, wrong="電")
    _, rep3 = glyphops.correct_spec(rgb3, spec3)
    assert rep3["items"][0]["mismatch"] == "none"

    # 縁取りで断った行は距離が膨らんでいる(縁がインクに入る)ので unknown。
    # ここを守らないと、無事な 4 字が「別物」に化ける(実測 2.5 倍)。
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(fonts[0], 96)
    im = Image.new("RGB", (24 * 2 + 96 * 4, 24 * 2 + 96), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for i, c in enumerate("電気設備"):
        d.text((24 + i * 96, 24), c, font=f, fill=(20, 20, 20), stroke_width=5, stroke_fill=(200, 30, 30))
    rgb4 = np.asarray(im, np.float64) / 255.0
    ys, xs = np.nonzero(rgb4.mean(axis=-1) < 0.6)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1 - xs.min()), int(ys.max() + 1 - ys.min())]
    _, rep4 = glyphops.correct_spec(rgb4, {"items": [{"text": "電気設備", "bbox": bbox}]})
    it4 = rep4["items"][0]
    assert it4["status"] == "skipped" and it4["mismatch"] == "unknown", it4


def test_every_refusal_carries_a_code_from_the_vocabulary(fonts):
    """``reason`` は人向けの文、``reason_code`` は機械向けの鍵。鍵は :data:`REASON_CODES`
    の中からしか出ない(外部 AI レビューの指摘: 語彙が無いと呼ぶ側が分岐できない)。"""
    rgb, spec = _sign(fonts)
    spec["items"].append({"text": "点検中"})                       # bbox 無し
    spec["items"].append({"text": "点検中", "bbox": [0, 0, 4, 4]})  # 小さすぎ
    _, rep = glyphops.correct_spec(rgb, spec)
    codes = [it.get("reason_code") for it in rep["items"][1:]]
    assert codes == ["missing_text_or_bbox", "bbox_too_small"], codes
    for it in rep["items"]:
        for holder in [it] + it.get("cells", []):
            if holder.get("status") == "skipped":
                assert holder["reason_code"] in glyphops.REASON_CODES, holder
                assert holder["reason"], holder

    # rewrite_line の拒否も同じ語彙。
    _, info = glyphops.rewrite_line(rgb, "", fonts[0])
    assert info == {"ok": False, "code": "empty_text",
                    "reason": glyphops.REASON_CODES["empty_text"]}
    _, info = glyphops.rewrite_line(np.ones_like(rgb), "電気", fonts[0])
    assert info["code"] == "no_ink"
    assert glyphops._code_of("色が単峰でない(前景 0.10 / 背景 0.50 / 縁 0.300) —— x") == "multimodal_colour"
    assert glyphops._code_of("マスが空(インクが 20 画素未満)") == "empty_cell"
    assert glyphops._code_of("何か別の理由") == "cannot_replace"


# --------------------------------------------------------------------------- #
# 指示書の自動生成(bbox を人が測らない)                                          #
# --------------------------------------------------------------------------- #
def _two_line_sign(fonts, lines=("電気設備", "点検中"), broken=(0, 2), wrong="誤"):
    """2 行の掲示。``broken=(行, 字)`` を差し替える。返り ``(rgb, 行ごとのインク bbox)``。"""
    from PIL import Image, ImageDraw, ImageFont
    size, pad, gap = 96, 24, 40
    f = ImageFont.truetype(fonts[0], size)
    W = pad * 2 + size * max(len(s) for s in lines)
    H = pad * 2 + size * len(lines) + gap * (len(lines) - 1)
    im = Image.new("RGB", (W, H), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for r, s in enumerate(lines):
        shown = list(s)
        if broken and broken[0] == r:
            shown[broken[1]] = wrong
        for i, c in enumerate(shown):
            d.text((pad + i * size, pad + r * (size + gap)), c, font=f, fill=(20, 20, 20))
    return np.asarray(im, np.float64) / 255.0


def test_make_spec_finds_the_lines_and_the_spec_drives_the_repair(fonts):
    """★bbox を人が測らずに、行を上から検出して指示書にし、そのまま直す。"""
    rgb = _two_line_sign(fonts)
    spec = glyphops.make_spec(rgb, ["電気設備", "点検中"])
    assert spec["layout"]["status"] == "ok" and spec["layout"]["n_lines"] == 2, spec["layout"]
    b0, b1 = spec["items"][0]["bbox"], spec["items"][1]["bbox"]
    assert b0[1] + b0[3] <= b1[1], "行が上から順でない"
    assert b0[2] > b1[2], "4 字の行の方が 3 字の行より広いはず"
    _, rep = glyphops.correct_spec(rgb, spec)
    st = [[c["status"] for c in it["cells"]] for it in rep["items"]]
    assert st[0][2] == "replaced", st                     # 植えた誤字は直る
    # 無事な字が replaced / failed_verification になるのは既知の誤検出(抽出経路の雑音
    # ≒ 床、約 3 割。床が低い環境 = CI の noto-cjk 0.040 ではさらに出る)で、置き直しは
    # 同じ字、不通過は元に戻すので絵は壊れない。ここで見たいのは「外れた箱で切って
    # skipped(マスが空)が出ない」こと。
    assert all(s in ("ok", "replaced", "failed_verification") for row in st for s in row), st


def test_make_spec_refuses_when_there_are_no_lines_and_correct_spec_then_touches_nothing(fonts):
    """版面が取れなければ items に bbox を入れない。その指示書を渡しても画像は 1 画素も
    変わらない(外れた箱で直すことが構造的に起きない)。"""
    blank = np.full((80, 320, 3), 0.9)
    spec = glyphops.make_spec(blank, ["電気設備"])
    assert spec["layout"]["status"] == "no_lines"
    assert spec["layout"]["reason_code"] in glyphops.REASON_CODES
    assert "bbox" not in spec["items"][0]
    out, rep = glyphops.correct_spec(blank, spec)
    assert np.array_equal(out, blank)
    assert rep["items"][0]["reason_code"] == "missing_text_or_bbox"
    # 行数が合わなければ implausible(2 行の絵に 1 行の指示)。
    rgb = _two_line_sign(fonts)
    spec = glyphops.make_spec(rgb, ["電気設備"])
    assert spec["layout"]["status"] in ("implausible", "ok")   # 1 行に潰せた場合は ok もありうる
    if spec["layout"]["status"] == "ok":
        pytest.skip("2 行が 1 帯に融けて 1 行として通った(この描き方では起きないはず)")
    assert spec["layout"]["reason_code"] == "layout_implausible"
    with pytest.raises(ValueError):
        glyphops.make_spec(rgb, [])


def test_the_poc_line_detector_is_the_shipped_one(fonts):
    """PoC の find_text_lines は出荷の関数を呼ぶ殻 —— 2 つ目の実装を残さない。"""
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "examples", "poc_glyph_typo_detection.py")
    s = importlib.util.spec_from_file_location("poc_glyph", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    rgb = _two_line_sign(fonts)
    g = rgb.mean(axis=-1)
    a, ink_a = m.find_text_lines(g, 2)
    b, ink_b = glyphops.find_text_lines(g, 2)
    assert a == b and np.array_equal(ink_a, ink_b)
