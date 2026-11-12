# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""円マークの校正板を最初から最後まで通す —— create_caltab → 描画 → find_caltab → camera_calibration_lm を真値と突き合わせる。

Circle-mark calibration plate, end to end: ``create_caltab`` → a rendered (synthetic) camera (known K, distortion,
poses) → ``find_caltab`` → ``camera_calibration_lm``, checked against the truth that went into the renderer.

    py -3.11 examples/poc_caltab_chain_truth.py

``CI`` では分岐しない(縮小モードは無い。常に同じ全量を走らせる、約 1.7 分)。``FULLSEYE_FIGURES=off`` で図の書き出しだけ止められる。

【この PoC が答える問題】
円マーク板(``create_caltab`` / ``find_caltab``)と、K・歪み・全姿勢を同時に詰める ``camera_calibration_lm`` は、
別々の時期に別々の試験で作られた。チェッカー板の鎖は ``poc_calibration_truth_map`` が通したが、**円マークの鎖は
1 度も端から端まで通っていない**。Fullseye の ``find_caltab`` の円マークの検出は「2 値化した連結成分の重心」で、
灰色の情報を捨てる。それで校正がどこまで当たるか、雑音を増やすと誤差がどう増えるかを、真値を仕込んだ描画で数える。
(所見は Fullseye のこの実装についてで、HALCON の同名の演算子の限界を言うものではない。)

【撮像と推定で独立な所・共通な所】
* 撮像は**合成**で、画素から板へ逆に引く描画: 画素(3x3 の標本)ごとに ``fs.undistort_points``(固定点反復で歪みを外す)
  → 視線を板の平面に当てる → 板の座標が円の内か外かで塗る → 光学のぼけ(σ 0.7 px)→ 正規雑音 σ_I。
* **共通**: レンズは推定と同じ Brown–Conrady の 4 係数(k1 k2 p1 p2)の族(実装は別: 描画は歪みを外す向き、推定は歪ませる向き)。
  式を全く共有しないわけではない。**独立**なのは、円の像の形と、面積の標本化(画素に何が入るか)。
* 推定は**検出点からの最適化**: ``find_caltab`` は画像しか見ず(平滑化 σ 1.2 px → 2 値化 → 連結成分の重心)、
  ``camera_calibration_lm`` はその点だけから前向きの投影モデルで K・歪み・姿勢を解く。
* 真の点(門で比べる側)は板の円の中心を前向きに投影した値(``fs.project_points`` + ``fs.distort_points``)。
  円の像の重心と中心の像の差(偏心)は ~f r² tanθ / Z² で、この PoC の配置では**最大 0.02 px**(円周を投影した多角形の
  重心で本文の中で数える。2 値の重心の床 ~0.09 px の 0.2 倍)。

【門(数値)】
1. 検出: 8 視点で 63 個すべてが拾え、対応がつく。雑音 0 の検出のずれは**2 値の重心の量子化**の理論値
   1/sqrt(6πρ)(ρ = 像の円の半径 [px]。境界の画素 ~2πρ 個が面積 U(−1/2, 1/2) の誤差を持つとした 2-D rms)の
   **0.8〜1.25 倍**。実測 0.0939 px / 理論 0.0934 px(ρ = 6.08 px)= 1.01。板を横に ±0.6 mm ずらした 18 配置でも
   0.95〜1.02。偏心は最大 0.02 px(門 0.03 px)。
   *限界*: 一様なずれと一様な拡大は cx / fx に吸収されて校正の誤差にならない(門 2 は原理的に見えない)。
   見えるのは門 1 の帯だけで、全点を各座標に 0.1 px(ずれの長さ 0.14 px)ずらすと比 1.88 で落ち、0.05 px(長さ 0.07 px)でも落ちる(変異で確認)が、**長さ約 0.07 px 未満の一様なずれは通る**。
2. 校正(σ_I = 0.05、**種 40 本の全部で**): fx・fy・cx・cy・k1・k2・p1・p2 の誤差が、それぞれ LM の共分散の 1σ の
   **4 倍以内**、かつ共分散で白色化した距離 d² = eᵀC⁻¹e が χ²(8) の 99.9 % 点 26.12 未満。実測: 最大 3.44σ(fy)、
   2σ を超えた種が 22/40、d² の中央値 8.1・最大 18.2。(種 1 だけなら最大 1.96σ・d² = 11.2 だが、これは種 1 の性質。
   「全部 2σ 以内」とは言えない。)1σ は観測の残差から推定した点の雑音で決まる(真値を見ない)ので、許容差の根拠は雑音量そのもの。
3. 姿勢(種 40 本の全部で): 回転と並進の誤差が、内部パラメータの 1σ から伝わる量の 4 倍以内(奥行きは fx と相殺するので
   ΔZ ≈ Z·σ_fx/fx、横は主点のずれで Z·σ_c/fx、回転は σ_c/fx [rad])。実測: 回転 最大 0.56、横 0.42、奥行き 0.83(許容に対する比)。
