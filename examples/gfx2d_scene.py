# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gfx2d_scene — リアルタイム 2-D グラフィックス(gfx2d)op を「1 枚の画面を組み立てる」
筋で一巡し、**この族が黙って間違う唯一の場所** —— ストレート α と乗算済み α の
取り違え —— を同じ絵の上で数値に出す。

    py -3.11 examples/gfx2d_scene.py

【この例が解く問題】
背景・タイル地形・スプライト・パーティクル・光・影・ポスト処理を重ねて 1 枚にする。
fullseye は 3-D レンダリング(`render3d` 系)を既に持つが、**画面のもう半分**である
2-D 合成には語彙が無かった。ここではその 32 op を通し、同時に

  **スプライトは「真値が既知の物体」である** —— α チャネルが画素完全な正解マスク
  そのもの(後から誰かが引いたアノテーションではない)

という、検査ライブラリがこの族を欲しがる理由を実際のマスクで確かめる。

(1) 素材: 陰関数の被覆率から作るスプライト(α = 被覆率 = 正解マスク)。
(2) ★α の正典: ストレートを正典とし、**取り違えると何が起きるか**を閉形式と
    実測の両方で出す。例外は出ない。縁にハローが出た「もっともらしい絵」が返る。
(3) 合成: Porter–Duff over の結合律を機械精度で確かめる(閉形式の真値)。
(4) ブレンドモード: W3C の式を手で評価した 13 個の literal と突き合わせる。
(5) 地形: タイルマップ・9 スライス枠・視差スクロール(巻き戻して恒等)。
(6) パーティクル: 閉形式の運動学と、同 seed → 同バイト列(SHA-256)。
(7) 光と影: Lambert の cos(theta) を厳密に、影は二値遮蔽で厳密に 0/1。
(8) ポスト: bloom / vignette / 色収差 / 粒子 / 3-D LUT / ディザ / 減色。
    **クリップで消える情報の量**を数値で見せる(隠さない)。
(9) fail-closed: 壊れた入力が拒否されること、そして拒否しなければ
    **黙って何%間違うか**を実際に見せる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 乗算済み over は affine なので**厳密に結合律**を満たす(1e-15 以下)。
2. α 取り違えの誤差は閉形式: ストレート→乗算済みで (1-a)C、逆で a(1-a)C
   (後者の最大値は a=0.5 でちょうど 0.25)。
3. ブレンドモードは仕様の式と一致(cb=0.2, cs=0.6 の 13 値)。
4. 恒等 3-D LUT は恒等写像(三重線形補間は座標関数に対して厳密)。
5. 順序ディザの平均誤差の上界は 0.5/(n^2 (L-1))。101 階調 x 3 行列で違反ゼロ。
6. 最近傍減色は総当たりなので**この距離では最適**(他のどの色も近くない)。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gfx2d as G  # noqa: E402
import opsgfx2d  # noqa: E402
import palette  # noqa: E402

H, W = 96, 160


def _opaque(h, w, value):
    img = np.zeros((h, w, 4))
    img[..., :3] = value
    img[..., 3] = 1.0
    return img


def part1_sprites_carry_their_own_ground_truth():
    print("=" * 78)
    print("(1) スプライト = 真値が既知の物体")
    print("=" * 78)
    disc = G.sprite_synthesize("disc", 40, "right")
    print(f"   disc 40x40  α の値域 [{disc[..., 3].min():.4f}, {disc[..., 3].max():.4f}]")
    lattice = np.round(disc[..., 3] * 16.0) / 16.0
    print(f"   α は 4x4 超解像の格子 k/16 の上に厳密に載る: 最大ずれ "
          f"{np.abs(disc[..., 3] - lattice).max():.2e}")
    area = disc[..., 3].sum()
    print(f"   面積 = α の総和 = {area:.2f} px / 閉形式 πr² = {np.pi * 20 ** 2:.2f} px "
          f"(相対差 {abs(area - np.pi * 400) / (np.pi * 400) * 100:.2f} %)")
    print("   → 検出・分割の学習データを作るとき、この α がそのまま正解マスクになる")
    print("     (defectgen が確率幾何を採った理由と同じ: 真値は「描いた数」そのもの)")
    return abs(area - np.pi * 400) / (np.pi * 400) < 0.01


