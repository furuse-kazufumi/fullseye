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