4. 雑音に比例するか(**真値は使わない自己整合**。真値と突き合わせるのは門 1〜3): σ_I を 0.02・0.05・0.1・0.2 に振り、
   種 40 本ずつ。雑音 0 の結果からのずれだけを見る(量子化の床は種によらず同じなので引き算で消える)。fx のずれ Δfx(種の rms)が
   検出点のずれ Δpt に比例し(log-log の傾き 0.7〜1.5。種の始まりを 4 通り変えて 1.04〜1.29)、比例の係数が共分散の利得
   G = σ_fx/σ_px(真値を見ない、25.65)の予測 G·Δpt と 0.5〜2 倍で合う(実測 0.82〜1.14、種の始まりを変えて 0.68〜1.30)。
   当てずっぽうの一致なら、雑音に比例しないし利得とも合わない。
5. 床の配置依存: 板を横に ±0.6 mm ずらした 18 配置と基準の 1 配置(雑音 0)で fx の誤差の rms が、床の予測
   G·(1/sqrt(6πρ))/√2 = 1.69 px の 0.5〜2 倍(実測 0.96 倍)。符号は配置で入れ替わる(正 8・負 11 配置、門)。
6. 比較(find_caltab の限界の数え直し): 灰色の重心(窓の中心に真の点を使う上限)は検出のずれ 0.022 px(2 値の床の 0.24 倍、門 0.5 倍未満)、
   平滑化なしの連結成分は σ_I = 0.2 で 6274 個(門 630 個超)。

【★ この PoC が出した所見】
(a) ``find_caltab`` は**2 値の重心**なので、検出点のずれは画像の雑音に比例しない: Δpt ∝ σ_I^0.57(門 0.4〜0.7)。
    しきい値をまたいで反転する境界の画素の数が σ_I に比例し、ずれはその数の平方根で増えるから(理論 0.5)。
    だから画像の雑音を半分にしても、**雑音が足す分の**校正の誤差は 1/√2 にしか減らない(床の分は雑音に依らず残る)。
    一方、校正の誤差は**検出点のずれ**には比例する(門 4、傾き 1.04〜1.29)。
(b) **2 値の重心の量子化が fx に rms 約 0.2 % の床を作る**(雑音 0、19 配置で −0.45〜+0.33 %、rms 0.198 %、予測 0.21 %)。
    -0.45 % は**この 8 視点の配置で**出た値で、板をずらすと符号も入れ替わる。検出点のずれ自体は像の円が小さいほど大きい
    (1/sqrt(6πρ))。マークを像で倍の半径にすれば床は 1/√2。灰色を重みにした重心なら 0.022 px(上の門 6、窓の中心に真の点を使った上限)。
    ``find_caltab`` には灰色の重心の経路が無い。
(c) ``find_caltab`` には面積の下限が無い。平滑化なしで σ_I = 0.2 を渡すと連結成分が 6274 個になり
    (平滑化 σ 1.2 px を挟むと 63 個)、``find_marks_and_pose`` の対応づけが壊れる。この PoC は平滑化を挟む。
(d) ``sim_caltab`` は**投影した中心に画素で決めた半径の円盤を塗る**(歪みなし、正方形の画像)ので、
    推定と同じ投影の式を共有し、円の像の形も面積の標本化も持たない。独立な撮像にはならないので、
    ここでは逆に引く描画を自前で書いた(それでもレンズの族は共通、上の「共通」)。
(e) k2 は板 1 枚の視野ではほとんど決まらない: 1σ 0.051 が真値 0.06 と同じ大きさで、**この配置・種 1 では**推定が符号まで逆(−0.030)。
    種 40 本では 26 本で k2 の推定が負(符号が逆)だった。それでも 4σ の内で、共分散は「決まらない」ことを正しく言っている。
    k2 を信じたいなら広角の視点を増やす。p2 の符号なども配置・種で入れ替わる。
(f) ``find_marks_and_pose`` は K を要求するが、対応づけ(ホモグラフィ誘導)だけなら K は効かない。
    ここでは未校正の公称 K(焦点 = 画像の幅、主点 = 画像の中心)を渡し、返る姿勢は使わない。

    EXTEND: 実画像に差し替えるには ``render_view`` の返りを撮った画像(明るいマーク・暗い板、[0, 1])に
    置き換え、``BOARD`` の間隔を実測値にする。真値が無いので門 2・3 の「誤差」は出せず、``param_std`` を見る。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

K_TRUE = np.array([[820.0, 0.0, 323.4], [0.0, 812.0, 238.7], [0.0, 0.0, 1.0]])
D_TRUE = np.array([-0.18, 0.06, 0.0008, -0.0005, 0.0])          # [k1, k2, p1, p2, k3](OpenCV の順)
SHAPE = (480, 640)
ROWS, COLS, SPACING = 7, 9, 15.0                                # 7x9 マーク、15 mm ピッチ
MARK_RADIUS = 0.25 * SPACING                                    # 円の半径 [mm]
LEVELS = {"plate": 0.05, "mark": 0.95, "background": 0.1}
BLUR_SIGMA = 0.7                                                # 光学のぼけ [px]
NOISE_BASE = 0.05                                               # 基準の画像雑音(輝度 [0, 1] の σ)
NOISE_SWEEP = (0.02, 0.05, 0.1, 0.2)
PRESMOOTH_SIGMA = 1.2                                           # find_caltab の前の平滑化 [px](単発の雑音画素をマークにしない)
SEEDS = 40                                                      # 雑音を振る門の種の数。rms の相対誤差 ~1/sqrt(2·40) = 11 %
CAL_SEEDS = 40                                                  # 基準の雑音で校正をやり直す種の数(門 2・3 は全部で通す)
SWEEP_BASE = 1000                                               # 雑音を振る門の種の始まり(変えても門が通ることを確かめた)
JITTER_N, JITTER_MM = 18, 0.6                                   # 板を横に ±0.6 mm(像で ~1 px)ずらした配置の数
DIST_MODEL = "k1k2p1p2"
INTR = ("fx", "fy", "cx", "cy")
DIST_NAMES = ("k1", "k2", "p1", "p2")