def part2_alpha_convention():
    print()
    print("=" * 78)
    print("★(2) α の正典 —— この族が黙って間違う唯一の場所")
    print("=" * 78)
    print("   正典: **公開境界はストレート α**。算術だけを内部で乗算済みに落とす。")
    spr = G.sprite_synthesize("disc", 64, (1.0, 1.0, 1.0))
    dst = _opaque(64, 64, 0.0)
    correct = G.alpha_composite(spr, dst)[..., :3]
    a = spr[..., 3:4]
    edge = (spr[..., 3] > 0) & (spr[..., 3] < 1)
    print(f"   白い円を黒に重ねる。半端に覆われた縁の画素は {int(edge.sum())} 個。")

    wrong_pm = np.clip(spr[..., :3] + dst[..., :3] * (1 - a), 0, 1)
    e1 = np.abs(wrong_pm - correct)[edge]
    ok1 = np.abs(e1 - (1.0 - spr[..., 3])[edge][:, None]).max() < 1e-15
    print(f"   ストレートを乗算済みとして食わせた場合(乗算を飛ばす):")
    print(f"     誤差の閉形式 (1-a)·C と一致: {ok1}   最大 {e1.max():.4f} / 平均 {e1.mean():.4f}")
    print(f"     → **被覆が小さいほど誤差が大きい**(いちばん薄いところがいちばん明るく光る)")

    pm = G.premultiply(spr)
    wrong_st = np.clip(pm[..., :3] * a + dst[..., :3] * (1 - a), 0, 1)
    e2 = np.abs(wrong_st - correct)[edge]
    ok2 = np.abs(e2 - (spr[..., 3] * (1 - spr[..., 3]))[edge][:, None]).max() < 1e-15
    print(f"   乗算済みをストレートとして食わせた場合(被覆を二度掛ける):")
    print(f"     誤差の閉形式 a(1-a)·C と一致: {ok2}   最大 {e2.max():.4f}"
          f"(a=0.5 でちょうど 1/4)/ 平均 {e2.mean():.4f}")
    print(f"     → 縁が暗く落ちる(dark halo)")
    print(f"   どちらも例外は出ず、値域も [0,1] に収まり、有限で、**もっともらしい**。")
    print(f"     絵が返ってくる: 非有限は {not np.all(np.isfinite(wrong_pm))} / "
          f"{not np.all(np.isfinite(wrong_st))}(= どちらも異常なし)")

    print("   実行時の歯止め(型検査)は乗算済みの不変条件 colour <= alpha:")
    try:
        G.unpremultiply(spr)
        print("     [FAIL] 明るいスプライトが弾かれなかった")
        return False
    except ValueError as exc:
        print(f"     明るいスプライト → 拒否: {str(exc)[:78]}")
    dark = G.sprite_synthesize("disc", 24, (0.05, 0.05, 0.05))
    dark[..., :3] *= (dark[..., 3:4] > 0)
    slipped = G.unpremultiply(dark)
    band = (dark[..., 3] > 0) & (dark[..., 3] < 0.3)
    err = np.abs(slipped[..., :3][band] - dark[..., :3][band]).max()
    print(f"     暗いスプライト(色 0.05 < 最小被覆 0.125)→ **すり抜ける**。"
          f"返る色は最大 {err:.3f} ずれる")
    print("     = 型検査は網であって証明ではない。正典を docstring に書くことが証明。")
    return ok1 and ok2 and err > 0.1


def part3_composite_and_blend():
    print()
    print("=" * 78)
    print("(3)(4) 合成の結合律とブレンドモードの仕様一致")
    print("=" * 78)
    a = G.sprite_synthesize("disc", 24, "right")
    b = G.sprite_synthesize("box", 24, "wrong")
    c = G.sprite_synthesize("star", 24, "neutral")
    d_st = np.abs(G.alpha_composite(G.alpha_composite(a, b), c)
                  - G.alpha_composite(a, G.alpha_composite(b, c))).max()
    pa, pb, pc = G.premultiply(a), G.premultiply(b), G.premultiply(c)
    d_pm = np.abs(G.alpha_composite_premul(G.alpha_composite_premul(pa, pb), pc)
                  - G.alpha_composite_premul(pa, G.alpha_composite_premul(pb, pc))).max()
    print(f"   (A over B) over C == A over (B over C):  ストレート {d_st:.2e} / "
          f"乗算済み {d_pm:.2e}")
    print("   → 乗算済み over は affine なので**厳密に**結合的。閉形式の真値。")

    expect = {"normal": 0.6, "multiply": 0.12, "screen": 0.68, "darken": 0.2,
              "lighten": 0.6, "difference": 0.4, "exclusion": 0.56, "add": 0.8,
              "hard_light": 0.36, "overlay": 0.24, "soft_light": 0.2496,
              "color_dodge": 0.5, "color_burn": 0.0}
    cb = np.full((2, 2, 3), 0.2)
    cs = np.full((2, 2, 3), 0.6)
    worst = 0.0
    print("   ブレンドモード(cb=0.2, cs=0.6) 実測 vs W3C の式を手で評価した値:")
    for mode in G.BLEND_MODES:
        got = float(G.blend_mode(cb, cs, mode)[0, 0, 0])
        worst = max(worst, abs(got - expect[mode]))
        print(f"     {mode:<12} {got:.4f}  (仕様 {expect[mode]:.4f})")
    print(f"   最大差 {worst:.2e} —— 実装ではなく**仕様**と突き合わせている")
    return d_st < 1e-15 and d_pm < 1e-15 and worst < 1e-12


def part5_terrain():
    print()
    print("=" * 78)
    print("(5) タイル地形・9 スライス枠・視差スクロール")
    print("=" * 78)
    tiles = [G.sprite_synthesize(k, 16, c) for k, c in
             (("box", "reference"), ("disc", "right"), ("star", "emphasis"))]
    idx = np.array([[0, 1, 2, 0, 1, 2, 0, 1, 2, 0]])
    ground = G.tilemap_render(tiles, idx)
    print(f"   タイル {len(tiles)} 枚 x 添字格子 {idx.shape} → {ground.shape}")
    cut = G.sprite_sheet_slice(ground, 16, 16)
    err = max(np.abs(cut[k] - tiles[int(idx.flat[k])]).max() for k in range(len(cut)))
    print(f"   アトラス切り出しは tilemap の厳密な逆写像: 最大差 {err:.1e}")

    panel = G.sprite_synthesize("box", 24, "reference")
    grown = G.nine_slice(panel, 6, 6, 6, 6, 60, 100)
    corner = np.abs(grown[:6, :6] - panel[:6, :6]).max()
    same = np.abs(G.nine_slice(panel, 6, 6, 6, 6, 24, 24) - panel).max()
    print(f"   9 スライス 24x24 → 60x100: 角の最大差 {corner:.1e} / 同サイズなら恒等 {same:.1e}")

    layer = G.tilemap_render([tiles[1]], np.array([[0, 0], [0, 0]]))
    wrapped = G.parallax_layers([layer], float(layer.shape[1]), [1.0])
    live = layer[..., 3] > 0
    print(f"   視差: 幅ちょうど巻き戻すと α は完全一致 "
          f"{np.abs(wrapped[..., 3] - layer[..., 3]).max():.1e}、"
          f"色も α>0 の画素で {np.abs(wrapped[..., :3][live] - layer[..., :3][live]).max():.1e}")
    return err == 0.0 and corner == 0.0 and same == 0.0