def board():
    """校正板の記述(``create_caltab``、板中心が原点、(y, x) [mm])と、world の (x, y)。"""
    b = fs.ledger.create_caltab(ROWS, COLS, SPACING)
    return b, b["points"][:, ::-1].copy()


def place(rx, ry, rz, uc, vc, Z):
    """板の中心を理想画素 (col uc, row vc)・奥行き Z [mm] に置く姿勢(板 → カメラ 4x4)。"""
    R = fs.rodrigues([rx, ry, rz])
    t = Z * np.array([(uc - K_TRUE[0, 2]) / K_TRUE[0, 0], (vc - K_TRUE[1, 2]) / K_TRUE[1, 1], 1.0])
    P = np.eye(4)
    P[:3, :3], P[:3, 3] = R, t
    return P


def poses():
    """8 視点。傾き 0.1〜0.4 rad、面内回転 ±0.3 rad、画像の隅まで、Z 430〜560 mm。"""
    return [place(0.30, -0.20, 0.05, 320, 240, 500), place(-0.25, 0.30, -0.10, 330, 250, 520),
            place(0.10, 0.35, 0.20, 215, 165, 470), place(-0.35, -0.15, 0.00, 430, 315, 540),
            place(0.20, 0.10, -0.30, 420, 160, 500), place(0.00, -0.40, 0.10, 210, 320, 530),
            place(0.38, 0.05, 0.25, 300, 300, 560), place(-0.10, -0.30, -0.20, 360, 180, 430)]


def true_pixels(xy, P):
    """板の円の中心を前向きに投影した真の画素 (row, col)(門で比べる側)。"""
    X = np.column_stack([xy, np.zeros(len(xy))])
    uv, depth = fs.project_points(X, K_TRUE, P[:3, :3], P[:3, 3])
    assert np.all(depth > 0)
    return fs.distort_points(uv, K_TRUE, D_TRUE)[:, ::-1]


_RAYS = {}


def _pixel_rays(supersample):
    """画素(標本点)ごとの理想の視線 (x, y, 1) の列(標本の数だけ)。歪みを外す固定点反復は姿勢に依らないので、
    1 度だけ計算して使い回す(値は毎回計算し直したものと同じ)。"""
    if supersample not in _RAYS:
        H, W = SHAPE
        off = (np.arange(supersample) + 0.5) / supersample - 0.5
        rr, cc = np.mgrid[0:H, 0:W].astype(float)
        Kinv = np.linalg.inv(K_TRUE)
        rays = []
        for oy in off:
            for ox in off:
                pix = np.column_stack([(cc + ox).ravel(), (rr + oy).ravel()])
                ideal = fs.undistort_points(pix, K_TRUE, D_TRUE, iters=8)
                rays.append(np.column_stack([ideal, np.ones(len(ideal))]) @ Kinv.T)
        _RAYS[supersample] = rays
    return _RAYS[supersample]


def render_view(xy, P, supersample=3):
    """画素から板へ逆に引いて描く(雑音なし、ぼけあり)。円の像の形は描画が決める。"""
    R, t = P[:3, :3], P[:3, 3]
    n3 = R[:, 2]
    acc = np.zeros(SHAPE)
    half_w, half_h = SPACING * (COLS / 2.0 + 0.5), SPACING * (ROWS / 2.0 + 0.5)   # 板の外形(マーク + 半ピッチの縁)
    for ray in _pixel_rays(supersample):
        den = ray @ n3
        lam = np.where(den > 1e-12, (n3 @ t) / np.where(den > 1e-12, den, 1.0), np.nan)
        Pb = (ray * lam[:, None] - t) @ R                        # 板の座標 (x, y, ~0)
        bx, by = Pb[:, 0], Pb[:, 1]
        on = np.isfinite(lam) & (lam > 0) & (np.abs(bx) <= half_w) & (np.abs(by) <= half_h)
        # 最も近いマークまでの距離(格子なので丸めで求まる)
        ix = np.clip(np.rint(bx / SPACING + (COLS - 1) / 2.0), 0, COLS - 1)
        iy = np.clip(np.rint(by / SPACING + (ROWS - 1) / 2.0), 0, ROWS - 1)
        mx = (ix - (COLS - 1) / 2.0) * SPACING
        my = (iy - (ROWS - 1) / 2.0) * SPACING
        inside = (bx - mx) ** 2 + (by - my) ** 2 <= MARK_RADIUS ** 2
        val = np.where(on, np.where(inside, LEVELS["mark"], LEVELS["plate"]), LEVELS["background"])
        acc += val.reshape(SHAPE)
    img = acc / supersample ** 2
    if BLUR_SIGMA > 0:
        from scipy import ndimage
        img = ndimage.gaussian_filter(img, BLUR_SIGMA, mode="nearest")
    return img