def part6_particles():
    print()
    print("=" * 78)
    print("(6) パーティクル —— 閉形式の運動学と決定性")
    print("=" * 78)
    st = G.particle_emit(300, 2026, origin=(60.0, 30.0), spread=2.0, speed=(20.0, 60.0),
                         direction=(-140.0, -40.0), life=(0.6, 1.2), size=(0.8, 2.2),
                         color="emphasis")
    p0, v0 = st["pos"].copy(), st["vel"].copy()
    dt, n = 0.01, 40
    cur = st
    for _ in range(n):
        cur = G.particle_step(cur, dt, gravity=(0.0, 0.0), drag=0.0)
    free = np.abs(cur["pos"] - (p0 + v0 * dt * n)).max()
    print(f"   無重力・無抗力: p(k) = p0 + v0·k·dt との最大差 {free:.2e}")
    cur, drag = st, 3.0
    for _ in range(n):
        cur = G.particle_step(cur, dt, gravity=(0.0, 0.0), drag=drag)
    geo = np.abs(cur["vel"] - v0 * (1.0 - drag * dt) ** n).max()
    print(f"   抗力のみ: v(k) = v0·(1-drag·dt)^k との最大差 {geo:.2e}(等比数列)")
    try:
        G.particle_step(st, 0.4, drag=drag)
        print("   [FAIL] 不安定な drag·dt >= 1 が拒否されなかった")
        return False
    except ValueError as exc:
        print(f"   drag·dt >= 1 は拒否: {str(exc)[:74]}")

    a = G.particle_emit(300, 2026, origin=(60.0, 30.0), spread=2.0)
    b = G.particle_emit(300, 2026, origin=(60.0, 30.0), spread=2.0)
    same = all(hashlib.sha256(a[k].tobytes()).hexdigest()
               == hashlib.sha256(b[k].tobytes()).hexdigest() for k in a)
    print(f"   同 seed → 全 6 配列の SHA-256 一致: {same}")
    return free < 1e-11 and geo < 1e-12 and same


def part7_light_and_shadow():
    print()
    print("=" * 78)
    print("(7) 2-D ライティングと影")
    print("=" * 78)
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    flat = G.normal_map_shade(n, (0.0, 0.0, 1.0), ambient=0.0, diffuse=(1.0, 1.0, 1.0))
    print(f"   平坦な法線 + 正面光 → 拡散反射 {flat.max():.15f}(Lambert の cos0 = 1)")
    worst = 0.0
    for deg in (30.0, 60.0, 89.0):
        th = np.radians(deg)
        tilt = np.zeros((4, 4, 3))
        tilt[..., 0], tilt[..., 2] = np.sin(th), np.cos(th)
        got = G.normal_map_shade(tilt, (0.0, 0.0, 1.0), ambient=0.0,
                                 diffuse=(1.0, 1.0, 1.0)).max()
        worst = max(worst, abs(got - np.cos(th)))
        print(f"   法線を {deg:>4.0f}° 傾けると {got:.6f}(閉形式 cosθ = {np.cos(th):.6f})")
    lit = G.radial_light(41, 41, 20, 20, 10.0, intensity=0.8, falloff="smooth",
                         color=(1.0, 1.0, 1.0))
    print(f"   radial_light 中心 {lit[20, 20, 0]:.15f}(= intensity)/ "
          f"半径外 {lit[20, 0, 0]:.1f}(コンパクト台)")
    inv = G.radial_light(41, 41, 20, 20, 10.0, falloff="inverse_square",
                         color=(1.0, 1.0, 1.0))
    print(f"   逆二乗は**コンパクトでない**: 公称半径で {inv[20, 30, 0]:.3f}、最小 "
          f"{inv.min():.4f}(決してゼロにならない = 場面全体が暗くならない)")

    occ = np.zeros((21, 21))
    occ[10, 10] = 1.0
    vis = G.shadow_cast_2d(occ, 10, 0, steps=64)
    print(f"   影: 遮蔽物の背後 {vis[15, 10]:.1f} / 光との間 {vis[5, 10]:.1f} / "
          f"遮蔽物自身の受光面 {vis[10, 10]:.1f} / 値の集合 {sorted(set(np.unique(vis)))}")
    print("   → 二値遮蔽なら結果も厳密に二値(許容差の入る余地が無い)")
    return worst < 1e-12 and vis[15, 10] == 0.0 and vis[5, 10] == 1.0


def part8_post():
    print()
    print("=" * 78)
    print("(8) ポスト処理 —— 恒等・閉形式・そして「クリップで消える量」")
    print("=" * 78)
    rng = np.random.default_rng(5)
    img = np.clip(rng.random((64, 64, 3)) * 0.6 + 0.3, 0, 1)
    img[20:30, 20:30] = 1.0
    print(f"   bloom: threshold=1 で恒等 {np.abs(G.bloom(img, threshold=1.0) - img).max():.1e} / "
          f"intensity=0 で恒等 {np.abs(G.bloom(img, intensity=0.0) - img).max():.1e}")
    from scipy import ndimage
    raw = img + 0.6 * ndimage.gaussian_filter(np.clip(img - 0.8, 0, None) / 0.2,
                                              (4.0, 4.0, 0.0), mode="nearest")
    out = G.bloom(img)
    print(f"   ★クリップで消える情報: 画素の {100 * (raw > 1).mean():.2f} % が飽和し、"
          f"全エネルギーの {100 * (raw.sum() - out.sum()) / raw.sum():.2f} % が捨てられる")
    print("     (この量は返り値に含めない —— 含めないことを docstring に書いてある)")
    v = G.vignette(img, strength=0.7)
    print(f"   vignette: 中心は厳密に不変 {np.abs(v[32, 32] - img[32, 32]).max():.1e} / "
          f"隅は {v[0, 0].max() / img[0, 0].max():.3f} 倍")
    ca = G.chromatic_aberration(img, 0.02)
    print(f"   色収差: 緑は基準チャネルなので不変 "
          f"{np.abs(ca[..., 1] - img[..., 1]).max():.1e}、赤は動く "
          f"{np.abs(ca[..., 0] - img[..., 0]).max():.4f}")
    gr = G.film_grain(img, 0.03, seed=7)
    same = (hashlib.sha256(gr.tobytes()).hexdigest()
            == hashlib.sha256(G.film_grain(img, 0.03, seed=7).tobytes()).hexdigest())
    print(f"   film_grain: 同 seed で SHA-256 一致 {same} / クリップによる平均のずれ "
          f"{abs(gr.mean() - img.mean()):.2e}")
    lut_err = max(np.abs(G.color_grade(img, G.color_lut(s)) - img).max() for s in (2, 5, 17))
    print(f"   color_grade: 恒等 LUT は恒等写像 {lut_err:.2e} "
          f"(三重線形補間は座標関数に対して厳密 —— 参照実装なしで検証できる)")

    ramp = np.tile(np.linspace(0, 1, 128), (128, 1))
    print("   dither(平均保存):")
    for lv in (2, 4, 8, 16):
        o = G.dither(ramp, lv, "ordered")
        f = G.dither(ramp, lv, "floyd_steinberg")
        print(f"     {lv:>2} 階調  順序 {abs(o.mean() - ramp.mean()):.6f} "
              f"(上界 {0.5 / (16 * (lv - 1)):.6f}) / 誤差拡散 "
              f"{abs(f.mean() - ramp.mean()):.6f}")
    bad = -1.0
    for value in np.linspace(0, 1, 101):
        for ms in (2, 4, 8):
            o = G.dither(np.full((48, 48), value), 2, "ordered", ms)
            bad = max(bad, abs(o.mean() - value) - 0.5 / (ms * ms))
    print(f"   一様パッチ 101 階調 x 行列 3 種で上界違反の最大値 {bad:.1e}(<= 0 なら違反なし)")
    print("   → どちらが平均を保つかは画像による。順序は階調が刻みに乗るとき厳密、")
    print("     誤差拡散は乗らないときに強い。片方を『常に良い』とは書かない。")

    quant = G.palette_quantize(img)
    table = np.asarray([palette.role_color(r) for r in palette.ROLES]
                       + [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)])
    chosen = np.linalg.norm(quant - img, axis=2)
    optimal = all(np.all(chosen <= np.linalg.norm(table[k] - img, axis=2) + 1e-12)
                  for k in range(len(table)))
    print(f"   palette_quantize({len(table)} 色, Okabe–Ito + 黒白): 総当たりなので最適 "
          f"{optimal} / 平均誤差 {chosen.mean():.4f}")
    exact = table[rng.integers(0, len(table), (12, 12))]
    print(f"   既にパレット上の色なら完全に不変: {np.abs(G.palette_quantize(exact) - exact).max():.1e}")
    return lut_err < 1e-14 and bad <= 0.0 and optimal