def detect(image, plate):
    """find_caltab で重心を拾い、ホモグラフィ誘導で板の点に対応づける((N,2) row, col、ideal の順)。"""
    image = fs.apply(image, "gaussian", a=(PRESMOOTH_SIGMA - 0.3) / 2.7)   # sigma = 0.3 + 2.7 a
    raw = fs.ledger.find_caltab(image, 0.5)
    nominal = np.array([[SHAPE[1], 0.0, SHAPE[1] / 2.0], [0.0, SHAPE[1], SHAPE[0] / 2.0], [0, 0, 1.0]])
    r = fs.ledger.find_marks_and_pose(image, nominal, plate, thresh=0.5, max_reproj_rms=None)
    n = ROWS * COLS
    if len(raw) != n or len(r["ideal_index"]) != n or not np.array_equal(np.sort(r["ideal_index"]), np.arange(n)):
        raise AssertionError("detection: found %d marks, matched %d of %d" % (len(raw), len(r["ideal_index"]), n))
    # 対応づいた点は find_caltab の点そのもの(並べ替えただけ)
    d = np.linalg.norm(r["marks"][:, None] - raw[None], axis=2).min(1)
    assert d.max() < 1e-9
    out = np.empty((n, 2))
    out[r["ideal_index"]] = r["marks"]
    return out


def calibrate(xy, found):
    return fs.ledger.camera_calibration_lm(xy, found, dist_model=DIST_MODEL)


def errors(cal, P_true):
    """内部パラメータの誤差と、各姿勢の誤差(回転 [rad]、並進 [mm] の 3 成分)。"""
    est = dict(fx=cal["fx"], fy=cal["fy"], cx=cal["cx"], cy=cal["cy"],
               **{n: cal["dist"][i] for i, n in enumerate(("k1", "k2", "p1", "p2"))})
    tru = dict(fx=K_TRUE[0, 0], fy=K_TRUE[1, 1], cx=K_TRUE[0, 2], cy=K_TRUE[1, 2],
               **{n: D_TRUE[i] for i, n in enumerate(("k1", "k2", "p1", "p2"))})
    dp = {k: est[k] - tru[k] for k in est}
    rot, tra = [], []
    for Pe, Pt in zip(cal["poses"], P_true):
        dR = Pe[:3, :3] @ Pt[:3, :3].T
        rot.append(float(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1))))
        tra.append(Pe[:3, 3] - Pt[:3, 3])
    return dp, np.array(rot), np.array(tra)


def noisy(clean, sigma, seed):
    if sigma <= 0:
        return clean
    return np.clip(clean + np.random.default_rng(seed).normal(0.0, sigma, clean.shape), 0.0, 1.0)


def run_once(xy, plate, cleans, truths, sigma, seed):
    found = [detect(noisy(c, sigma, seed * 101 + i), plate) for i, c in enumerate(cleans)]
    det = np.concatenate([np.linalg.norm(f - t, axis=1) for f, t in zip(found, truths)])
    return found, det, calibrate(xy, found)


def mark_eccentricity(xy, Ps, truths):
    """円の像の面積重心 − 中心の像(偏心)を、板の円周を投影した多角形の重心で出す(細かい標本、画素に依らない)。"""
    th = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    out = []
    for P, t in zip(Ps, truths):
        for k, (x, y) in enumerate(xy):
            X = np.column_stack([x + MARK_RADIUS * np.cos(th), y + MARK_RADIUS * np.sin(th), np.zeros_like(th)])
            uv, _ = fs.project_points(X, K_TRUE, P[:3, :3], P[:3, 3])
            uv = fs.distort_points(uv, K_TRUE, D_TRUE)
            px, py = uv[:, 0], uv[:, 1]
            cr = px * np.roll(py, -1) - np.roll(px, -1) * py
            A = cr.sum() / 2.0
            cx_ = ((px + np.roll(px, -1)) * cr).sum() / (6.0 * A)
            cy_ = ((py + np.roll(py, -1)) * cr).sum() / (6.0 * A)
            out.append(np.hypot(cx_ - t[k, 1], cy_ - t[k, 0]))
    return np.array(out)


def grey_centroids(clean, truth, half=10):
    """灰色を重みにした重心(``find_caltab`` に無い経路の比較用)。窓の中心は**真の点**(検出ではない)なので、
    量子化の床だけを見る上限の試験: 重み = 板の輝度を引いた明るさ。"""
    out = np.empty_like(truth)
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1]
    for k, (r, c) in enumerate(truth):
        r0, c0 = int(round(r)), int(round(c))
        w = np.clip(clean[r0 - half:r0 + half + 1, c0 - half:c0 + half + 1] - LEVELS["plate"], 0.0, None)
        out[k] = [r0 + (w * yy).sum() / w.sum(), c0 + (w * xx).sum() / w.sum()]
    return out