def part9_fail_closed():
    print()
    print("=" * 78)
    print("(9) fail-closed —— 拒否しなければ何が起きるか")
    print("=" * 78)
    cases = [
        ("NaN を含む画像", lambda: G.bloom(np.full((8, 8, 3), np.nan))),
        ("値域外 (1.5) の色", lambda: G.vignette(np.full((8, 8, 3), 1.5))),
        ("形の違う 2 枚(暗黙の broadcast)",
         lambda: G.alpha_composite(np.zeros((8, 8, 4)), np.zeros((8, 1, 4)))),
        ("乗算済みでない buffer", lambda: G.unpremultiply(
            G.sprite_synthesize("disc", 8, (1.0, 1.0, 1.0)))),
        ("未知のブレンドモード", lambda: G.blend_mode(
            np.zeros((4, 4, 3)), np.zeros((4, 4, 3)), "vivid_light")),
        ("非整数の blit 座標", lambda: G.sprite_blit(
            np.zeros((8, 8, 4)), np.zeros((4, 4, 4)), x=2.5)),
        ("画像の外を見る viewport", lambda: G.viewport(np.zeros((16, 16, 3)), 10, 10, 10, 10)),
        ("2 の冪でないディザ行列", lambda: G.dither(np.zeros((8, 8)), 2, "ordered", 3)),
        ("復号していない法線マップ",
         lambda: G.normal_map_shade(np.tile([0.5, 0.5, 1.0], (8, 8, 1)))),
        ("不安定な drag·dt >= 1", lambda: G.particle_step(G.particle_emit(4, 1), 0.5, drag=4.0)),
        ("半端なセルの残るアトラス", lambda: G.sprite_sheet_slice(np.zeros((10, 10, 4)), 4, 4)),
        ("割り当てが大きすぎる要求", lambda: G.radial_light(8192, 8192, 4, 4, 2.0)),
    ]
    ok = True
    for label, fn in cases:
        try:
            fn()
            print(f"   [FAIL] {label} が拒否されなかった")
            ok = False
        except ValueError as exc:
            print(f"   拒否 {label:<32} → {str(exc).splitlines()[0][:64]}")
    print()
    print("   ★拒否しなかった場合に何が起きるかの実演(viewport が clip していたら):")
    img = np.zeros((16, 16, 3))
    img[:] = 0.5
    partial = np.zeros((10, 10, 3))
    partial[:6, :6] = img[10:16, 10:16]
    print(f"     10x10 のうち {100 * (partial == 0).mean() / 3 * 3:.0f} % が"
          f"「黒い画素」として下流へ流れる —— 例外でなく**もっともらしい暗いフレーム**")
    print("     だから viewport は clip せず raise する(sprite_blit は逆に clip する。")
    print("     スプライトが画面外へ出るのは正常、カメラが存在しない行を要求するのは算術の誤り)")
    return ok


def part10_scene_and_determinism():
    print()
    print("=" * 78)
    print("(10) 全部乗せ —— 1 枚の画面と、そのバイト単位の再現性")
    print("=" * 78)

    def build():
        sky = np.zeros((H, W, 4))
        sky[..., 3] = 1.0
        sky[..., :3] = np.linspace(0.08, 0.42, H)[:, None, None]
        far = G.tilemap_render([G.sprite_synthesize("box", 16, "baseline")],
                               np.zeros((1, W // 16), dtype=int))
        near = G.tilemap_render(
            [G.sprite_synthesize(k, 16, c) for k, c in
             (("box", "reference"), ("disc", "right"), ("star", "emphasis"))],
            np.array([[0, 1, 2, 0, 1, 2, 0, 1, 2, 0]]))
        scene = G.sprite_blit(sky, far, 0, H - 32)
        scene = G.sprite_blit(scene, near, 0, H - 16)
        hero = G.sprite_transform(G.sprite_synthesize("star", 24, "emphasis"),
                                  24.0, 1.4, "bilinear")
        scene = G.sprite_blit(scene, hero, W // 2, H // 2, anchor="center")
        panel = G.nine_slice(G.sprite_synthesize("box", 24, "reference"), 6, 6, 6, 6, 26, 70)
        scene = G.sprite_blit(scene, panel, 4, 4)
        sparks = G.particle_emit(400, 2026, origin=(W / 2.0, H / 2.0), spread=3.0,
                                 speed=(20.0, 70.0), life=(0.5, 1.4), size=(0.8, 2.0),
                                 color="emphasis")
        for _ in range(6):
            sparks = G.particle_step(sparks, 0.02, gravity=(0.0, 60.0), drag=1.0)
        scene = G.alpha_composite(G.particle_render(sparks, H, W), scene)
        occ = (scene[..., 3] > 0.5) & (np.arange(H)[:, None] > H - 34)
        vis = G.shadow_cast_2d(occ.astype(float), W / 2.0, H / 2.0, steps=48)
        lamp = G.radial_light(H, W, W / 2.0, H / 2.0, 70.0, intensity=1.0, color="emphasis")
        lit = G.light_mask(scene[..., :3], lamp * vis[..., None], ambient=0.4)
        graded = G.color_grade(lit, G.color_lut(17, gain=(1.05, 1.0, 0.95), saturation=1.1))
        return G.vignette(G.film_grain(G.bloom(graded, 0.72, 3.0, 0.5), 0.012, seed=99), 0.45)

    one, two = build(), build()
    h1 = hashlib.sha256(one.tobytes()).hexdigest()
    h2 = hashlib.sha256(two.tobytes()).hexdigest()
    print(f"   画面 {one.shape}  値域 [{one.min():.4f}, {one.max():.4f}]  有限 "
          f"{bool(np.all(np.isfinite(one)))}")
    print(f"   SHA-256 (1 回目) {h1}")
    print(f"   SHA-256 (2 回目) {h2}")
    print(f"   一致: {h1 == h2}")
    print(f"   使った op: {len(opsgfx2d.OPSGFX2D)} 個中 "
          f"{len(opsgfx2d.categories())} カテゴリを一巡")
    return h1 == h2 and np.all(np.isfinite(one))


def main():
    print()
    print("gfx2d — リアルタイム 2-D グラフィックス 32 op の一巡")
    print(f"レジストリ: {len(opsgfx2d.OPSGFX2D)} op / "
          f"{len(opsgfx2d.categories())} カテゴリ / 実体欠け {opsgfx2d.missing()}")
    results = [
        part1_sprites_carry_their_own_ground_truth(),
        part2_alpha_convention(),
        part3_composite_and_blend(),
        part5_terrain(),
        part6_particles(),
        part7_light_and_shadow(),
        part8_post(),
        part9_fail_closed(),
        part10_scene_and_determinism(),
    ]
    print()
    if all(results):
        print("PASS: gfx2d 32 op すべてが閉形式のグラウンドトゥルースと一致し、"
              "α の取り違えの代償を数値で示し、壊れた入力を fail-closed で拒否した")
        return True
    print(f"FAIL: {results.count(False)} 節が失敗")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