def judge(cal, Ps):
    """1 回の校正を門 2・3 の物差しで測る。返り: 各パラメータの |e|/σ、d²、姿勢の誤差/許容の最大 3 成分、誤差。"""
    dp, rot, tra = errors(cal, Ps)
    std = cal["param_std"]
    z = {k: abs(dp[k]) / std[k] for k in INTR + DIST_NAMES}
    e8 = np.array([dp[k] for k in INTR + DIST_NAMES])
    d2 = float(e8 @ np.linalg.solve(cal["covariance"][:8, :8], e8))
    sc = max(std["cx"], std["cy"])
    Zs = np.array([P[2, 3] for P in Ps])
    tol_r = 4 * sc / K_TRUE[0, 0]
    tol_xy = 4 * Zs * sc / K_TRUE[0, 0]
    tol_z = 4 * Zs * std["fx"] / K_TRUE[0, 0]
    pose = (float((rot / tol_r).max()), float((np.hypot(tra[:, 0], tra[:, 1]) / tol_xy).max()),
            float((np.abs(tra[:, 2]) / tol_z).max()))
    return dict(z=z, d2=d2, pose=pose, dp=dp, rot=rot, tra=tra, tol=(tol_r, tol_xy, tol_z))


def main():
    plate, xy = board()
    assert xy.shape == (ROWS * COLS, 2) and abs(xy.mean()) < 1e-9          # 板中心が原点
    Ps = poses()
    truths = [true_pixels(xy, P) for P in Ps]
    for t in truths:                                                       # 全部の円が画像の内側
        assert t[:, 0].min() > 15 and t[:, 0].max() < SHAPE[0] - 15 and t[:, 1].min() > 15 \
            and t[:, 1].max() < SHAPE[1] - 15, "a mark is too close to the image border"
    cleans = [render_view(xy, P) for P in Ps]
    for c in cleans:
        assert np.isfinite(c).all() and float(np.ptp(c)) > 0.5

    # --- 1. 雑音 0 の床(検出の偏心 + 2 値化の量子化)/ noise-free floor --------------------------------
    found0, det0, cal0 = run_once(xy, plate, cleans, truths, 0.0, 0)
    rms0 = float(np.sqrt(np.mean(det0 ** 2)))
    dp0, rot0, tra0 = errors(cal0, Ps)
    print("1. noise-free (this 8-view layout): %d views x %d marks detected; detection vs projected centre rms %.4f px,"
          " max %.4f px" % (len(Ps), ROWS * COLS, rms0, det0.max()))
    print("   calibration: fx err %+.4f px (%+.3f %%), cx err %+.4f px, k1 err %+.2e, reproj rms %.4f px"
          % (dp0["fx"], 100 * dp0["fx"] / K_TRUE[0, 0], dp0["cx"], dp0["k1"], cal0["reproj_rms"]))
    # 2 値の重心の量子化: 境界の画素 ~2πρ 個がそれぞれ面積 U(-1/2, 1/2) の誤差を持つとして、
    # 重心のずれの 2-D rms = 1/sqrt(6πρ)(ρ = 像の円の半径 [px])。
    rho = float(np.mean([MARK_RADIUS * np.sqrt(K_TRUE[0, 0] * K_TRUE[1, 1]) / P[2, 3] for P in Ps]))
    pred0 = 1.0 / np.sqrt(6 * np.pi * rho)
    print("   binary-centroid quantization predicts rms 1/sqrt(6 pi rho) = %.4f px (rho = %.2f px): measured / predicted %.2f"
          % (pred0, rho, rms0 / pred0))
    assert 0.8 < rms0 / pred0 < 1.25
    assert det0.max() < 4 * pred0
    # 偏心(円の像の重心 − 中心の像): 画素に依らない幾何の差。量子化の床に比べて小さいことを数える。
    ecc = mark_eccentricity(xy, Ps, truths)
    print("   centroid offset (centroid of the projected circle - projected centre): max %.4f px, rms %.4f px"
          " (%.2f of the floor)" % (ecc.max(), np.sqrt(np.mean(ecc ** 2)), np.sqrt(np.mean(ecc ** 2)) / pred0))
    assert ecc.max() < 0.03 and np.sqrt(np.mean(ecc ** 2)) < 0.25 * pred0

    # 配置を変えると床の fx の誤差は動く: 板を横に ±0.6 mm ずらした 18 通り(雑音 0)。
    G = cal0["param_std"]["fx"] / cal0["sigma_px"]               # 共分散の利得 σ_fx / σ_px(真値を見ない)
    floor_fx = G * pred0 / np.sqrt(2.0)                          # 床の予測: 利得 x 座標あたりの量子化のずれ(rms)
    jrng = np.random.default_rng(2026)
    fx_err, jit_ratio, k2_err = [dp0["fx"]], [rms0 / pred0], [dp0["k2"]]
    for _ in range(JITTER_N):
        Pj = []
        for P in Ps:
            Q = P.copy()
            Q[:2, 3] += jrng.uniform(-JITTER_MM, JITTER_MM, 2)
            Pj.append(Q)
        tj = [true_pixels(xy, P) for P in Pj]
        fj = [detect(render_view(xy, P), plate) for P in Pj]
        dj = np.concatenate([np.linalg.norm(f - t, axis=1) for f, t in zip(fj, tj)])
        cj = calibrate(xy, fj)
        fx_err.append(cj["fx"] - K_TRUE[0, 0])
        k2_err.append(cj["dist"][1] - D_TRUE[1])
        jit_ratio.append(float(np.sqrt(np.mean(dj ** 2))) / pred0)
    fx_err, k2_err = np.array(fx_err), np.array(k2_err)
    fx_rms = float(np.sqrt(np.mean(fx_err ** 2)))
    print("   %d layouts (this one + %d with the plate moved up to %.1f mm sideways), noise-free: fx error %+.2f ... %+.2f px"
          " (%+.3f ... %+.3f %%), rms %.2f px (%.3f %%); sign: %d positive, %d negative"
          % (len(fx_err), JITTER_N, JITTER_MM, fx_err.min(), fx_err.max(), 100 * fx_err.min() / K_TRUE[0, 0],
             100 * fx_err.max() / K_TRUE[0, 0], fx_rms, 100 * fx_rms / K_TRUE[0, 0], int((fx_err > 0).sum()),
             int((fx_err < 0).sum())))
    print("   floor prediction G * rms_quantisation / sqrt(2) = %.2f px (G = %.2f): measured rms / predicted %.2f;"
          " detection / quantisation prediction over the layouts %.2f ... %.2f"
          % (floor_fx, G, fx_rms / floor_fx, min(jit_ratio), max(jit_ratio)))
    assert 0.5 < fx_rms / floor_fx < 2.0                          # 床の fx の誤差の rms は量子化の予測の 0.5〜2 倍
    assert (fx_err > 0).any() and (fx_err < 0).any()              # 符号は配置で入れ替わる(-0.45 % は 1 配置の値)
    assert 0.8 < min(jit_ratio) and max(jit_ratio) < 1.25          # 検出のずれはどの配置でも量子化の予測のまま

    # 比較: 灰色の重心と、平滑化なしの連結成分の数(find_caltab の 2 つの限界、試験は上の配置の画像で)
    grey = [grey_centroids(c, t) for c, t in zip(cleans, truths)]
    g_det = np.concatenate([np.linalg.norm(g - t, axis=1) for g, t in zip(grey, truths)])
    g_rms = float(np.sqrt(np.mean(g_det ** 2)))
    g_cal = calibrate(xy, grey)
    print("   grey-weighted centroid on the same clean images (window centred on the true point, an upper bound for"
          " the quantisation only): detection rms %.4f px (%.2f of the binary floor); fx err %+.2f px"
          % (g_rms, g_rms / rms0, g_cal["fx"] - K_TRUE[0, 0]))
    assert g_rms < 0.5 * rms0
    n_raw = len(fs.ledger.find_caltab(noisy(cleans[0], 0.2, 7), 0.5))
    print("   find_caltab without the pre-smoothing at sigma_I = 0.2: %d connected components (%d marks)"
          % (n_raw, ROWS * COLS))
    assert n_raw > 10 * ROWS * COLS

    # --- 2-3. 基準の雑音で校正をやり直す / calibrations at the base noise -----------------------------
    cals = []
    for seed in range(1, CAL_SEEDS + 1):
        f_, d_, c_ = run_once(xy, plate, cleans, truths, NOISE_BASE, seed)
        cals.append((f_, d_, c_, judge(c_, Ps)))
    found, det, cal, j1 = cals[0]                                  # 種 1 の詳細を表にする
    dp, rot, tra = j1["dp"], j1["rot"], j1["tra"]
    std = cal["param_std"]
    print("\n2. image noise sigma_I = %.3f, seed 1 of %d: detection rms %.4f px, reprojection rms %.4f px,"
          " sigma_px from residual %.4f" % (NOISE_BASE, CAL_SEEDS, np.sqrt(np.mean(det ** 2)), cal["reproj_rms"],
                                            cal["sigma_px"]))
    print("   %-4s %12s %12s %11s %10s %7s" % ("", "truth", "estimate", "error", "1-sigma", "|e|/s"))
    tru = dict(fx=K_TRUE[0, 0], fy=K_TRUE[1, 1], cx=K_TRUE[0, 2], cy=K_TRUE[1, 2],
               k1=D_TRUE[0], k2=D_TRUE[1], p1=D_TRUE[2], p2=D_TRUE[3])
    table = []
    for k in INTR + DIST_NAMES:
        z = j1["z"][k]
        print("   %-4s %12.6g %12.6g %+11.3g %10.3g %7.2f" % (k, tru[k], tru[k] + dp[k], dp[k], std[k], z))
        table.append([k, "%.6g" % tru[k], "%.6g" % (tru[k] + dp[k]), "%+.3g" % dp[k], "%.3g" % std[k], "%.2f" % z])
        assert std[k] > 0 and np.isfinite(std[k])
    # 8 個は強く相関する(fx と fy は板までの距離を介して同じ向きにずれる)ので、1 つずつの 4σ に加えて
    # 共分散で白色化した距離 d² = eᵀ C⁻¹ e を見る。正しく当たっていれば d² ~ χ²(8)、99.9 % 点は 26.12。
    # 門は種 40 本の全部で通す(1 種だけの性質を主張しない)。
    zmax = np.array([max(c[3]["z"].values()) for c in cals])
    which = [max(c[3]["z"], key=c[3]["z"].get) for c in cals]
    d2s = np.array([c[3]["d2"] for c in cals])
    k2_neg = int(sum(c[2]["dist"][1] < 0 for c in cals))
    print("   all %d seeds: max |e|/sigma over the 8 parameters %.2f (%s), above 2 sigma in %d seeds, above 4 sigma in %d;"
          " d^2 median %.2f, max %.2f (chi^2_8 99.9 %% point 26.12); k2 estimated with the wrong sign in %d seeds"
          % (CAL_SEEDS, zmax.max(), which[int(np.argmax(zmax))], int((zmax > 2).sum()), int((zmax > 4).sum()),
             np.median(d2s), d2s.max(), k2_neg))
    print("   seed 1: Mahalanobis d^2 = %.2f; fx error %.3f %%" % (j1["d2"], 100 * dp["fx"] / K_TRUE[0, 0]))
    assert np.all(zmax < 4.0) and np.all((d2s > 0.0) & (d2s < 26.12))
    print("\n3. poses (8 views), seed 1: rotation err max %.4f deg (tol %.4f); |dt_xy| / tol max %.2f (max %.3f mm);"
          " |dt_z| / tol max %.2f (max %.3f mm)"
          % (np.degrees(rot.max()), np.degrees(j1["tol"][0]), j1["pose"][1], np.hypot(tra[:, 0], tra[:, 1]).max(),
             j1["pose"][2], np.abs(tra[:, 2]).max()))
    pose_max = np.array([c[3]["pose"] for c in cals]).max(0)
    print("   all %d seeds: rotation / tol max %.2f, lateral / tol max %.2f, depth / tol max %.2f"
          % (CAL_SEEDS, *pose_max))
    assert np.all(pose_max < 1.0)

    # --- 4. 雑音を振る / noise sweep ------------------------------------------------------------------
    # 雑音 0 の結果からの「雑音が足した分」だけを見る(量子化の床は種によらず同じなので引き算で消える)。
    # 線形化した最小二乗では Δfx = G·Δpt で、利得 G は共分散から読める: G = σ_fx / σ_px
    # (cov = σ_px² (JᵀJ)⁻¹)。だから予測 Δfx_pred = G·(座標あたりの点のずれの rms)を真値なしで出せる。
    # ★この門は真値を使わない(雑音 0 の自分の結果と、共分散だけ): 真値と突き合わせるのは門 1〜3。
    print("\n4. noise sweep (%d seeds each, seeds from %d), deviations from the noise-free run (self-consistency,"
          " no truth used); gain G = sigma_fx / sigma_px = %.2f" % (SEEDS, SWEEP_BASE, G))
    print("   %8s %14s %14s %14s %8s" % ("sigma_I", "d_pt px/coord", "d_fx rms px", "G * d_pt", "ratio"))
    rows = []
    for s in NOISE_SWEEP:
        dpt, dfx = [], []
        for k in range(SEEDS):
            f, _, c = run_once(xy, plate, cleans, truths, s, SWEEP_BASE + k)
            dpt.append(np.concatenate([fi - f0 for fi, f0 in zip(f, found0)]).ravel())
            dfx.append(c["fx"] - cal0["fx"])
        spt = float(np.sqrt(np.mean(np.concatenate(dpt) ** 2)))
        sfx = float(np.sqrt(np.mean(np.square(dfx))))
        rows.append((s, spt, sfx, G * spt))
        r = rows[-1]
        print("   %8.3f %14.4f %14.4f %14.4f %8.2f" % (r[0], r[1], r[2], r[3], r[2] / r[3]))
    a = np.array(rows)
    slope_pt = float(np.polyfit(np.log(a[:, 1]), np.log(a[:, 2]), 1)[0])
    slope_img = float(np.polyfit(np.log(a[:, 0]), np.log(a[:, 1]), 1)[0])
    ratio = a[:, 2] / a[:, 3]
    print("   log-log slope: d_fx vs d_pt %.2f;  d_pt vs sigma_I %.2f (binary centroid, see (a))"
          % (slope_pt, slope_img))
    assert np.all(np.diff(a[:, 1]) > 0) and np.all(np.diff(a[:, 2]) > 0)     # 単調に増える
    assert 0.7 < slope_pt < 1.5                                              # 種の始まりで 1.04〜1.29 に動く
    assert 0.4 < slope_img < 0.7                                             # 検出点のずれは雑音の ~0.5 乗(理論 0.5)
    assert np.all((ratio > 0.5) & (ratio < 2.0))                             # 共分散の利得どおり
    assert a[-1, 2] > 3 * a[0, 2]                                            # 振れ幅が見える大きさ

    # --- 図 / figures ---------------------------------------------------------------------------------
    img = noisy(cleans[2], NOISE_BASE, 1 * 101 + 2)
    over = np.stack([img, img, img], axis=-1)
    # 拡大: 板の隅のマーク 1 個のまわり 24x24 px を 20 倍(最近傍、元の画像と同じ高さ 480)。十字は副画素の位置に引く。
    Z = 20
    k0 = int(np.argmax(np.hypot(truths[2][:, 0] - SHAPE[0] / 2, truths[2][:, 1] - SHAPE[1] / 2)))
    r0, c0 = (int(round(v)) - 12 for v in truths[2][k0])
    zoom = np.kron(img[r0:r0 + 24, c0:c0 + 24], np.ones((Z, Z)))
    zoom = np.stack([zoom, zoom, zoom], axis=-1)
    for pts, ch in ((found[2], 0), (truths[2], 2)):
        rr = np.clip(np.rint(pts[:, 0]).astype(int), 0, SHAPE[0] - 1)
        cc = np.clip(np.rint(pts[:, 1]).astype(int), 0, SHAPE[1] - 1)
        pure = np.zeros(3)                                                    # 純色(白いマークの上でも見える。
        pure[ch] = 1.0                                                        # 1 チャネルだけ 1.0 にしても白は白のまま)
        arm = 5 if ch == 0 else 2                                             # 検出(赤)は長く、真の中心(青)は短く:
        for d in range(-arm, arm + 1):                                        # 0.1 px のずれだと同じ画素で青が赤を隠す
            over[np.clip(rr + d, 0, SHAPE[0] - 1), cc] = pure
            over[rr, np.clip(cc + d, 0, SHAPE[1] - 1)] = pure
        zr = int(round((pts[k0, 0] - r0 + 0.5) * Z))
        zc = int(round((pts[k0, 1] - c0 + 0.5) * Z))
        col = np.zeros(3)
        col[ch] = 1.0
        zoom[np.clip(np.arange(zr - 50, zr + 51), 0, 24 * Z - 1), zc] = col
        zoom[zr, np.clip(np.arange(zc - 50, zc + 51), 0, 24 * Z - 1)] = col
    res = np.zeros(SHAPE)                                                     # 検出のずれを画素位置に置いた地図
    for f, t in zip(found0, truths):
        for (r_, c_), e in zip(t, np.linalg.norm(f - t, axis=1)):
            res[int(round(r_)) - 2:int(round(r_)) + 3, int(round(c_)) - 2:int(round(c_)) + 3] = e
    # 重ね描きが見えること(以前は白いマークの上に 1 チャネルだけ 1.0 を書いていて、赤も青も 0 画素だった)
    assert int(((over[..., 0] > 0.99) & (over[..., 1] < 0.01) & (over[..., 2] < 0.01)).sum()) > 100
    assert int(((over[..., 2] > 0.99) & (over[..., 0] < 0.01) & (over[..., 1] < 0.01)).sum()) > 100
    for nm, arr in (("view", over), ("zoom", zoom), ("floor map", res)):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, nm
    zerr = float(np.linalg.norm(found[2][k0] - truths[2][k0]))
    figs.save_grid("caltab_chain", [over, zoom, res],
                   captions=["rendered view 3 (sigma_I %.2f): find_caltab red, projected centre blue" % NOISE_BASE,
                             "corner mark x20 (24 px square): offset %.3f px" % zerr,
                             "noise-free detection offset at each mark, all 8 views [px] (rms %.3f)" % rms0],
                   ncols=3, gray=[True, True, False], colorbar=[False, False, True], unit="px",
                   caption="create_caltab -> rendered camera -> find_caltab -> camera_calibration_lm")
    figs.save_table("caltab_chain_params", ["param", "truth", "estimate", "error", "1-sigma (cov)", "|err|/sigma"],
                    table, title="8 rendered views, sigma_I = %.2f, seed 1 of %d" % (NOISE_BASE, CAL_SEEDS),
                    caption="all %d seeds inside 4 sigma of the LM covariance (largest %.2f sigma)"
                    % (CAL_SEEDS, zmax.max()))
    lo, hi = float(np.log10(a[:, 1]).min()), float(np.log10(a[:, 1]).max())
    figs.save_plot("caltab_chain_noise",
                   [("fx deviation, rms of %d seeds (points)" % SEEDS, np.log10(a[:, 1]), np.log10(a[:, 2])),
                    ("covariance prediction G * d_pt (dotted)", np.log10(a[:, 1]), np.log10(a[:, 3])),
                    ("slope 1 reference (dashed)", np.array([lo, hi]),
                     np.log10(a[0, 2]) + np.array([0.0, hi - lo]))],
                   xlabel="log10 detection deviation d_pt [px per coordinate]", ylabel="log10 fx deviation [px]",
                   title="calibration error grows in proportion to the detection error",
                   kinds=["scatter", "line", "line"], styles=[None, "dotted", "dashed"],
                   colors=["emphasis", "neutral", "reference"],
                   caption="image noise sigma_I 0.02-0.2, deviations from the noise-free run; fitted slope %.2f"
                   % slope_pt)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("PASS")


if __name__ == "__main__":
    main()
