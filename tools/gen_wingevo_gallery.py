# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingevo_gallery — 「進化とオペレータ品質保証」ウィングの展示を作る。

## この翼が見せるもの

絵にしやすい題材(フィルタの結果、3D レンダ)と違って、ここで見せたいのは
**アルゴリズムが設計されていく様子**と**バグが見つかる様子**である。どちらも
本来は数字とログの世界にあるので、**可視化の設計そのものが仕事**になる。

作る展示は 13 点(GIF 6 / PNG タイル・グラフ 10 ファイル)。

  1. champion の実力            — 課題ごとのタイル(入力/正解/恒等/手/進化)
  2. 恒等写像に勝てているか      — beat-the-null(6 課題を同じ軸に)
  3. 観測 split と locked の差   — 勝った例と負けた例
  4. ばらつきの開示             — seed を変えると結果がどれだけ動くか (GIF)
  5. 世代とパイプラインの伸縮    — 実走した 24 世代の軌跡 (GIF)
  6. champion の各段            — 中間値のタイル
  7. 同じ鎖を 1 段ずつ歩く      — (GIF)
  8. 署名の収束                 — 数値マスクの前後 (GIF)
  9. 型到達可能性の不動点        — 1 枚の画像から 4 段で 506 op へ (GIF)
 10. 族ごとのカバレッジ内訳      — 「304/417」では分からないもの
 11. 拡散と収束                 — 到達 op が増え、新しい署名が枯れる (GIF)
 12. 無言のバグの見え方          — 例外でなく「もっともらしく違う数字」
 13. 昇格ゲート                 — counterfactual utility と重複判定

## 規律

* **数字はすべて実測**。過去の記録を焼く場合は出どころ(どの JSON か)を
  ``_provenance`` に載せる。走らせて出した数字は ``measured_now`` と印を付ける。
* **描画は Fullseye 自身の ``imagedraw`` op と numpy 合成**。matplotlib は使わない
  (カラーマップも ``fullseye.apply_cmap``)。文字だけは Fullseye にテキスト op が
  無いため PIL を使う。
* **決定的**。乱数はすべて seed 固定、時刻もファイル一覧順にも依存しない。
  同じコマンドを 2 回走らせると PNG の SHA-256 が一致する。
* **タイルにするか原寸で置くかを分ける**(``tools/exhibit_tile.py`` の規約)。
  ありふれた処理結果の比較はタイル、軸ラベル付きグラフと GIF は原寸。

## 使い方

    py -3.11 tools/gen_wingevo_gallery.py                    # 全部
    py -3.11 tools/gen_wingevo_gallery.py --only champions,generations
    py -3.11 tools/gen_wingevo_gallery.py --list

測定は ``out/wingevo/`` にキャッシュする(``--refresh`` で測り直し)。**同じ
キャッシュから作った画像は SHA-256 までビット一致する**(実測済み)。

正直な但し書き: 進化・昇格ゲート・型到達可能性は測り直しても同じ数字になるが、
**連鎖ファザーだけは走行ごとに揺れる**。一部の op が入力次第で巨大な内部確保を
試み、そのときの空きメモリで成功したり例外になったりするためで、実測では同じ
プロセスで先に進化を回すと到達 op が 445 → 433 に動いた。そこで測定は
まっさらな子プロセスに切り出してあり、キャッシュはその 1 回の走行の記録として
扱う(``--refresh`` すると別の走行になる)。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fullseye as fs                                    # noqa: E402  カラーマップ
import imagedraw                                         # noqa: E402  Fullseye の描画 op
from exhibit_tile import (contact_sheet, flipbook, markdown,  # noqa: E402
                          markdown_animation, save_animation, save_exhibit)

ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
THUMBS = os.path.join(ASSETS, "thumbs")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
WORK = os.path.join(_ROOT, "out", "wingevo")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

# 進化の archived champion。robust.py が best-of-N を書いた実走の出力。
CHAMP_DIRS = {
    "photon_denoise": "out/rb_ph",
    "vibration_map": "out/rb_vibration_map",
    "lf_slope": "out/rb_lf",
    "specular_removal": "out/rb_specular_removal",
    "points_denoise": "out/fix_points_denoise",
    "signal_denoise": "out/fix_signal_denoise",
}
#: locked holdout の作り方は baseline.py / evolve.run と同一
#: (``prob.make(n_holdout, size, seed + 20000)``)。ここを変えると
#: 「同じ split で比べる」という前提が崩れる。
LOCKED = dict(n=8, size=64, seed_offset=20_000)

# 配色。赤緑の対で意味を担わせない(色覚に依らず読める組み合わせにする)。
C_BG = (0.047, 0.051, 0.067)
C_PANEL = (0.098, 0.106, 0.129)
C_TEXT = (0.918, 0.925, 0.941)
C_DIM = (0.478, 0.510, 0.561)
C_GRID = (0.169, 0.184, 0.220)
C_EVO = (0.984, 0.792, 0.294)      # 進化
C_HAND = (0.353, 0.706, 1.000)     # 手(既存 op の最良)
C_IDENT = (0.588, 0.612, 0.659)    # 恒等
C_TRUE = (0.129, 0.847, 0.796)     # 正解
C_LOCK = (0.780, 0.541, 0.976)     # locked holdout
C_WARN = (1.000, 0.639, 0.259)     # 注意(見逃し・却下)

FONT_JP = r"C:\Windows\Fonts\meiryo.ttc"
FONT_JP_B = r"C:\Windows\Fonts\meiryob.ttc"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_MONO_B = r"C:\Windows\Fonts\consolab.ttf"
_FONTS: dict = {}


# --------------------------------------------------------------------------- #
# 描画キット(Fullseye の imagedraw op + numpy 合成。matplotlib は使わない)      #
# --------------------------------------------------------------------------- #
def _font(size=14, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _FONTS:
        from PIL import ImageFont
        path = (FONT_MONO_B if bold else FONT_MONO) if mono else \
               (FONT_JP_B if bold else FONT_JP)
        try:
            _FONTS[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONTS[key] = ImageFont.load_default()
    return _FONTS[key]


def canvas(w, h, color=C_BG):
    return np.tile(np.asarray(color, np.float64), (h, w, 1))


def fill(c, y0, y1, x0, x1, color):
    c[int(y0):int(y1), int(x0):int(x1), :] = np.asarray(color, np.float64)


def to_u8(c):
    a = np.asarray(c, np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError("canvas contains NaN/Inf — 黒として焼かない(fail-closed)")
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def text(frame_u8, items):
    """``(x, y, s, color, size, bold[, anchor[, mono]])`` をまとめて焼く。

    Fullseye にテキスト描画 op が無いので、**文字だけ** PIL を使う。図形(線・
    折れ線・円・マーカー)は ``imagedraw`` の op で描いている。
    """
    from PIL import Image, ImageDraw
    im = Image.fromarray(frame_u8)
    d = ImageDraw.Draw(im)
    for it in items:
        x, y, s, col, size, bold = it[:6]
        anchor = it[6] if len(it) > 6 else "la"
        mono = it[7] if len(it) > 7 else False
        # 等幅(consola)は日本語の字形を持たないので、非 ASCII が 1 文字でも
        # 入っていたら日本語フォントへ落とす。落とさないと豆腐(□)になり、
        # **図の中に読めない文字が残っていることに誰も気づけない**。
        if mono and not s.isascii():
            mono = False
        d.text((x, y), s, fill=tuple(int(round(255 * v)) for v in col),
               font=_font(size, bold, mono), anchor=anchor)
    return np.asarray(im)


def dashed(c, p0, p1, color, width=1, dash=6, gap=5):
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    ln = float(np.hypot(x1 - x0, y1 - y0))
    if ln < 1e-9:
        return c
    t = 0.0
    while t < ln:
        t2 = min(t + dash, ln)
        a = (x0 + (x1 - x0) * t / ln, y0 + (y1 - y0) * t / ln)
        b = (x0 + (x1 - x0) * t2 / ln, y0 + (y1 - y0) * t2 / ln)
        c = imagedraw.draw_line(c, a, b, color=color, width=width)
        t = t2 + gap
    return c


class Plot:
    """軸つきの折れ線/棒グラフ。線は ``imagedraw`` の op で引く。"""

    def __init__(self, c, box, xlim, ylim):
        self.c = c
        self.x0, self.y0, self.x1, self.y1 = [int(v) for v in box]
        self.xlim = (float(xlim[0]), float(xlim[1]))
        self.ylim = (float(ylim[0]), float(ylim[1]))

    def X(self, v):
        lo, hi = self.xlim
        f = 0.0 if hi <= lo else (float(v) - lo) / (hi - lo)
        return self.x0 + (self.x1 - self.x0) * float(np.clip(f, 0.0, 1.0))

    def Y(self, v):
        lo, hi = self.ylim
        f = 0.0 if hi <= lo else (float(v) - lo) / (hi - lo)
        return self.y1 - (self.y1 - self.y0) * float(np.clip(f, 0.0, 1.0))

    def grid(self, yticks=(), xticks=()):
        for v in yticks:
            y = self.Y(v)
            self.c = imagedraw.draw_line(self.c, (self.x0, y), (self.x1, y),
                                         color=C_GRID, width=1)
        for v in xticks:
            x = self.X(v)
            self.c = imagedraw.draw_line(self.c, (x, self.y0), (x, self.y1),
                                         color=C_GRID, width=1)
        return self

    def frame(self):
        self.c = imagedraw.draw_line(self.c, (self.x0, self.y1), (self.x1, self.y1),
                                     color=C_DIM, width=1)
        self.c = imagedraw.draw_line(self.c, (self.x0, self.y0), (self.x0, self.y1),
                                     color=C_DIM, width=1)
        return self

    def line(self, xs, ys, color, width=2):
        pts = [(self.X(a), self.Y(b)) for a, b in zip(xs, ys)]
        if len(pts) >= 2:
            self.c = imagedraw.draw_polyline(self.c, pts, color=color, width=width)
        elif len(pts) == 1:
            self.c = imagedraw.draw_markers(self.c, pts, color=color, size=3,
                                            shape="dot")
        return self

    def marks(self, xs, ys, color, size=4, shape="dot", width=2):
        pts = [(self.X(a), self.Y(b)) for a, b in zip(xs, ys)]
        if pts:
            self.c = imagedraw.draw_markers(self.c, pts, color=color, size=size,
                                            shape=shape, width=width)
        return self

    def hline(self, v, color, width=1, dash=None):
        y = self.Y(v)
        if dash:
            self.c = dashed(self.c, (self.x0, y), (self.x1, y), color, width, *dash)
        else:
            self.c = imagedraw.draw_line(self.c, (self.x0, y), (self.x1, y),
                                         color=color, width=width)
        return self

    def vline(self, v, color, width=1, dash=None):
        x = self.X(v)
        if dash:
            self.c = dashed(self.c, (x, self.y0), (x, self.y1), color, width, *dash)
        else:
            self.c = imagedraw.draw_line(self.c, (x, self.y0), (x, self.y1),
                                         color=color, width=width)
        return self

    def hbar(self, v, y, h, color):
        """左端から値 *v* まで水平に塗る棒。"""
        fill(self.c, y, y + h, self.x0 + 1, max(self.x0 + 2, self.X(v)), color)
        return self

    def vbar(self, x_center, v, half_w, color, base=None):
        y_top = self.Y(v)
        y_base = self.y1 if base is None else self.Y(base)
        lo, hi = sorted((y_top, y_base))
        fill(self.c, lo, max(lo + 1, hi), self.X(x_center) - half_w,
             self.X(x_center) + half_w, color)
        return self


def upscale(a, k):
    """最近傍の整数倍拡大。補間しない — 32x32 が 32x32 であることも情報。"""
    return np.repeat(np.repeat(np.asarray(a), int(k), axis=0), int(k), axis=1)


def to_rgb(a):
    a = np.asarray(a, np.float64)
    if a.ndim == 2:
        return np.repeat(np.clip(a, 0, 1)[:, :, None], 3, axis=2)
    return np.clip(a, 0, 1)


def cmap_panel(field, name="viridis", px=256, border=None):
    """スカラー場を Fullseye の ``apply_cmap`` で着色して正方パネルにする。"""
    f = np.asarray(field, np.float64)
    if not np.all(np.isfinite(f)):
        raise ValueError("cmap_panel: 非有限が混ざっている(黒として焼かない)")
    rgb = fs.apply_cmap(f, name)
    k = max(1, px // max(1, max(rgb.shape[:2])))
    out = upscale(rgb, k)
    if border is not None:
        out = np.array(out)
        out[:2, :, :] = border
        out[-2:, :, :] = border
        out[:, :2, :] = border
        out[:, -2:, :] = border
    return out


def curve_panel(px, series, *, ylim=None, xlim=None, title=None, note=None,
                bg=C_PANEL, legend=(), h=None):
    """1-D の系列をパネル 1 枚に描く(``imagedraw`` の折れ線)。"""
    h = px if h is None else h
    c = canvas(px, h, bg)
    box = (34, 26 if title else 12, px - 10, h - 26)
    xs_all = np.concatenate([np.asarray(s["x"], float) for s in series])
    ys_all = np.concatenate([np.asarray(s["y"], float) for s in series])
    xlim = xlim or (float(xs_all.min()), float(xs_all.max()))
    if ylim is None:
        lo, hi = float(ys_all.min()), float(ys_all.max())
        pad = 0.08 * max(1e-9, hi - lo)
        ylim = (lo - pad, hi + pad)
    p = Plot(c, box, xlim, ylim)
    p.grid(yticks=np.linspace(ylim[0], ylim[1], 5)).frame()
    for s in series:
        p.line(s["x"], s["y"], s["color"], s.get("width", 2))
    u8 = to_u8(p.c)
    items = []
    if title:
        items.append((px // 2, 12, title, C_TEXT, 14, True, "ma"))
    if note:
        items.append((px // 2, h - 20, note, C_DIM, 12, False, "ma"))
    for i, (lab, col) in enumerate(legend):
        items.append((40, box[1] + 4 + 16 * i, lab, col, 12, True))
    return np.asarray(text(u8, items), np.float64) / 255.0


# --------------------------------------------------------------------------- #
# 書き出し                                                                      #
# --------------------------------------------------------------------------- #
GIF_BUDGET = 3_000_000


def save_gif(frames_u8, stem, *, fps=6, hold_last_ms=1400, max_bytes=GIF_BUDGET):
    """共通部品 ``save_animation`` で書き、**予算超過なら減色して**書き直す。

    ``save_animation`` は書き戻し検証つきなので基本はそちらに任せる。ただし
    RGB のまま GIF にすると大きくなりすぎることがあるので、3 MB を超えたら
    適応パレットで減色して書き直し、**同じ検証を自分でもう一度やる**。
    """
    from PIL import Image, ImageSequence
    info = save_animation(frames_u8, stem, duration_ms=int(round(1000 / fps)),
                          hold_last_ms=hold_last_ms)
    colors = None
    if info["gif_bytes"] > max_bytes:
        path = info["gif"]
        for n_col in (192, 128, 96, 64):
            pil = [Image.fromarray(f, "RGB").convert(
                "P", palette=Image.ADAPTIVE, colors=n_col) for f in frames_u8]
            dur = [int(round(1000 / fps))] * len(pil)
            dur[-1] = hold_last_ms
            pil[0].save(path, save_all=True, append_images=pil[1:],
                        duration=dur, loop=0, optimize=True, disposal=2)
            colors = n_col
            if os.path.getsize(path) <= max_bytes:
                break
        with Image.open(path) as im:
            n_read = sum(1 for _ in ImageSequence.Iterator(im))
        if n_read != len(frames_u8):
            raise RuntimeError(f"{path}: 読み戻し {n_read} != 期待 {len(frames_u8)}")
        with open(path, "rb") as fh:
            info["gif_sha256"] = hashlib.sha256(fh.read()).hexdigest()
        info["gif_bytes"] = os.path.getsize(path)
        info["frames"] = n_read
    info["colors"] = colors
    info["fps"] = fps
    info["thumb_bytes"] = os.path.getsize(info["thumb"])
    return info


# --------------------------------------------------------------------------- #
# 測定層(すべて seed 固定。キャッシュは速度のためだけにある)                    #
# --------------------------------------------------------------------------- #
def _cache(name, build, refresh=False, log=print):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, f"cache_{name}.json")
    if not refresh and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    log(f"  [measure] {name} ...")
    t = time.time()
    data = build()
    data["_wall_s"] = round(time.time() - t, 1)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    log(f"  [measure] {name} done in {data['_wall_s']}s")
    return data


def _locked_data(prob):
    return prob.make(LOCKED["n"], LOCKED["size"], LOCKED["seed_offset"])


def _champion(problem):
    path = os.path.join(_ROOT, CHAMP_DIRS[problem], f"champion_{problem}.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh), os.path.relpath(path, _ROOT).replace("\\", "/")


def measure_champions(log=print):
    """archived champion を **同じ locked split** で恒等/手と測り直す。

    「比較は必ず同一の split で取る」— 違う抽出どうしを比べると 20 倍近く
    盛れる、というのが docs/EVOLUTION_ENVIRONMENT.md に残っている実測の教訓。
    """
    import ops
    import problems
    rows = {}
    for name in CHAMP_DIRS:
        prob = problems.PROBLEMS[name]
        lo = _locked_data(prob)
        tr = prob.make(14, LOCKED["size"], 0)
        ch, src = _champion(name)
        stages = ops.decode_by_names(ch["pipeline_stages"])
        rows[name] = {
            "unit": prob.unit, "in_sort": prob.in_sort,
            "source": src, "recorded_locked": ch.get("locked_holdout"),
            "recorded_holdout": ch.get("holdout"),
            "seed": ch.get("seed"), "gens": ch.get("gens"), "pop": ch.get("pop"),
            "pipeline": ch["pipeline"],
            "ops": [s["op"] for s in ch["pipeline_stages"] if s["op"] != "identity"],
            "locked_trivial": round(prob.score_stages([], lo), 4),
            "locked_hand": round(prob.score_stages(prob.hand_stages(), lo), 4),
            "locked_champion": round(prob.score_stages(stages, lo), 4),
            "train_hand": round(prob.score_stages(prob.hand_stages(), tr), 4),
            "train_champion": round(prob.score_stages(stages, tr), 4),
            "hand_pipeline": " -> ".join(
                f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in prob.hand_stages()) or "identity",
        }
    return {"rows": rows, "split": LOCKED, "measured_now": True}


def measure_trajectory(problem="photon_denoise", gens=24, pop=16, seed=0, log=print):
    """世代ごとの champion を実走で拾う。

    ``evolve.run`` は世代数以外が同じなら**前半が完全に同じ軌跡**になる(rng の
    消費が世代ごとに閉じている)ので、``gens=1..G`` を順に走らせると G 世代ぶんの
    champion 列が取れる。既存コードを 1 行も変えずに軌跡を得るための手。
    """
    import evolve
    import ops
    import problems
    wd = os.path.join(WORK, "ev")
    os.makedirs(wd, exist_ok=True)
    prob = problems.PROBLEMS[problem]
    lo = _locked_data(prob)
    hist = []
    for g in range(1, gens + 1):
        ch = evolve.run(problem, wd, gens=g, pop=pop, seed=seed, verbose=False)
        stages = ops.decode_by_names(ch["pipeline_stages"])
        hist.append({
            "gen": g, "train": ch["train"], "holdout": ch["holdout"],
            "locked": round(prob.score_stages(stages, lo), 4),
            "ops": [s["op"] for s in ch["pipeline_stages"] if s["op"] != "identity"],
            "stages": [s for s in ch["pipeline_stages"] if s["op"] != "identity"],
        })
    return {"problem": problem, "gens": gens, "pop": pop, "seed": seed,
            "hand_locked": round(prob.score_stages(prob.hand_stages(), lo), 4),
            "trivial_locked": round(prob.score_stages([], lo), 4),
            "unit": prob.unit, "history": hist, "measured_now": True}


def measure_seed_sweep(problems_seeds=(("photon_denoise", 8), ("specular_removal", 8)),
                       gens=12, pop=16, log=print):
    """同じ設定で seed だけを変えて走らせ、**ばらつきをそのまま**記録する。"""
    import evolve
    import problems as P
    wd = os.path.join(WORK, "ev_seeds")
    os.makedirs(wd, exist_ok=True)
    out = {}
    for name, nseeds in problems_seeds:
        prob = P.PROBLEMS[name]
        lo = _locked_data(prob)
        runs = []
        for s in range(nseeds):
            ch = evolve.run(name, wd, gens=gens, pop=pop, seed=s, verbose=False)
            runs.append({"seed": s, "train": ch["train"], "holdout": ch["holdout"],
                         "locked": ch["locked_holdout"],
                         "pipeline": ch["pipeline"]})
            log(f"    {name} seed {s}: train {ch['train']:.4f} "
                f"locked {ch['locked_holdout']:.4f}")
        out[name] = {"runs": runs, "unit": prob.unit,
                     "hand_locked": round(prob.score_stages(prob.hand_stages(), lo), 4),
                     "trivial_locked": round(prob.score_stages([], lo), 4)}
    return {"gens": gens, "pop": pop, "problems": out, "measured_now": True}


def measure_fuzz(chains=600, seed=4242, length=6, explore=0.5, log=print):
    """連鎖ファザーを**まっさらな子プロセスで**回し、途中経過つきで記録する。

    CLI(``tools/chain_fuzz.py``)は最終値しか出さないので、収束の様子を描くには
    途中経過が要る。``run_chain`` をそのまま呼ぶだけで、ファザー側は 1 行も
    変えていない(連鎖固有 seed も CLI と同じ ``seed*1_000_003 + i``)。

    **なぜ子プロセスなのか(実測)**: 同じ引数でも、同じプロセスで先に進化
    (``evolve.run`` を 20 回以上)を走らせてから呼ぶと結果が変わる ―― 実測で
    到達 op 445 → 433、発見 174 → 220。原因は、一部の op が入力次第で巨大な
    内部確保を試み、**そのときの空きメモリで成功したり例外になったりする**ため
    (docs/CHAIN_FUZZ.md の「小さい入力→巨大な内部割当」の家系)。子プロセスに
    分けると CLI 単独実行と同じ数字になり、繰り返しても揃う。
    """
    if os.environ.get("WINGEVO_FUZZ_WORKER") != "1":
        import subprocess
        out = os.path.join(WORK, "_fuzz_worker.json")
        env = dict(os.environ, WINGEVO_FUZZ_WORKER="1", PYTHONUTF8="1",
                   PYTHONHASHSEED="0")
        cmd = [sys.executable, os.path.abspath(__file__), "--fuzz-worker",
               "--chains", str(chains), "--fuzz-seed", str(seed),
               "--fuzz-length", str(length), "--fuzz-explore", str(explore),
               "--fuzz-out", out]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"fuzz worker failed ({r.returncode}):\n"
                               f"{r.stderr[-2000:]}")
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)
    import chain_fuzz as cf
    ops_ = cf.catalog()
    gens = cf.make_generators()
    log_rows, used, rows = [], set(), []
    for i in range(chains):
        cs = seed * 1_000_003 + i
        trace = cf.run_chain(ops_, gens, np.random.default_rng(cs), length,
                             log_rows, chain_seed=cs, explore=explore)
        used.update(trace)
        raw = {(f["kind"], f["op"], f.get("exc", ""), f.get("msg", ""))
               for f in log_rows}
        msk = {cf.signature(f) for f in log_rows}
        rows.append({"chain": i + 1, "covered": len(used),
                     "findings": len(log_rows), "sig_raw": len(raw),
                     "sig_masked": len(msk)})
    kinds = {}
    for f in log_rows:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    by_family = {}
    for name, fam, _i, _o, _fn in ops_:
        hit, miss = by_family.setdefault(fam, [0, 0])
        if name in used:
            hit += 1
        else:
            miss += 1
        by_family[fam] = [hit, miss]
    # 数値マスクが効いた実例(同じ 1 件が数だけ違って別署名になっていたもの)
    groups = {}
    for f in log_rows:
        groups.setdefault(cf.signature(f), set()).add(f.get("msg", ""))
    collapsed = sorted(((len(v), k, sorted(v)) for k, v in groups.items()),
                       key=lambda t: -t[0])
    example = None
    if collapsed and collapsed[0][0] > 1:
        n, key, msgs = collapsed[0]
        example = {"n": n, "op": key[1], "masked": key[3],
                   "raw": msgs[:3]}
    return {"chains": chains, "seed": seed, "length": length, "explore": explore,
            "n_ops": len(ops_), "rows": rows, "kinds": kinds,
            "by_family": by_family, "mask_example": example,
            "measured_now": True}


def measure_reachability(log=print):
    """型到達可能性の不動点。

    「初期プールの型から、入力が揃う op の出力型を足していく」を収束するまで
    回す。**種を 1 つ(image2d)に絞った場合**の段数と、ファザーが実際に持って
    いる 37 種の生成器で始めた場合の両方を測る。
    """
    import chain_fuzz as cf
    ops_ = cf.catalog()
    gens = cf.make_generators()

    def fixpoint(seed_types):
        reach = set(seed_types)
        enabled = set()
        rounds = [{"types": sorted(reach), "new_types": sorted(reach),
                   "n_ops": 0, "new_ops": 0}]
        while True:
            new_ops, added = set(), set()
            for name, _fam, ins, out, _fn in ops_:
                if name in enabled:
                    continue
                if all(t in reach for t in ins):
                    new_ops.add(name)
                    if out not in reach:
                        added.add(out)
            if not new_ops:
                break
            enabled |= new_ops
            reach |= added
            rounds.append({"types": sorted(reach), "new_types": sorted(added),
                           "n_ops": len(enabled), "new_ops": len(new_ops)})
        return rounds, sorted(reach), sorted(enabled)

    r_one, reach_one, en_one = fixpoint(["image2d"])
    r_all, reach_all, en_all = fixpoint(sorted(gens))
    unreachable = sorted(n for n, _f, _i, _o, _fn in ops_ if n not in en_all)
    edges = sorted({(i, out) for _n, _f, ins, out, _fn in ops_ for i in ins})
    return {"n_ops": len(ops_), "seed_types": sorted(gens),
            "rounds_from_image2d": r_one,
            "enabled_from_image2d": len(en_one),
            "types_from_image2d": len(reach_one),
            "rounds_from_all_seeds": len(r_all) - 1,
            "enabled_from_all_seeds": len(en_all),
            "unreachable": unreachable,
            "unreachable_detail": [
                {"op": n, "in": list(ins), "out": out}
                for n, _f, ins, out, _fn in ops_ if n in set(unreachable)],
            "edges": [list(e) for e in edges],
            "all_types": sorted({t for e in edges for t in e}),
            "measured_now": True}


def measure_gate(candidates=("macro_denoise", "tb_lf_epi_slope",
                             "tb_temporal_band_power"), max_existing=40, log=print):
    """昇格ゲートを候補ごとに回す(重複判定 + counterfactual utility + 判定)。"""
    import ops
    import problems as P
    import promote_gate as pg
    out = {}
    for name in candidates:
        op = ops._BY_NAME[name]
        dup = pg.find_behavioural_duplicate(ops, op.fn, op.in_sort, 0.5, 0.5,
                                            limit=max_existing)
        util = pg.counterfactual_utility(ops, P, name, 0.5, 0.5, split="locked",
                                         max_existing=max_existing)
        lib = pg._load_library()
        ok, reason = pg.decide(util, dup, len(lib), pg.DNA_CAPACITY)
        out[name] = {"in_sort": op.in_sort, "out_sort": op.out_sort,
                     "duplicate_of": dup, "promote": bool(ok), "reason": reason,
                     "library_size": len(lib), "capacity": pg.DNA_CAPACITY,
                     "utility": util}
        log(f"    gate {name}: {'PROMOTE' if ok else 'REJECT'} — {reason}")
    return {"candidates": list(candidates), "max_existing": max_existing,
            "min_relative_gain": pg.MIN_RELATIVE_GAIN, "results": out,
            "measured_now": True}


def measure_silent(log=print):
    """「例外は出ないが数だけ違う」実例を実際に走らせて拾う。"""
    import ops
    import problems as P
    m = np.zeros((8, 8))
    m[2, 2] = 1.0
    m[3, 3] = 1.0
    conn = {"conn8": float(ops._blob_count(m, 0, 0)),
            "conn4": float(ops._blob_count(m, 0, 0, connectivity=4))}
    # 型を外すと例外ではなく **スコア 0** になる(壊れたのか外したのか読めない)
    prob = P.PROBLEMS["vibration_map"]
    lo = _locked_data(prob)
    ident = round(prob.score_stages([], lo), 4)
    hand = round(prob.score_stages(prob.hand_stages(), lo), 4)
    shape = list(np.shape(lo["input"][0]))
    return {"blob_count": conn, "diag_mask": m.tolist(),
            "vibration_identity_score": ident, "vibration_hand_score": hand,
            "vibration_input_shape": shape,
            "measured_now": True}


def load_robust(log=print):
    """archived な robust.py の出力(seed ばらつきの開示)を読む。"""
    out = {}
    for name, d in CHAMP_DIRS.items():
        p = os.path.join(_ROOT, d, f"robust_{name}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                out[name] = json.load(fh)
                out[name]["_source"] = os.path.relpath(p, _ROOT).replace("\\", "/")
    return out


def load_coverage_archive():
    """過去に書かれたカバレッジ内訳(族ごと)。数だけでは読めないものの実例。"""
    out = {}
    for key, rel in (("wave8", "out/fuzz_wave8_coverage.json"),
                     ("explore0", "out/cmpcov_0.json"),
                     ("explore03", "out/cmpcov_0.3.json"),
                     ("explore07", "out/cmpcov_0.7.json"),
                     ("beforehints", "out/cov_e0.json")):
        p = os.path.join(_ROOT, rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            out[key] = {"source": rel, "total": d["total"],
                        "covered": len(d["covered"]),
                        "by_family": {f: [len(v["covered"]), len(v["uncovered"])]
                                      for f, v in d["by_family"].items()}}
    return out


# --------------------------------------------------------------------------- #
# パネル作り(課題ごとの絵)                                                     #
# --------------------------------------------------------------------------- #
PANEL_PX = 250


def _photon_norm(v):
    a = np.asarray(v, np.float64).ravel()
    s = a.sum() if a.sum() > 0 else 1.0
    return a / s


def _photon_panel(y, target, label_color, vmax, px=PANEL_PX, zoom=0.06,
                  h=None, labels=True):
    """光子ヒストグラム 1 枚。上段 = 山ぜんぶ、下段 = 背景の帯を拡大。

    面積で正規化して比べる(絶対カウントは光量で動くので、そこは問うていない)。
    **縦軸は全パネル共通**にする。パネルごとに自動で伸ばすと、山の高さが変わって
    見えて「形が変わった」と誤読させる。そして上段だけだと差が出るところ(背景の
    高さ)が潰れるので、下段に同じデータを ``1/zoom`` 倍で拡大して並べる ――
    軸の上限で頭を切って「平らな山」に見せるのは、静かな嘘になる。
    """
    h = px if h is None else h
    t = _photon_norm(target)
    yy = _photon_norm(y)
    hi = vmax * 1.12
    c = canvas(px, h, C_PANEL)
    mid = int(h * 0.54)
    top_box = (56, 16, px - 12, mid - 16)
    bot_box = (56, mid + 14, px - 12, h - 30)
    items = []
    for box, lim, tag in ((top_box, hi, None),
                          (bot_box, vmax * zoom, f"縦軸 x{1 / zoom:.0f} 拡大")):
        p = Plot(c, box, (0, len(t) - 1), (-0.02 * lim, lim))
        p.grid(yticks=np.linspace(0, lim, 3)).frame()
        p.line(np.arange(len(t)), t, C_TRUE, 2)
        p.line(np.arange(len(yy)), yy, label_color, 2)
        c = p.c
        if labels:
            for v in np.linspace(0, lim, 3):
                items.append((box[0] - 6, p.Y(v), f"{v:.3f}", C_DIM, 10, False,
                              "rm", True))
            if tag:
                items.append((box[2], box[1] + 2, tag, C_DIM, 11, False, "ra"))
    return np.asarray(text(to_u8(c), items), np.float64) / 255.0


def problem_panels(name, row):
    """課題 1 件ぶんの 4 パネル(入力=恒等 / 手 / 進化 / 正解)を作る。

    「入力」と「恒等」は定義上まったく同じ絵なので、列を分けない(同じ絵を 2 度
    並べても記事が縦に伸びるだけ)。ラベルに恒等のスコアを書く。

    画像系のパネルは **入力の最大値で共通に正規化**する。パネルごとに自動で
    伸ばすと、明るさの違いという実際の差が消えてしまう。
    """
    import ops
    import problems
    prob = problems.PROBLEMS[name]
    lo = _locked_data(prob)
    inp, tgt = lo["input"][0], lo["items"][0]
    ch, _ = _champion(name)
    out_hand = ops.run_stages(prob.hand_stages(), inp)
    out_evo = ops.run_stages(ops.decode_by_names(ch["pipeline_stages"]), inp)

    if name == "photon_denoise":
        vs = [inp, out_hand, out_evo, tgt]
        vmax = max(float(_photon_norm(v).max()) for v in vs)
        return [_photon_panel(v, tgt, col, vmax, px=PANEL_PX, h=PANEL_PX)
                for v, col in zip(vs, (C_IDENT, C_HAND, C_EVO, C_TRUE))]
    if name == "signal_denoise":
        x = np.arange(len(tgt))

        def sig(y, col):
            y = np.asarray(y, np.float64).ravel()
            return curve_panel(PANEL_PX,
                               [{"x": x, "y": tgt, "color": C_TRUE, "width": 2},
                                {"x": np.arange(len(y)), "y": y, "color": col,
                                 "width": 2}], ylim=(-1.6, 1.6))
        return [sig(inp, C_IDENT), sig(out_hand, C_HAND), sig(out_evo, C_EVO),
                sig(tgt, C_TRUE)]
    if name == "points_denoise":
        def cloud(pts, col):
            p = np.asarray(pts, np.float64)
            c = canvas(PANEL_PX, PANEL_PX, C_PANEL)
            pl = Plot(c, (18, 14, PANEL_PX - 12, PANEL_PX - 22), (-6, 16), (-6, 16))
            pl.grid(yticks=(0, 5, 10), xticks=(0, 5, 10)).frame()
            pl.marks(p[:, 0], p[:, 2], col, size=1, shape="dot")
            return pl.c
        return [cloud(inp, C_IDENT), cloud(out_hand, C_HAND),
                cloud(out_evo, C_EVO), cloud(tgt, C_TRUE)]
    if name == "vibration_map":
        return [
            cmap_panel(np.asarray(inp)[0], "bone", PANEL_PX, border=C_IDENT),
            cmap_panel(np.asarray(out_hand), "viridis", PANEL_PX, border=C_HAND),
            cmap_panel(np.asarray(out_evo), "viridis", PANEL_PX, border=C_EVO),
            cmap_panel(np.asarray(tgt), "viridis", PANEL_PX, border=C_TRUE),
        ]
    if name == "lf_slope":
        lf = np.asarray(inp)
        centre = lf[lf.shape[0] // 2, lf.shape[1] // 2]
        return [
            cmap_panel(centre, "bone", PANEL_PX, border=C_IDENT),
            cmap_panel(np.asarray(out_hand), "turbo", PANEL_PX, border=C_HAND),
            cmap_panel(np.asarray(out_evo), "turbo", PANEL_PX, border=C_EVO),
            cmap_panel(np.asarray(tgt), "turbo", PANEL_PX, border=C_TRUE),
        ]
    if name == "specular_removal":
        scale = max(1e-9, float(np.max(inp)))     # 全パネル共通の正規化

        def rgb(a, border):
            p = np.array(upscale(to_rgb(np.asarray(a, np.float64) / scale), 8))
            p[:2], p[-2:], p[:, :2], p[:, -2:] = border, border, border, border
            return p
        return [rgb(inp, C_IDENT), rgb(out_hand, C_HAND), rgb(out_evo, C_EVO),
                rgb(tgt, C_TRUE)]
    raise KeyError(name)


# --------------------------------------------------------------------------- #
# 展示 1 — champion の実力(課題ごとのタイル)                                    #
# --------------------------------------------------------------------------- #
TITLES = {
    "photon_denoise": "光子計数ヒストグラムのデノイズ(counts)",
    "vibration_map": "振動している場所の地図(video)",
    "lf_slope": "ライトフィールドの視差スロープ(lightfield)",
    "specular_removal": "鏡面(テカり)の除去(rgbimage)",
    "points_denoise": "点群デノイズ(points)",
    "signal_denoise": "1-D 信号デノイズ(signal)",
}
#: 図の中で使う短い呼び名。``TITLES`` を "(" で切ると全角/半角の括弧違いで
#: 「鏡面」のように**意味が消える**ところまで削れてしまうので、表を分けて持つ。
SHORT = {
    "photon_denoise": "光子計数ヒストグラムのデノイズ",
    "vibration_map": "振動している場所の地図",
    "lf_slope": "ライトフィールドの視差スロープ",
    "specular_removal": "鏡面(テカり)の除去",
    "points_denoise": "点群デノイズ",
    "signal_denoise": "1-D 信号デノイズ",
}


def ex_champions(data, log=print):
    out = []
    for name in ("photon_denoise", "vibration_map", "lf_slope", "specular_removal"):
        row = data["champions"]["rows"][name]
        panels = problem_panels(name, row)
        labels = [
            f"入力 = 恒等  {row['locked_trivial']:.4f}",
            f"手(既存最良 1 段)  {row['locked_hand']:.4f}",
            f"進化 champion  {row['locked_champion']:.4f}",
            "正解",
        ]
        gain = (row["locked_champion"] - row["locked_hand"]) / abs(row["locked_hand"])
        sheet = contact_sheet(
            panels, labels, ncols=4, panel_px=250, font_size=15,
            title=f"{TITLES[name]} — 手比 {gain * 100:+.1f}%  [{row['unit']}]")
        stem = f"wingevo_champion_{name}"
        info = save_exhibit(sheet, stem)
        ops_used = ", ".join(f"`{o}`" for o in row["ops"][:4])
        cap = (f"**{TITLES[name]}** ―― 同じ locked holdout(``seed+20000``、"
               f"champion に一度だけ当てる分割)で測り直した実測。恒等 "
               f"{row['locked_trivial']:.4f} / 手 {row['locked_hand']:.4f} / "
               f"進化 {row['locked_champion']:.4f}({row['unit']})= 手比 "
               f"{gain * 100:+.1f}%。使用 op: {ops_used}。")
        out.append({"stem": stem, "kind": "png", "info": info,
                    "md": markdown(stem, TITLES[name], cap),
                    "numbers": {k: row[k] for k in
                                ("locked_trivial", "locked_hand",
                                 "locked_champion", "unit")},
                    "provenance": f"champion={row['source']} / スコアは本スクリプトで実測"})
        log(f"    {stem}: {info['size']} {info['png_bytes'] / 1e3:.0f} kB")
    return out


# --------------------------------------------------------------------------- #
# 展示 2 — 恒等写像に勝てているか(beat-the-null)                                #
# --------------------------------------------------------------------------- #
def ex_beat_null(data, log=print):
    rows = data["champions"]["rows"]
    order = ["photon_denoise", "vibration_map", "lf_slope", "specular_removal",
             "points_denoise", "signal_denoise"]
    W, rowh, top = 1120, 96, 92
    H = top + rowh * len(order) + 78
    c = canvas(W, H)
    x0, x1 = 300, W - 150
    items = [(28, 26, "恒等・手・進化を同じ軸に置く — beat-the-null", C_TEXT, 22, True),
             (28, 58, "各行はその課題の locked holdout。単位が課題ごとに違うので、"
                      "行内で最大値を 1.0 とした相対長さ(数値は絶対値)。",
              C_DIM, 13, False)]
    for i, name in enumerate(order):
        r = rows[name]
        y = top + i * rowh
        fill(c, y, y + rowh - 10, 24, W - 24, C_PANEL)
        vals = [("恒等", r["locked_trivial"], C_IDENT),
                ("手", r["locked_hand"], C_HAND),
                ("進化", r["locked_champion"], C_EVO)]
        hi = max(1e-9, max(v for _l, v, _c in vals))
        p = Plot(c, (x0, y + 8, x1, y + rowh - 20), (0, hi), (0, 1))
        for j, (lab, v, col) in enumerate(vals):
            by = y + 12 + j * 23
            p.hbar(v, by, 17, col)
        c = p.c
        items.append((34, y + 12, SHORT[name], C_TEXT, 15, True))
        items.append((34, y + 36, f"[{r['unit']}]", C_DIM, 12, False))
        items.append((34, y + 56, f"pipeline {len(r['ops'])} 段", C_DIM, 12, False))
        for j, (lab, v, col) in enumerate(vals):
            by = y + 12 + j * 23
            items.append((x0 - 8, by + 8, lab, col, 13, True, "rm"))
            items.append((x1 + 8, by + 8, f"{v:.4f}", col, 13, True, "lm", True))
        # 恒等に負けていないかを明示(負けていれば警告色で書く)
        if r["locked_champion"] < r["locked_trivial"]:
            items.append((x1 + 8, y + rowh - 26, "恒等に負け", C_WARN, 12, True, "lm"))
    items.append((28, H - 52,
                  "恒等が 0.0000 の 2 課題(vibration_map / lf_slope)は「何もしない = "
                  "型が合わないので 0 点」であって、易しいという意味ではない。",
                  C_DIM, 13, False))
    items.append((28, H - 30,
                  "手 = その課題で既存 op 単体の最良(昇格ゲートが全探索して選んだもの)"
                  "。自分が最初に思いついた手ではない。", C_DIM, 13, False))
    img = np.asarray(text(to_u8(c), items), np.float64) / 255.0
    stem = "wingevo_beat_null"
    info = save_exhibit(img, stem)
    cap = ("**恒等写像に勝てているか** ―― 6 課題の locked holdout を同じ軸に。"
           f"進化が手を上回るのは {sum(1 for n in order if rows[n]['locked_champion'] > rows[n]['locked_hand'])}/6 で、"
           f"`specular_removal` は手 {rows['specular_removal']['locked_hand']:.4f} に対し "
           f"進化 {rows['specular_removal']['locked_champion']:.4f} と**負けている**。"
           "「進化が勝った」と言う前に、恒等と手の両方を同じ分割で測る。"
           "使用 op: `decode_by_names`, `run_stages`。")
    log(f"    {stem}: {info['size']}")
    return [{"stem": stem, "kind": "png", "info": info,
             "md": markdown(stem, "beat-the-null 図", cap),
             "numbers": {n: [rows[n]["locked_trivial"], rows[n]["locked_hand"],
                             rows[n]["locked_champion"]] for n in order},
             "provenance": "本スクリプトで locked split を実測(champion は out/rb_* / out/fix_*)"}]


# --------------------------------------------------------------------------- #
# 展示 3 — 観測 split と locked holdout の差                                    #
# --------------------------------------------------------------------------- #
def ex_observed_vs_locked(data, log=print):
    rb = data["robust"]
    rows = data["champions"]["rows"]
    names = [n for n in ("vibration_map", "photon_denoise", "lf_slope",
                         "specular_removal") if n in rb]
    W, H = 1120, 660
    c = canvas(W, H)
    box = (118, 120, W - 260, H - 180)
    p = Plot(c, box, (-0.5, len(names) - 0.5), (0.0, 1.0))
    p.grid(yticks=np.arange(0, 1.01, 0.2)).frame()
    items = [(28, 26, "同じ champion を「観測用 holdout」と「locked holdout」で測る",
              C_TEXT, 22, True),
             (28, 58, "観測用 (seed+10000) は毎世代スコアを見ている分割。"
                      "locked (seed+20000) は champion に一度だけ当てる分割。"
                      "選択に使っていないのは両方だが、見た回数が違う。",
              C_DIM, 13, False)]
    for i, n in enumerate(names):
        d = rb[n]
        obs = d["selected_by_train"]["holdout"]
        lok = d["selected_by_train"]["locked_holdout"]
        sp = d["locked_holdout_spread"]
        p.vbar(i - 0.16, obs, 26, C_EVO)
        p.vbar(i + 0.16, lok, 26, C_LOCK)
        # seed ばらつき(locked)を誤差棒で
        x = p.X(i + 0.16)
        p.c = imagedraw.draw_line(p.c, (x, p.Y(sp["min"])), (x, p.Y(sp["max"])),
                                  color=C_TEXT, width=2)
        for v in (sp["min"], sp["max"]):
            p.c = imagedraw.draw_line(p.c, (x - 9, p.Y(v)), (x + 9, p.Y(v)),
                                      color=C_TEXT, width=2)
        # 手の基準線(同じ locked split で測り直したもの)
        hb = rows[n]["locked_hand"]
        p.c = dashed(p.c, (p.X(i - 0.42), p.Y(hb)), (p.X(i + 0.42), p.Y(hb)),
                     C_HAND, 2, 7, 5)
        # 課題名は日本語だと隣と必ず重なる幅になるので、図の中では problem キー
        # (ASCII)で並べる。日本語の呼び名はキャプション側にある。
        items += [
            (p.X(i), H - 152, n, C_TEXT, 14, True, "ma", True),
            (p.X(i - 0.16), p.Y(obs) - 6, f"{obs:.4f}", C_EVO, 13, True, "md", True),
            (p.X(i + 0.16), p.Y(lok) - 6, f"{lok:.4f}", C_LOCK, 13, True, "md", True),
            (p.X(i), H - 130, f"hand {hb:.4f} / locked std {sp['std']:.4f}",
             C_DIM, 12, False, "ma", True),
            (p.X(i), H - 112,
             f"min {sp['min']:.3f} / max {sp['max']:.3f}", C_DIM, 12, False,
             "ma", True),
        ]
    for v in np.arange(0, 1.01, 0.2):
        items.append((112, p.Y(v), f"{v:.1f}", C_DIM, 11, False, "rm", True))
    c = p.c
    lx = W - 240
    fill(c, 120, 300, lx, W - 24, C_PANEL)
    items += [
        (lx + 14, 132, "凡例", C_TEXT, 14, True),
        (lx + 14, 158, "■ 観測用 holdout", C_EVO, 13, True),
        (lx + 14, 182, "■ locked holdout", C_LOCK, 13, True),
        (lx + 14, 206, "│ seed 間の min–max", C_TEXT, 13, True),
        (lx + 14, 230, "-- 手の基準線(hand)", C_HAND, 13, True),
        (lx + 14, 258, f"seeds = {rb[names[0]]['seeds']} / "
                       f"gens = {rb[names[0]]['gens']}", C_DIM, 12, False),
    ]
    spec = rb["specular_removal"]
    items += [
        (28, H - 62,
         f"`specular_removal`: 観測用では {spec['selected_by_train']['holdout']:.4f} と手に迫って見えたのに、"
         f"locked では {spec['selected_by_train']['locked_holdout']:.4f} まで落ちた"
         f"(seed 間 std {spec['locked_holdout_spread']['std']:.4f})。",
         C_WARN, 14, True),
        (28, H - 38,
         f"勝った `vibration_map` は逆に locked の std が {rb['vibration_map']['locked_holdout_spread']['std']:.4f} と極端に小さい。"
         "ばらつきの開示があって初めて、この 2 つを別物として読める。",
         C_DIM, 13, False),
    ]
    img = np.asarray(text(to_u8(c), items), np.float64) / 255.0
    stem = "wingevo_observed_vs_locked"
    info = save_exhibit(img, stem)
    cap = ("**勝った例と負けた例** ―― 同じ champion でも観測用 holdout と locked "
           f"holdout で数字が動く。`specular_removal` は {spec['selected_by_train']['holdout']:.4f} → "
           f"{spec['selected_by_train']['locked_holdout']:.4f}(seed 間 std "
           f"{spec['locked_holdout_spread']['std']:.4f})、`vibration_map` は "
           f"{rb['vibration_map']['selected_by_train']['holdout']:.4f} → "
           f"{rb['vibration_map']['selected_by_train']['locked_holdout']:.4f}"
           f"(std {rb['vibration_map']['locked_holdout_spread']['std']:.4f})。"
           "使用 op: `robust.run`(記録)、`decode_by_names`(手の測り直し)。")
    log(f"    {stem}: {info['size']}")
    return [{"stem": stem, "kind": "png", "info": info,
             "md": markdown(stem, "観測 split と locked holdout の差", cap),
             "numbers": {n: rb[n]["selected_by_train"] for n in names},
             "provenance": "; ".join(rb[n]["_source"] for n in names)}]


# --------------------------------------------------------------------------- #
# 展示 4 — ばらつきの開示(GIF)                                                 #
# --------------------------------------------------------------------------- #
def ex_seed_spread(data, log=print):
    sw = data["seed_sweep"]["problems"]
    names = list(sw)
    W, H = 1100, 640
    frames = []
    nmax = max(len(sw[n]["runs"]) for n in names)
    for k in range(1, nmax + 1):
        c = canvas(W, H)
        items = [(28, 24, "seed を変えると結果はどれだけ動くか(single-seed の危うさ)",
                  C_TEXT, 22, True),
                 (28, 56, f"同じ課題・同じ設定(gens {data['seed_sweep']['gens']} / "
                          f"pop {data['seed_sweep']['pop']})で seed だけを変えた実走。"
                          "白丸 = その seed の locked holdout。",
                  C_DIM, 13, False)]
        for i, n in enumerate(names):
            runs = sw[n]["runs"][:k]
            y0 = 100 + i * 262
            fill(c, y0, y0 + 246, 24, W - 24, C_PANEL)
            allv = [r["locked"] for r in sw[n]["runs"]] + \
                   [sw[n]["hand_locked"], sw[n]["trivial_locked"]]
            hi = max(allv) * 1.15
            p = Plot(c, (120, y0 + 42, W - 300, y0 + 210), (-0.6, nmax - 0.4), (0, hi))
            p.grid(yticks=np.linspace(0, hi, 5)).frame()
            p.hline(sw[n]["hand_locked"], C_HAND, 2, dash=(7, 5))
            p.hline(sw[n]["trivial_locked"], C_IDENT, 2, dash=(4, 4))
            xs = [r["seed"] for r in runs]
            ys = [r["locked"] for r in runs]
            for x, v in zip(xs, ys):
                p.vbar(x, v, 16, C_LOCK if v >= sw[n]["hand_locked"] else C_WARN)
            p.marks(xs, ys, (1.0, 1.0, 1.0), size=4, shape="dot")
            # best-of-N は train で選ぶ(locked を見て選ばない)
            best = max(runs, key=lambda r: r["train"])
            p.marks([best["seed"]], [best["locked"]], C_EVO, size=9,
                    shape="square", width=3)
            c = p.c
            arr = np.array(ys, float)
            items += [
                (34, y0 + 12, SHORT[n], C_TEXT, 16, True),
                (34, y0 + 214, "seed", C_DIM, 12, False),
                (280, y0 + 12, f"[{sw[n]['unit']}]", C_DIM, 12, False),
                (W - 286, y0 + 46,
                 f"seeds so far  {len(runs)}", C_TEXT, 13, True),
                (W - 286, y0 + 70,
                 f"locked  min {arr.min():.4f}", C_DIM, 13, False, "la", True),
                (W - 286, y0 + 92,
                 f"        max {arr.max():.4f}", C_DIM, 13, False, "la", True),
                (W - 286, y0 + 114,
                 f"        std {arr.std():.4f}", C_TEXT, 13, True, "la", True),
                (W - 286, y0 + 140,
                 f"train で選んだ 1 本 {best['locked']:.4f}", C_EVO, 13, True),
                (W - 286, y0 + 164,
                 f"手 {sw[n]['hand_locked']:.4f}", C_HAND, 13, True),
                (W - 286, y0 + 186,
                 f"恒等 {sw[n]['trivial_locked']:.4f}", C_IDENT, 13, True),
            ]
            for v in np.linspace(0, hi, 5):          # 縦軸の目盛りを実数で書く
                items.append((114, p.Y(v), f"{v:.2f}", C_DIM, 11, False, "rm", True))
            for r in runs:                            # 横軸 = seed 番号
                items.append((p.X(r["seed"]), y0 + 214, str(r["seed"]),
                              C_DIM, 11, False, "ma", True))
            below = int(np.sum(arr < sw[n]["trivial_locked"]))
            if below:
                items.append((W - 286, y0 + 210,
                              f"恒等を下回った seed {below}/{len(runs)}", C_WARN, 13, True))
        frames.append(text(to_u8(c), items))
    # 末尾を複製して「溜め」を作らない — PIL の GIF 最適化は**連続する同一
    # フレームを畳む**ので、書いた枚数と読み戻した枚数が食い違って
    # save_animation の検証に落ちる。溜めは hold_last_ms が担当する。
    info = save_gif(frames, "wingevo_seed_spread", fps=2)
    lines = []
    for n in names:
        arr = np.array([r["locked"] for r in sw[n]["runs"]], float)
        lines.append(f"`{n}` std {arr.std():.4f}(min {arr.min():.4f} / max {arr.max():.4f})")
    cap = ("**ばらつきの開示** ―― seed だけを変えて実走した locked holdout。"
           + " / ".join(lines) +
           "。選択は train でのみ行い(黄枠)、locked は選択に使わない。"
           "1 本だけ走らせて報告すると、この幅がまるごと消える。"
           "使用 op: `evolve.run`, `decode_by_names`。")
    log(f"    wingevo_seed_spread: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_seed_spread", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_seed_spread", "seed ばらつきの開示", cap),
             "numbers": {n: [r["locked"] for r in sw[n]["runs"]] for n in names},
             "provenance": "本スクリプトで実走(evolve.run, seed 0..N-1)"}]


# --------------------------------------------------------------------------- #
# 展示 5 — 世代とパイプラインの伸縮(GIF)                                       #
# --------------------------------------------------------------------------- #
def _runs(seq):
    """連続する重複を畳んだ列(``[5,5,4,4,5]`` → ``[5,4,5]``)。"""
    out = []
    for v in seq:
        if not out or out[-1] != v:
            out.append(v)
    return out


def _first_op_swap(hist):
    """champion の op 集合が最初に入れ替わった世代と、その中身を返す。"""
    for i in range(1, len(hist)):
        before, after = set(hist[i - 1]["ops"]), set(hist[i]["ops"])
        gone, came = sorted(before - after), sorted(after - before)
        if gone and came:
            return hist[i]["gen"], gone[0], came[0]
    return None, None, None


def ex_generations(data, log=print):
    tj = data["trajectory"]
    hist = tj["history"]
    W, H = 1120, 660
    trains = [h["train"] for h in hist]
    holds = [h["holdout"] for h in hist]
    lens = [len(h["ops"]) for h in hist]
    ylo = min(min(trains), min(holds)) - 0.03
    yhi = max(max(trains), max(holds)) + 0.03
    frames = []
    for k in range(1, len(hist) + 1):
        h = hist[k - 1]
        c = canvas(W, H)
        items = [(28, 22, f"世代が進むとパイプラインは伸びも縮みもする — "
                          f"{tj['problem']}(実走)", C_TEXT, 22, True),
                 (28, 54, f"seed {tj['seed']} / pop {tj['pop']} / "
                          f"{tj['gens']} 世代。選択は train のみ。"
                          f"観測用 holdout は毎世代見るが選択には使わない。",
                  C_DIM, 13, False)]
        # 上段左: 適合度
        fill(c, 86, 380, 24, 700, C_PANEL)
        p = Plot(c, (86, 108, 676, 352), (1, len(hist)), (ylo, yhi))
        p.grid(yticks=np.linspace(ylo, yhi, 5),
               xticks=np.arange(4, len(hist) + 1, 4)).frame()
        p.line(range(1, k + 1), trains[:k], C_EVO, 3)
        p.line(range(1, k + 1), holds[:k], C_LOCK, 2)
        p.marks([k], [trains[k - 1]], (1, 1, 1), size=4, shape="dot")
        c = p.c
        items += [
            (168, 92, "適合度", C_TEXT, 15, True),
            (100, 288, "train(選択に使う)", C_EVO, 13, True),
            (100, 308, "観測用 holdout(見るだけ)", C_LOCK, 13, True),
            (86, 358, "世代", C_DIM, 12, False),
            (676, 358, str(len(hist)), C_DIM, 12, False, "ra"),
        ]
        for v in (ylo, (ylo + yhi) / 2, yhi):
            items.append((80, p.Y(v), f"{v:.3f}", C_DIM, 11, False, "rm", True))
        # 上段右: パイプラインの長さ
        fill(c, 86, 380, 716, W - 24, C_PANEL)
        p2 = Plot(c, (760, 132, W - 48, 352), (1, len(hist)),
                  (0, max(lens) + 0.6))
        p2.grid(yticks=range(0, max(lens) + 1)).frame()
        for i in range(k):
            p2.vbar(i + 1, lens[i], 6, C_HAND if i < k - 1 else C_EVO)
        c = p2.c
        items += [(730, 96, "champion の op 数", C_TEXT, 15, True),
                  (760, 358, "世代", C_DIM, 12, False)]
        for v in range(0, max(lens) + 1):
            items.append((754, p2.Y(v), str(v), C_DIM, 11, False, "rm", True))
        # 下段: op の鎖
        fill(c, 396, 560, 24, W - 24, C_PANEL)
        prev = hist[k - 2]["ops"] if k >= 2 else []
        bw = min(232, (W - 80) // max(1, len(h["ops"])))
        for i, opname in enumerate(h["ops"]):
            x = 44 + i * (bw + 10)
            changed = i >= len(prev) or prev[i] != opname
            col = C_EVO if changed else C_HAND
            fill(c, 452, 508, x, x + bw, (0.16, 0.17, 0.21))
            fill(c, 452, 456, x, x + bw, col)
            items.append((x + bw // 2, 480,
                          opname.replace("tb_", ""), C_TEXT, 12, changed, "mm"))
            if i < len(h["ops"]) - 1:
                items.append((x + bw + 5, 480, "→", C_DIM, 14, False, "mm"))
            if changed:
                items.append((x + bw // 2, 520, "前世代から変化", C_EVO, 11, True, "ma"))
        items += [
            (40, 414, f"第 {h['gen']} 世代の champion({len(h['ops'])} 段)",
             C_TEXT, 16, True),
            (W - 40, 414,
             f"train {h['train']:.4f}   observed {h['holdout']:.4f}   "
             f"locked {h['locked']:.4f}", C_TEXT, 15, True, "ra", True),
        ]
        # 下段の注記
        items += [
            (28, 580,
             f"手の基準線(locked) {tj['hand_locked']:.4f} / "
             f"恒等 {tj['trivial_locked']:.4f}  [{tj['unit']}]",
             C_DIM, 13, False),
            (28, 606,
             "train は定義上単調に上がる(より良いものしか champion にしない)。"
             "観測用 holdout は上下する — そこが「選択に使っていない」証拠。",
             C_DIM, 13, False),
            (28, 630,
             "op 数は " + " → ".join(str(v) for v in _runs(lens)) +
             " と伸び縮みする。長い方が強いとは限らない。", C_DIM, 13, False),
        ]
        frames.append(text(to_u8(c), items))
    # 末尾を複製して「溜め」を作らない — PIL の GIF 最適化は**連続する同一
    # フレームを畳む**ので、書いた枚数と読み戻した枚数が食い違って
    # save_animation の検証に落ちる。溜めは hold_last_ms が担当する。
    info = save_gif(frames, "wingevo_generations", fps=3)
    swap_gen, gone, came = _first_op_swap(hist)
    swap = (f"、第 {swap_gen} 世代で `{gone}` が `{came}` に入れ替わった"
            if swap_gen else "")
    cap = (f"**世代が進むとパイプラインが伸びる/縮む** ―― `{tj['problem']}` を "
           f"seed {tj['seed']} / pop {tj['pop']} で {tj['gens']} 世代、実際に走らせた軌跡。"
           f"train は {trains[0]:.4f} → {trains[-1]:.4f}、op 数は "
           + " → ".join(str(v) for v in _runs(lens)) + " と伸び縮みし" + swap +
           "。観測用 holdout は上下する(選択に使っていないので単調ではない)。"
           "使用 op: `evolve.run`, `ops.decode_by_names`。")
    log(f"    wingevo_generations: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_generations", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_generations", "世代ごとの champion", cap),
             "numbers": {"train": trains, "holdout": holds, "len": lens},
             "provenance": "本スクリプトで実走(evolve.run gens=1..24)"}]


# --------------------------------------------------------------------------- #
# 展示 6/7 — champion のパイプラインをコマ送りで(flipbook GIF)                   #
# --------------------------------------------------------------------------- #
def _stage_states(problem):
    """champion の鎖を 1 段ずつ適用して中間値とスコアを返す。

    各段の値を**その場で最終出力とみなして**採点する。段ごとのスコアは単調とは
    限らない ― 途中で下げてから最後に取り返す鎖を進化は平気で見つけるので、
    そこが見えるようにしておく。
    """
    import ops
    import problems
    prob = problems.PROBLEMS[problem]
    lo = _locked_data(prob)
    inp, tgt = lo["input"][0], lo["items"][0]
    ch, src = _champion(problem)
    specs = [s for s in ch["pipeline_stages"] if s["op"] != "identity"]
    states, scores = [np.asarray(inp, np.float64)], []
    v = inp
    for s in specs:
        v = ops.run_stages(ops.decode_by_names([s]), v)
        states.append(np.asarray(v, np.float64))
        scores.append(round(float(prob.score_value(v, tgt)), 4))
    return prob, specs, states, scores, tgt, src


def _photon_frame(y, target, color, vmax, w=1040, h=560):
    """光子ヒストグラムのコマ 1 枚(上段 = 山ぜんぶ、下段 = 背景の帯を拡大)。"""
    body = _photon_panel(y, target, color, vmax, px=w, h=h - 44)
    c = canvas(w, h, C_BG)
    c[44:44 + body.shape[0], :body.shape[1]] = body
    items = [(72, 14, "正解(背景ゼロ・雑音なし)", C_TRUE, 13, True),
             (360, 14, "現在の値(面積で正規化)", color, 13, True),
             (w - 20, 14, "横軸 = 時間ビン 0..255", C_DIM, 12, False, "ra")]
    return np.asarray(text(to_u8(c), items), np.float64) / 255.0


def ex_stage_photon(data, log=print):
    """勝った champion の中身 — 光子族だけで閉じた 4 段。"""
    problem = "photon_denoise"
    row = data["champions"]["rows"][problem]
    prob, specs, states, scores, tgt, src = _stage_states(problem)

    def _norm_max(v):
        a = np.asarray(v, np.float64).ravel()
        s = a.sum() if a.sum() > 0 else 1.0
        return float(np.max(a / s))
    vmax = max(_norm_max(v) for v in states + [tgt])
    frames = [_photon_frame(states[0], tgt, C_IDENT, vmax)]
    labels = [f"入力(この時点のスコア {row['locked_trivial']:.4f})"]
    for i, s in enumerate(specs):
        frames.append(_photon_frame(states[i + 1], tgt, C_EVO, vmax))
        labels.append(f"{s['op']}  →  {scores[i]:.4f}")
    frames.append(_photon_frame(tgt, tgt, C_TRUE, vmax))
    labels.append(f"正解(手の基準線は {row['locked_hand']:.4f})")
    book = flipbook(frames, labels,
                    title=f"champion の各段 — {problem}")
    info = save_gif(book, "wingevo_stage_photon", fps=1.2)
    chain = " → ".join(f"`{s['op']}`" for s in specs)
    cap = ("**champion のパイプライン図(各段の中間値)** ―― " + chain +
           " の 4 段。各段を最終出力とみなしたスコアは "
           + " → ".join(f"{v:.4f}" for v in scores) +
           f"(恒等 {row['locked_trivial']:.4f} / 手 {row['locked_hand']:.4f} / "
           f"鎖ぜんぶで {row['locked_champion']:.4f})。"
           "光子族だけで閉じた合成 = 新しい族が「単体で使える op」ではなく"
           "「op を繋いだ手順」として価値を出した最初の例。")
    log(f"    wingevo_stage_photon: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_stage_photon", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_stage_photon",
                                      "champion の各段(光子計数)", cap),
             "numbers": {"per_stage": scores,
                         "ops": [s["op"] for s in specs]},
             "provenance": f"champion={src} / 中間値は本スクリプトで実測"}]


def _rgbish(a, scale, px=512, w=1000, h=560):
    """(H,W,3) はそのまま、(H,W,4)(四元数)はベクトル部 3 成分を色として出す。

    明るさは**全コマ共通の scale** で割る(コマごとに自動で伸ばすと、暗く
    なったのか明るくなったのかが消える)。コマ送りに載せるので幅は固定。
    """
    arr = np.asarray(a, np.float64)
    note = None
    if arr.ndim == 3 and arr.shape[2] == 4:
        arr = arr[:, :, 1:4]
        note = "quaternion"
    arr = np.clip(arr / scale, 0.0, 1.0)
    k = max(1, px // max(1, arr.shape[0]))
    pan = upscale(to_rgb(arr), k)
    frame = canvas(w, h, C_BG)
    ph, pw = pan.shape[:2]
    y0, x0 = (h - ph) // 2, (w - pw) // 2
    frame[y0:y0 + ph, x0:x0 + pw] = pan
    return frame, note


def ex_stage_specular(data, log=print):
    """負けた champion の中身 — 族をまたいで四元数へ寄り道する鎖。"""
    problem = "specular_removal"
    row = data["champions"]["rows"][problem]
    rb = data["robust"][problem]
    prob, specs, states, scores, tgt, src = _stage_states(problem)
    scale = max(1e-9, float(np.max(np.abs(states[0]))))   # 全コマ共通の明るさ
    f0, _ = _rgbish(states[0], scale)
    frames, labels = [f0], [
        f"入力(テカりのある色画像。恒等 {row['locked_trivial']:.4f})"]
    for i, s in enumerate(specs):
        fr, note = _rgbish(states[i + 1], scale)
        frames.append(fr)
        tag = "(四元数: ベクトル部を色で表示)" if note else ""
        labels.append(f"{s['op']}{tag} → {scores[i]:.4f}")
    ft, _ = _rgbish(tgt, scale)
    frames.append(ft)
    labels.append("正解(テカりが無ければ見えていた絵)")
    book = flipbook(frames, labels,
                    title="負けた champion の各段 — specular_removal")
    info = save_gif(book, "wingevo_stage_specular", fps=1.2)
    cap = ("**族をまたいだ寄り道が「惜しく見えた」例** ―― `specular_removal` の "
           "champion は " + " → ".join(f"`{s['op']}`" for s in specs) +
           "。RGB を四元数に持ち上げて色空間で回し、戻してから鏡面分離する。"
           f"観測用 holdout では {rb['selected_by_train']['holdout']:.4f} と手に迫って"
           f"見えたのに、locked では {row['locked_champion']:.4f} で手 "
           f"{row['locked_hand']:.4f} に**負けている**。"
           f"1 枚目の item に対する段ごとのスコアは "
           + " → ".join(f"{v:.4f}" for v in scores) +
           " で、四元数へ持ち上げている間は 2 段とも 0.0000(型が合わないので"
           "採点対象にならない)。")
    log(f"    wingevo_stage_specular: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_stage_specular", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_stage_specular",
                                      "負けた champion の各段", cap),
             "numbers": {"per_stage": scores,
                         "ops": [s["op"] for s in specs],
                         "observed": rb["selected_by_train"]["holdout"],
                         "locked": row["locked_champion"],
                         "hand": row["locked_hand"]},
             "provenance": f"champion={src} / 中間値は本スクリプトで実測"}]


# --------------------------------------------------------------------------- #
# 展示 8 — 署名の収束(GIF)                                                     #
# --------------------------------------------------------------------------- #
def ex_signature_collapse(data, log=print):
    fz = data["fuzz"]
    rows = fz["rows"]
    W, H = 1100, 620
    step = max(1, len(rows) // 40)
    idxs = list(range(step - 1, len(rows), step))
    if idxs[-1] != len(rows) - 1:
        idxs.append(len(rows) - 1)
    ymax = max(r["findings"] for r in rows) * 1.1
    frames = []
    ex = fz.get("mask_example")
    for j in idxs:
        c = canvas(W, H)
        items = [(28, 22, "同じ 1 件が「別の署名」に化けるのを止める — 署名の収束",
                  C_TEXT, 22, True),
                 (28, 54, f"連鎖ファザーを {fz['chains']} 本(長さ {fz['length']}、"
                          f"seed {fz['seed']}、explore {fz['explore']})実走した途中経過。",
                  C_DIM, 13, False)]
        fill(c, 88, 420, 24, W - 24, C_PANEL)
        p = Plot(c, (96, 112, W - 240, 392), (1, len(rows)), (0, ymax))
        p.grid(yticks=np.linspace(0, ymax, 6),
               xticks=np.arange(0, len(rows) + 1, 100)).frame()
        sub = rows[:j + 1]
        p.line([r["chain"] for r in sub], [r["findings"] for r in sub], C_DIM, 2)
        p.line([r["chain"] for r in sub], [r["sig_raw"] for r in sub], C_WARN, 3)
        p.line([r["chain"] for r in sub], [r["sig_masked"] for r in sub], C_TRUE, 3)
        c = p.c
        r = rows[j]
        items += [
            (96, 398, "連鎖の本数", C_DIM, 12, False),
            (W - 232, 112, "生の発見(のべ)", C_DIM, 13, True),
            (W - 232, 136, f"{r['findings']}", C_DIM, 20, True, "la", True),
            (W - 232, 176, "素の文字列で数えた署名", C_WARN, 13, True),
            (W - 232, 200, f"{r['sig_raw']}", C_WARN, 20, True, "la", True),
            (W - 232, 240, "数値を伏せて数えた署名", C_TRUE, 13, True),
            (W - 232, 264, f"{r['sig_masked']}", C_TRUE, 20, True, "la", True),
            (W - 232, 304, f"連鎖 {r['chain']} / {len(rows)}", C_TEXT, 14, True),
            (W - 232, 330, f"到達 op {r['covered']}/{fz['n_ops']}", C_DIM, 13, False),
        ]
        for v in np.linspace(0, ymax, 6):
            items.append((90, p.Y(v), f"{v:.0f}", C_DIM, 11, False, "rm", True))
        # 実例パネル
        fill(c, 436, 596, 24, W - 24, C_PANEL)
        items.append((40, 448, "数値を伏せると何が起きるか(この走行で実際に起きた例)",
                      C_TEXT, 15, True))
        if ex:
            for i, m in enumerate(ex["raw"][:2]):
                items.append((56, 478 + i * 22, "素: " + m[:118], C_WARN, 12, False,
                              "la", True))
            items.append((56, 478 + 2 * 22, "伏: " + ex["masked"][:118], C_TRUE, 12,
                          False, "la", True))
            items.append((56, 478 + 3 * 22 + 4,
                          f"→ `{ex['op']}` の同じ 1 件が {ex['n']} 通りの文字列で出ていた。"
                          "数を伏せれば 1 件に畳める。", C_DIM, 12, False))
        else:
            items.append((56, 478, "この走行では数値違いの分裂が出なかった。",
                          C_DIM, 12, False))
        frames.append(text(to_u8(c), items))
    # 末尾を複製して「溜め」を作らない — PIL の GIF 最適化は**連続する同一
    # フレームを畳む**ので、書いた枚数と読み戻した枚数が食い違って
    # save_animation の検証に落ちる。溜めは hold_last_ms が担当する。
    info = save_gif(frames, "wingevo_signature_collapse", fps=6)
    last = rows[-1]
    cap = ("**署名の収束** ―― 良いエラーメッセージほど実行固有の数を含むので、"
           "素の文字列で同一視すると同じ 1 件が毎回別署名になる。実走 "
           f"{fz['chains']} 連鎖で、生の発見 {last['findings']} 件 → 素の文字列で "
           f"{last['sig_raw']} 署名 → **数値を伏せて {last['sig_masked']} 署名**"
           f"({100 * (1 - last['sig_masked'] / max(1, last['sig_raw'])):.0f}% 減)。"
           "使用 op: `chain_fuzz.run_chain`, `chain_fuzz.signature`。")
    log(f"    wingevo_signature_collapse: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_signature_collapse", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_signature_collapse", "署名の収束", cap),
             "numbers": {"findings": last["findings"], "sig_raw": last["sig_raw"],
                         "sig_masked": last["sig_masked"]},
             "provenance": "本スクリプトで実走(chain_fuzz.run_chain を in-process)"}]


# --------------------------------------------------------------------------- #
# 展示 9 — 型到達可能性の不動点(GIF)                                           #
# --------------------------------------------------------------------------- #
def ex_type_fixpoint(data, log=print):
    rc = data["reach"]
    types = rc["all_types"]
    n = len(types)
    W, H = 1100, 790
    cx, cy, R = 470, 410, 226
    pos = {}
    for i, t in enumerate(types):
        a = 2 * np.pi * i / n - np.pi / 2
        pos[t] = (cx + R * np.cos(a), cy + R * np.sin(a))
    edges = [tuple(e) for e in rc["edges"] if e[0] in pos and e[1] in pos]
    rounds = rc["rounds_from_image2d"]
    frames = []
    for k in range(len(rounds)):
        reach = set(rounds[k]["types"])
        newt = set(rounds[k]["new_types"])
        c = canvas(W, H)
        # 辺: 両端が到達済みなら明るく
        for a, b in edges:
            if a == b:
                continue
            lit = a in reach and b in reach
            col = (0.20, 0.30, 0.38) if lit else (0.105, 0.115, 0.135)
            c = imagedraw.draw_line(c, pos[a], pos[b], color=col, width=1)
        for t in types:
            x, y = pos[t]
            if t in newt:
                c = imagedraw.draw_circle(c, (x, y), 9, color=C_EVO, fill=True)
                c = imagedraw.draw_circle(c, (x, y), 14, color=C_EVO, width=2)
            elif t in reach:
                c = imagedraw.draw_circle(c, (x, y), 6, color=C_TRUE, fill=True)
            else:
                c = imagedraw.draw_circle(c, (x, y), 4, color=(0.30, 0.32, 0.37),
                                          fill=True)
        items = [(28, 22, "型到達可能性の不動点 — 1 枚の画像から何段で全体に届くか",
                  C_TEXT, 22, True),
                 (28, 54, "節点 = 型、辺 = 「その型を入力に取り、この型を出す op がある」。"
                          "初期プールを image2d 1 種だけにして不動点を回した実測。",
                  C_DIM, 13, False)]
        for i, t in enumerate(types):
            x, y = pos[t]
            ang = np.arctan2(y - cy, x - cx)
            # 円周の上下では隣り合うラベルが重なるので、半径を 1 つおきにずらす。
            # ずらさないと 12 時/6 時付近の型名が読めない(見た目の破綻)。
            rr = R + (20 if i % 2 == 0 else 54)
            lx, ly = cx + rr * np.cos(ang), cy + rr * np.sin(ang)
            col = C_EVO if t in newt else (C_TEXT if t in reach else C_DIM)
            anchor = "lm" if np.cos(ang) >= 0 else "rm"
            items.append((lx, ly, t, col, 11, t in newt, anchor, True))
        px = 852
        fill(c, 104, 380, px, W - 24, C_PANEL)
        items += [
            (px + 14, 116, f"段 {k} / {len(rounds) - 1}", C_TEXT, 18, True),
            (px + 14, 150, "到達した型", C_DIM, 13, False),
            (px + 14, 170, f"{len(reach)} / {n}", C_TRUE, 20, True, "la", True),
            (px + 14, 208, "使えるようになった op", C_DIM, 13, False),
            (px + 14, 228, f"{rounds[k]['n_ops']} / {rc['n_ops']}", C_EVO, 20, True,
             "la", True),
            (px + 14, 266, f"この段で増えた型 {len(newt)}", C_EVO, 13, True),
            (px + 14, 290, f"この段で増えた op {rounds[k]['new_ops']}", C_EVO, 13, True),
            (px + 14, 330, "● 今この段で届いた", C_EVO, 12, True),
            (px + 14, 352, "● すでに届いている", C_TRUE, 12, True),
        ]
        fill(c, 400, 660, px, W - 24, C_PANEL)
        items += [
            (px + 14, 412, "ファザー本体(種 37 型)では", C_TEXT, 14, True),
            (px + 14, 440, f"{rc['rounds_from_all_seeds']} 段で "
                           f"{rc['enabled_from_all_seeds']}/{rc['n_ops']} op",
             C_TRUE, 13, True),
            (px + 14, 464, f"構造的に到達不能 {len(rc['unreachable'])} 件",
             C_WARN if rc["unreachable"] else C_TRUE, 13, True),
        ]
        for i, d in enumerate(rc["unreachable_detail"][:3]):
            items.append((px + 14, 490 + i * 34,
                          f"{d['op']}", C_WARN, 12, True, "la", True))
            items.append((px + 22, 506 + i * 34,
                          f"in={'+'.join(d['in'])} → {d['out']}", C_DIM, 11,
                          False, "la", True))
        items.append((px + 14, 604,
                      "この 2 件は入力型が `any` で、", C_DIM, 11, False))
        items.append((px + 14, 622,
                      "型では絞れない = 専用の引数", C_DIM, 11, False))
        items.append((px + 14, 640,
                      "builder が要る側の話。", C_DIM, 11, False))
        items.append((28, H - 34,
                      f"到達した op は {rounds[0]['n_ops']} → "
                      + " → ".join(str(r["n_ops"]) for r in rounds[1:])
                      + f"。1 枚の画像から始めて {len(rounds) - 1} 段で "
                        f"{rc['enabled_from_image2d']}/{rc['n_ops']} op に届く。",
                      C_DIM, 13, False))
        frames.append(text(to_u8(c), items))
    # 段が 5 コマしかないので 1 コマを長く見せる(複製で伸ばすと PIL の GIF 最適化が
    # 連続同一フレームを畳んでしまい、書いた枚数と読み戻した枚数が食い違う)。
    info = save_gif(frames, "wingevo_type_fixpoint", fps=0.6, hold_last_ms=2600)
    cap = ("**型到達可能性の不動点** ―― 「初期プールの型から、入力が揃う op の出力型を"
           "足していく」を収束まで回す。初期プールを `image2d` 1 種だけにすると "
           f"{len(rounds) - 1} 段で {rc['enabled_from_image2d']}/{rc['n_ops']} op に届き、"
           f"ファザー本体の 37 種の種では {rc['rounds_from_all_seeds']} 段で "
           f"{rc['enabled_from_all_seeds']}/{rc['n_ops']}。"
           f"**構造的に到達不能なのは {len(rc['unreachable'])} 件だけ**"
           f"({', '.join('`' + u + '`' for u in rc['unreachable'])})で、"
           "どちらも入力型が `any` = 型では絞れないので専用の引数 builder が要る。")
    log(f"    wingevo_type_fixpoint: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_type_fixpoint", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_type_fixpoint", "型到達可能性の不動点", cap),
             "numbers": {"rounds": [r["n_ops"] for r in rounds],
                         "unreachable": rc["unreachable"]},
             "provenance": "本スクリプトで計算(chain_fuzz.catalog / make_generators)"}]


# --------------------------------------------------------------------------- #
# 展示 10 — 族ごとのカバレッジ内訳                                              #
# --------------------------------------------------------------------------- #
def ex_coverage_families(data, log=print):
    now = data["fuzz"]["by_family"]
    arch = data["coverage_archive"]
    wave8 = arch.get("wave8")
    fams = sorted(now, key=lambda f: -(now[f][0] + now[f][1]))
    W = 1120
    top = 150
    rowh = 34
    H = top + rowh * len(fams) + 190
    c = canvas(W, H)
    lx0, lx1 = 190, 560
    rx0, rx1 = 700, 1024
    tot_now = sum(v[0] for v in now.values()), sum(sum(v) for v in now.values())
    items = [(28, 24, f"「{tot_now[0]}/{tot_now[1]}」という 1 つの数では、"
                      "残りが頑健なのか到達不能なのか分からない",
              C_TEXT, 22, True),
             (28, 56, "同じ数を族ごとに割ると、その場で読める形になる。"
                      "左 = 本スクリプトの実走、右 = 記録に残る過去の走行。",
              C_DIM, 13, False)]
    items += [
        (lx0, top - 40, f"今回の実走  {tot_now[0]}/{tot_now[1]}", C_TRUE, 16, True),
        (lx0, top - 18, f"{data['fuzz']['chains']} 連鎖 x 長さ "
                        f"{data['fuzz']['length']} / seed {data['fuzz']['seed']}",
         C_DIM, 12, False),
    ]
    if wave8:
        items += [
            (rx0, top - 40, f"記録: wave-8  {wave8['covered']}/{wave8['total']}",
             C_WARN, 16, True),
            (rx0, top - 18, wave8["source"], C_DIM, 12, False, "la", True),
        ]
    for i, f in enumerate(fams):
        y = top + i * rowh
        hit, miss = now[f]
        tot = hit + miss
        items.append((176, y + 12, f, C_TEXT, 13, True, "ra", True))
        fill(c, y + 6, y + 26, lx0, lx1, (0.14, 0.15, 0.18))
        fill(c, y + 6, y + 26, lx0, lx0 + int((lx1 - lx0) * hit / max(1, tot)),
             C_TRUE if hit == tot else C_HAND)
        items.append((lx1 + 8, y + 16, f"{hit}/{tot}",
                      C_TRUE if hit == tot else C_HAND, 13, True, "lm", True))
        if wave8 and f in wave8["by_family"]:
            h2, m2 = wave8["by_family"][f]
            t2 = h2 + m2
            fill(c, y + 6, y + 26, rx0, rx1, (0.14, 0.15, 0.18))
            col = C_TRUE if h2 == t2 else (C_WARN if h2 / max(1, t2) < 0.7 else C_HAND)
            fill(c, y + 6, y + 26, rx0, rx0 + int((rx1 - rx0) * h2 / max(1, t2)), col)
            items.append((rx1 + 8, y + 16, f"{h2}/{t2}", col, 13, True, "lm", True))
    ph_now = now.get("photon")
    ph_w8 = wave8["by_family"].get("photon") if wave8 else None
    note_y = top + rowh * len(fams) + 18
    fill(c, note_y, note_y + 150, 24, W - 24, C_PANEL)
    lines = [
        "内訳にした瞬間に分かったこと(記録):",
        (f"photon 族が {ph_w8[0]}/{ph_w8[0] + ph_w8[1]} — 「fail-closed が効きすぎて "
         f"{ph_w8[1]} op が一度も実行されない」" if ph_w8 else ""),
        (f"同じ族は今回の走行では {ph_now[0]}/{ph_now[0] + ph_now[1]}(引数ヒントを足した後)"
         if ph_now else ""),
        "到達 0 の族は「頑健だから発見が無い」のではなく「そもそも連鎖が入ってこない」",
        "= 狭い sort の症状で、意味がまるで違う。",
    ]
    for i, s in enumerate(l for l in lines if l):
        items.append((44, note_y + 16 + i * 26, s,
                      C_TEXT if i == 0 else C_DIM, 14 if i == 0 else 13, i == 0))
    img = np.asarray(text(to_u8(c), items), np.float64) / 255.0
    stem = "wingevo_coverage_families"
    info = save_exhibit(img, stem)
    cap = ("**族ごとのカバレッジ内訳** ―― 全体の数(今回の実走 "
           f"{tot_now[0]}/{tot_now[1]})だけでは、残りが頑健なのか到達不能なのかを"
           "区別できない。族に割ると"
           + (f"、記録に残る wave-8 では photon 族が {ph_w8[0]}/{ph_w8[0] + ph_w8[1]}"
              "(fail-closed が効きすぎて実行されない)と一目で出る" if ph_w8 else "")
           + "。使用 op: `chain_fuzz.catalog`, `chain_fuzz.run_chain`。")
    log(f"    {stem}: {info['size']}")
    return [{"stem": stem, "kind": "png", "info": info,
             "md": markdown(stem, "族ごとのカバレッジ内訳", cap),
             "numbers": {"now": now, "wave8": wave8},
             "provenance": ("左=本スクリプトで実走 / 右=" +
                            (wave8["source"] if wave8 else "なし"))}]


# --------------------------------------------------------------------------- #
# 展示 11 — 拡散と収束(GIF)                                                    #
# --------------------------------------------------------------------------- #
def ex_diffusion(data, log=print):
    fz = data["fuzz"]
    rows = fz["rows"]
    W, H = 1100, 600
    step = max(1, len(rows) // 40)
    idxs = list(range(step - 1, len(rows), step))
    if idxs[-1] != len(rows) - 1:
        idxs.append(len(rows) - 1)
    # 新しい署名が出た本数(限界発見率)を 50 連鎖ごとに集計
    win = 50
    marg = []
    for r in rows:
        j = r["chain"]
        base = rows[max(0, j - win - 1)]["sig_masked"] if j > win else 0
        marg.append(r["sig_masked"] - base)
    cov_max = fz["n_ops"]
    frames = []
    for j in idxs:
        c = canvas(W, H)
        items = [(28, 22, "拡散すると型プールが広がり、収束すると新しい署名が枯れる",
                  C_TEXT, 22, True),
                 (28, 54, "左 = ランダム連鎖が到達した op の数(拡散)。"
                          f"右 = 直近 {win} 連鎖で新しく出た署名の数(収束)。",
                  C_DIM, 13, False)]
        sub = rows[:j + 1]
        fill(c, 92, 470, 24, 546, C_PANEL)
        p = Plot(c, (110, 120, 520, 430), (1, len(rows)), (0, cov_max))
        p.grid(yticks=np.linspace(0, cov_max, 6),
               xticks=np.arange(0, len(rows) + 1, 150)).frame()
        p.line([r["chain"] for r in sub], [r["covered"] for r in sub], C_TRUE, 3)
        p.marks([sub[-1]["chain"]], [sub[-1]["covered"]], (1, 1, 1), size=4)
        c = p.c
        items += [(44, 100, "拡散 — 到達した op", C_TRUE, 16, True),
                  (110, 438, "連鎖の本数", C_DIM, 12, False),
                  (520, 130, f"{sub[-1]['covered']}/{cov_max}", C_TRUE, 22, True,
                   "ra", True)]
        for v in np.linspace(0, cov_max, 6):
            items.append((104, p.Y(v), f"{v:.0f}", C_DIM, 11, False, "rm", True))
        fill(c, 92, 470, 566, W - 24, C_PANEL)
        mmax = max(1, max(marg))
        p2 = Plot(c, (640, 120, W - 46, 430), (1, len(rows)), (0, mmax * 1.15))
        p2.grid(yticks=np.linspace(0, mmax, 5),
                xticks=np.arange(0, len(rows) + 1, 150)).frame()
        p2.line([r["chain"] for r in sub], [marg[r["chain"] - 1] for r in sub],
                C_EVO, 2)
        c = p2.c
        items += [(586, 100, f"収束 — 直近 {win} 連鎖の新署名", C_EVO, 16, True),
                  (640, 438, "連鎖の本数", C_DIM, 12, False),
                  (W - 46, 130, f"{marg[j]}", C_EVO, 22, True, "ra", True)]
        for v in np.linspace(0, mmax, 5):
            items.append((634, p2.Y(v), f"{v:.0f}", C_DIM, 11, False, "rm", True))
        items += [
            (28, 492,
             f"連鎖 {sub[-1]['chain']}/{len(rows)}  到達 op {sub[-1]['covered']}/{cov_max}  "
             f"署名 {sub[-1]['sig_masked']}  のべ発見 {sub[-1]['findings']}",
             C_TEXT, 15, True, "la", True),
            (28, 522,
             "到達 op は " + " / ".join(
                 f"{m} 連鎖 {rows[m - 1]['covered']}"
                 for m in (100, 200, 400, len(rows)) if m <= len(rows)) +
             f" と伸びが鈍る一方、新しい署名は最後まで細く出続ける"
             " — この 2 つは別の速さで進む。", C_DIM, 13, False),
            (28, 548,
             f"この走行の内訳: " + ", ".join(f"{k} {v}" for k, v in
                                            sorted(fz["kinds"].items())) +
             "(CONTRACT = 文書化された ValueError = fail-closed が仕事をした側)",
             C_DIM, 13, False),
            (28, 574,
             "「発見ゼロ」は頑健さの証拠ではない。到達 op の内訳と一緒に読む。",
             C_DIM, 13, False),
        ]
        frames.append(text(to_u8(c), items))
    # 末尾を複製して「溜め」を作らない — PIL の GIF 最適化は**連続する同一
    # フレームを畳む**ので、書いた枚数と読み戻した枚数が食い違って
    # save_animation の検証に落ちる。溜めは hold_last_ms が担当する。
    info = save_gif(frames, "wingevo_diffusion", fps=6)
    last = rows[-1]
    cap = ("**拡散と収束** ―― ランダム連鎖を "
           f"{fz['chains']} 本張ると到達 op は {rows[min(49, len(rows) - 1)]['covered']}"
           f"(50 連鎖)→ {rows[min(199, len(rows) - 1)]['covered']}(200 連鎖)"
           f"→ {last['covered']}/{fz['n_ops']} と伸びが鈍る一方、"
           f"新しい署名は最後まで細く出続ける。この走行の発見は "
           + ", ".join(f"{k} {v}" for k, v in sorted(fz["kinds"].items())) +
           "。使用 op: `chain_fuzz.run_chain`。")
    log(f"    wingevo_diffusion: {info['frames']} frames "
        f"{info['gif_bytes'] / 1e6:.2f} MB")
    return [{"stem": "wingevo_diffusion", "kind": "gif", "info": info,
             "md": markdown_animation("wingevo_diffusion", "拡散と収束", cap),
             "numbers": {"covered": last["covered"], "kinds": fz["kinds"]},
             "provenance": "本スクリプトで実走(chain_fuzz.run_chain を in-process)"}]


# --------------------------------------------------------------------------- #
# 展示 12 — 無言のバグの見え方                                                  #
# --------------------------------------------------------------------------- #
def ex_silent_bug(data, log=print):
    s = data["silent"]
    g = data["gate"]["results"]["tb_temporal_band_power"]
    bad = [r for r in g["utility"]["per_problem"] if r["best_existing"] == 0.0]
    W, H = 1120, 780
    c = canvas(W, H)
    items = [(28, 24, "無言のバグ ―― 例外は出ない。もっともらしい数字が返る",
              C_TEXT, 22, True),
             (28, 56, "落ちてくれるバグは簡単だ。怖いのは「動いたように見えて、"
                      "数字だけが違う」種類のもの。3 つとも今この場で走らせた実測。",
              C_DIM, 13, False)]
    # (1) 連結性
    y = 102
    fill(c, y, y + 202, 24, W - 24, C_PANEL)
    # 同じ 2 画素を「1 個」と読んだ場合と「2 個」と読んだ場合で塗り分ける。
    # 入力を 2 枚並べても違いは見えない — 違うのはラベルの付き方なので、
    # そこを色にする。
    m = np.asarray(s["diag_mask"], np.float64)
    lab8 = np.zeros(m.shape + (3,), np.float64)
    lab4 = np.zeros(m.shape + (3,), np.float64)
    ys, xs = np.nonzero(m > 0.5)
    for k, (yy, xx) in enumerate(zip(ys, xs)):
        lab8[yy, xx] = C_TRUE                       # 8 連結: 同じ物体 = 同じ色
        lab4[yy, xx] = (C_WARN if k else C_LOCK)    # 4 連結: 別の物体 = 別の色
    pan8 = upscale(lab8, 18)
    pan4 = upscale(lab4, 18)
    ph, pw = pan8.shape[:2]
    c[y + 24:y + 24 + ph, 60:60 + pw] = pan8
    c[y + 24:y + 24 + ph, 60 + pw + 40:60 + 2 * pw + 40] = pan4
    items += [
        (40, y + 8, "1. 同じ絵・同じ op・違う連結性 — 例外は出ず、数だけ変わる",
         C_TEXT, 16, True),
        (60 + pw // 2, y + 30 + ph, f"8 連結 → {s['blob_count']['conn8']:.0f} 個",
         C_TRUE, 15, True, "ma"),
        (60 + pw + 40 + pw // 2, y + 30 + ph,
         f"4 連結 → {s['blob_count']['conn4']:.0f} 個", C_WARN, 15, True, "ma"),
        (60 + 2 * pw + 90, y + 34,
         "対角に接する 2 画素。HALCON の `connection` 既定は 8 連結なので",
         C_DIM, 13, False),
        (60 + 2 * pw + 90, y + 58,
         "4 連結だと 1 個の物体が 2 個に増える。実データでは細胞計数が",
         C_DIM, 13, False),
        (60 + 2 * pw + 90, y + 82,
         "342 対 327 の乖離として現れた(docs/KNOWN_ISSUES.md #1)。",
         C_DIM, 13, False),
        (60 + 2 * pw + 90, y + 116,
         "再現: m=zeros((8,8)); m[2,2]=m[3,3]=1;", C_TEXT, 12, False, "la", True),
        (60 + 2 * pw + 90, y + 136,
         "  ops._blob_count(m,0,0)              -> "
         f"{s['blob_count']['conn8']:.1f}", C_TRUE, 12, False, "la", True),
        (60 + 2 * pw + 90, y + 156,
         "  ops._blob_count(m,0,0,connectivity=4) -> "
         f"{s['blob_count']['conn4']:.1f}", C_WARN, 12, False, "la", True),
    ]
    # (2) 0 割りに近い相対改善
    y = 322
    fill(c, y, y + 226, 24, W - 24, C_PANEL)
    items += [
        (40, y + 8, "2. 基準線が 0 のときの「相対改善」— 昇格ゲートが通してしまう",
         C_TEXT, 16, True),
        (56, y + 40, "op                    candidate   best_existing   relative_gain",
         C_DIM, 13, True, "la", True),
    ]
    show = [r for r in g["utility"]["per_problem"]
            if r["problem"] in ("vibration_map", "signal_denoise", "count")]
    for i, r in enumerate(show):
        col = C_WARN if r["best_existing"] == 0.0 else C_DIM
        items.append((56, y + 66 + i * 24,
                      f"{r['problem']:<20s} {r['candidate']:>9.5f}   "
                      f"{r['best_existing']:>13.5f}   {r['relative_gain']:>+.4g}",
                      col, 13, r["best_existing"] == 0.0, "la", True))
    items += [
        (56, y + 150,
         f"`tb_temporal_band_power` の判定: "
         f"{'PROMOTE' if g['promote'] else 'REJECT'} — {g['reason'][:88]}",
         C_WARN, 14, True),
        (56, y + 176,
         "best_existing が 0.0 だと denom = |0| + 1e-12 になり、相対改善が 7e11 に跳ねる。",
         C_DIM, 13, False),
        (56, y + 200,
         "例外は出ない。ログに出るのは「改善 1 problem」という、読めてしまう文字列だけ。",
         C_DIM, 13, False),
    ]
    # (3) 型を外すと 0 点
    y = 570
    fill(c, y, y + 184, 24, W - 24, C_PANEL)
    items += [
        (40, y + 8, "3. 型を外すと例外ではなく「スコア 0」— 壊れたのか外したのか読めない",
         C_TEXT, 16, True),
        (56, y + 44,
         f"vibration_map の入力は {tuple(s['vibration_input_shape'])} の動画。"
         "何もしないパイプラインは動画をそのまま返す。",
         C_DIM, 13, False),
        (56, y + 72,
         f"恒等の locked スコア {s['vibration_identity_score']:.4f}  "
         f"(手は {s['vibration_hand_score']:.4f})", C_WARN, 15, True, "la", True),
        (56, y + 102,
         "0.0000 は「まったく当たらなかった」ではなく「2-D の地図を返さなかったので"
         "採点対象にならなかった」。", C_DIM, 13, False),
        (56, y + 126,
         "同じ 0.0000 が「型を外した」と「本当に外れた」の両方を意味するので、"
         "表の 0 は必ず内訳と一緒に読む。", C_DIM, 13, False),
        (56, y + 152,
         "この 3 つに共通するのは、止まらないということ。だから連鎖ファザーは"
         "「例外が出たか」ではなく「宣言型と返りが合うか」まで機械検証する。",
         C_TEXT, 13, True),
    ]
    img = np.asarray(text(to_u8(c), items), np.float64) / 255.0
    stem = "wingevo_silent_bug"
    info = save_exhibit(img, stem)
    cap = ("**無言のバグの見え方** ―― 例外ではなく「もっともらしく違う数字」が返る 3 例。"
           f"(1) 対角に接する 2 画素が 8 連結で {s['blob_count']['conn8']:.0f} 個 / "
           f"4 連結で {s['blob_count']['conn4']:.0f} 個。"
           f"(2) 昇格ゲートの相対改善が、基準線 0.0 との比で "
           f"{bad[0]['relative_gain']:+.4g} に跳ね、それでも判定は "
           f"{'PROMOTE' if g['promote'] else 'REJECT'}。"
           f"(3) 型を外したパイプラインは例外ではなくスコア "
           f"{s['vibration_identity_score']:.4f} を返す。"
           "使用 op: `ops._blob_count`, `promote_gate.counterfactual_utility`。")
    log(f"    {stem}: {info['size']}")
    return [{"stem": stem, "kind": "png", "info": info,
             "md": markdown(stem, "無言のバグの見え方", cap),
             "numbers": {"blob_count": s["blob_count"],
                         "relative_gain_blowup": bad[0] if bad else None,
                         "identity_score": s["vibration_identity_score"]},
             "provenance": "本スクリプトで実測(ops / promote_gate を直接呼ぶ)"}]


# --------------------------------------------------------------------------- #
# 展示 13 — 昇格ゲート                                                          #
# --------------------------------------------------------------------------- #
def ex_promotion_gate(data, log=print):
    g = data["gate"]
    picks = ["macro_denoise", "tb_lf_epi_slope"]
    rows_ch = data["champions"]["rows"]["points_denoise"]
    W, H = 1120, 860
    c = canvas(W, H)
    items = [(28, 24, "昇格ゲート — 「強い」ではなく「既存では届かないところに届く」",
              C_TEXT, 22, True),
             (28, 56, "候補を 1 段として使ったスコアと、「既存語彙の最良 1 段」を"
                      "全 problem で比べる(locked split)。既存で届く分を差し引くのが要点。",
              C_DIM, 13, False)]
    for j, name in enumerate(picks):
        r = g["results"][name]
        y0 = 100 + j * 348
        fill(c, y0, y0 + 330, 24, W - 24, C_PANEL)
        per = r["utility"]["per_problem"]
        # 相対改善が有限に読める範囲に収める(桁あふれ行は別枠で明示)
        finite = [p for p in per if abs(p["relative_gain"]) < 1e6]
        lo = min([p["relative_gain"] for p in finite] + [-1.0])
        hi = max([p["relative_gain"] for p in finite] + [0.6])
        p = Plot(c, (300, y0 + 60, W - 300, y0 + 288), (-0.5, len(finite) - 0.5),
                 (lo * 1.1, hi * 1.15))
        p.grid(yticks=np.linspace(lo, hi, 5)).frame()
        p.hline(0.0, C_DIM, 1)
        p.hline(g["min_relative_gain"], C_TRUE, 2, dash=(6, 5))
        for i, pr in enumerate(finite):
            col = C_EVO if pr["relative_gain"] > g["min_relative_gain"] else C_DIM
            p.vbar(i, pr["relative_gain"], 12, col, base=0.0)
        c = p.c
        for i, pr in enumerate(finite):
            # 課題名は横に並べると必ず重なるので 2 段に振り分ける
            items.append((p.X(i), y0 + 296 + (0 if i % 2 == 0 else 14),
                          pr["problem"][:14], C_DIM, 10, False, "ma", True))
        items += [
            (40, y0 + 14, f"候補 `{name}`  ({r['in_sort']} → {r['out_sort']})",
             C_TEXT, 17, True),
            (40, y0 + 44, "1. counterfactual utility", C_TEXT, 14, True),
            (40, y0 + 72,
             f"評価 {r['utility']['problems_evaluated']} problem", C_DIM, 13, False),
            (40, y0 + 96,
             f"改善 {r['utility']['problems_improved']} problem", C_EVO, 13, True),
            (40, y0 + 120,
             f"最良 {r['utility']['best_relative_gain']:+.4g}", C_EVO, 13, True,
             "la", True),
            (40, y0 + 152, "2. 振る舞いの重複判定", C_TEXT, 14, True),
            (40, y0 + 180,
             (f"重複: {r['duplicate_of']}" if r["duplicate_of"] else "重複なし"),
             C_WARN if r["duplicate_of"] else C_TRUE, 13, True),
            (40, y0 + 212, "3. 容量上限", C_TEXT, 14, True),
            (40, y0 + 240,
             f"DNA 語彙 {r['library_size']}/{r['capacity']}", C_DIM, 13, False),
            (40, y0 + 276,
             ("PROMOTE" if r["promote"] else "REJECT"),
             C_TRUE if r["promote"] else C_WARN, 24, True),
            (40, y0 + 306, r["reason"][:44], C_DIM, 12, False),
            (W - 292, y0 + 60,
             f"点線 = 昇格に要る最低改善 {g['min_relative_gain']:+.1%}",
             C_TRUE, 12, True),
            (W - 292, y0 + 84,
             "(測定誤差以内なら却下)", C_DIM, 12, False),
        ]
        for v in np.linspace(lo, hi, 5):
            items.append((294, p.Y(v), f"{v:+.2f}", C_DIM, 11, False, "rm", True))
        best = max(per, key=lambda q: q["relative_gain"])
        items.append((W - 292, y0 + 120,
                      f"最も伸びた課題 {best['problem']}", C_TEXT, 13, True))
        items.append((W - 292, y0 + 144,
                      f"候補 {best['candidate']:.4f} 対 既存最良 "
                      f"{best['best_existing']:.4f}", C_DIM, 12, False, "la", True))
        items.append((W - 292, y0 + 166,
                      f"既存最良の op = {best['best_existing_op']}", C_DIM, 12,
                      False, "la", True))
    # 端から端までの実証(train で勝ち locked で負けた例)
    y = 796
    fill(c, y, y + 56, 24, W - 24, C_PANEL)
    items += [
        (44, y + 8,
         f"端から端まで通した実証(points_denoise): train で手 "
         f"{rows_ch['train_hand']:.4f} → champion {rows_ch['train_champion']:.4f}"
         f"({(rows_ch['train_champion'] / rows_ch['train_hand'] - 1) * 100:+.2f}%)、",
         C_TEXT, 14, True),
        (44, y + 32,
         f"しかし一度も見ていない locked では手 {rows_ch['locked_hand']:.4f} → "
         f"champion {rows_ch['locked_champion']:.4f}"
         f"({(rows_ch['locked_champion'] / rows_ch['locked_hand'] - 1) * 100:+.2f}%)"
         " = 却下。3 分割の honesty guard が捕まえるために存在する現象そのもの。",
         C_DIM, 13, False),
    ]
    img = np.asarray(text(to_u8(c), items), np.float64) / 255.0
    stem = "wingevo_promotion_gate"
    info = save_exhibit(img, stem)
    a, b = (g["results"][n] for n in picks)
    cap = ("**昇格ゲート** ―― counterfactual utility(既存語彙の最良 1 段との差)/ "
           "振る舞いの重複判定 / 容量上限の 3 つを全部通らないと語彙に入らない。"
           f"`macro_denoise` は {a['utility']['problems_improved']} problem を改善して PROMOTE、"
           f"`tb_lf_epi_slope` は lf_slope を {b['utility']['best_relative_gain']:+.1%} 伸ばすのに"
           f"**`{b['duplicate_of']}` と振る舞いが同じ**なので REJECT。"
           "「強い」だけでは通らない。使用 op: `promote_gate.counterfactual_utility`, "
           "`promote_gate.find_behavioural_duplicate`。")
    log(f"    {stem}: {info['size']}")
    return [{"stem": stem, "kind": "png", "info": info,
             "md": markdown(stem, "昇格ゲート", cap),
             "numbers": {n: {"promote": g["results"][n]["promote"],
                             "reason": g["results"][n]["reason"],
                             "best_relative_gain":
                                 g["results"][n]["utility"]["best_relative_gain"]}
                         for n in picks},
             "provenance": "本スクリプトで実走(promote_gate、max_existing=%d)"
                           % g["max_existing"]}]


# --------------------------------------------------------------------------- #
# 目録                                                                          #
# --------------------------------------------------------------------------- #
EXHIBIT_ORDER = [
    ("champions", "1. 進化した champion の実力", ex_champions),
    ("beat_null", "2. 恒等写像に勝てているか", ex_beat_null),
    ("observed_vs_locked", "3. 勝った例と負けた例", ex_observed_vs_locked),
    ("seed_spread", "4. ばらつきの開示", ex_seed_spread),
    ("generations", "5. 世代が進むとパイプラインが伸びる/縮む", ex_generations),
    ("stage_photon", "6. champion のパイプライン図(各段の中間値)", ex_stage_photon),
    ("stage_specular", "7. 負けた champion の中身(族をまたいだ寄り道)",
     ex_stage_specular),
    ("signature_collapse", "8. 署名の収束", ex_signature_collapse),
    ("type_fixpoint", "9. 型到達可能性の不動点", ex_type_fixpoint),
    ("coverage_families", "10. 族ごとのカバレッジ内訳", ex_coverage_families),
    ("diffusion", "11. 拡散と収束", ex_diffusion),
    ("silent_bug", "12. 無言のバグの見え方", ex_silent_bug),
    ("promotion_gate", "13. 昇格ゲート", ex_promotion_gate),
]

_INTRO = """<!-- tools/gen_wingevo_gallery.py が自動生成。記事本体 (docs/articles/*.md)
     はこのファイルからは触らない。 -->

## 進化とオペレータ品質保証ウィング

この翼で見せるのは、**アルゴリズムが設計されていく様子**と、**バグが見つかる様子**
です。どちらも本来は数字とログの世界にあるので、ここでは可視化そのものを設計して
います。数字はすべて実測で、実走したものと過去の記録から引いたものを区別して
書いてあります。分割の呼び分けは 1 か所だけ覚えてください ―― **観測用 holdout**
(`seed+10000`、毎世代スコアを見るが選択には使わない)と、**locked holdout**
(`seed+20000`、最終 champion に一度だけ当てる)は別物です。

再生成: `py -3.11 tools/gen_wingevo_gallery.py`
"""


def write_exhibit_md(results, meta, log=print):
    os.makedirs(EXHIBITS, exist_ok=True)
    path = os.path.join(EXHIBITS, "wingevo.md")
    lines = [_INTRO, ""]
    for key, title, _fn in EXHIBIT_ORDER:
        if key not in results:
            continue
        lines.append(f"### {title}")
        lines.append("")
        for item in results[key]:
            lines.append(item["md"])
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("#### 数字の出どころ")
    lines.append("")
    lines.append("| 展示 | ファイル | 出どころ |")
    lines.append("|---|---|---|")
    for key, title, _fn in EXHIBIT_ORDER:
        for item in results.get(key, []):
            lines.append(f"| {title} | `{item['stem']}` | {item['provenance']} |")
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    mpath = os.path.join(ASSETS, "_wingevo_meta.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    log(f"  exhibits -> {path}")
    log(f"  meta     -> {mpath}")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="進化 / QA ウィングの展示を作る")
    ap.add_argument("--only", default="", help="comma list of exhibit keys")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="測定キャッシュを捨てる")
    ap.add_argument("--chains", type=int, default=600)
    ap.add_argument("--gens", type=int, default=24)
    # 連鎖ファザーを別プロセスで回すための内部フラグ(直接使う必要は無い)
    ap.add_argument("--fuzz-worker", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--fuzz-seed", type=int, default=4242, help=argparse.SUPPRESS)
    ap.add_argument("--fuzz-length", type=int, default=6, help=argparse.SUPPRESS)
    ap.add_argument("--fuzz-explore", type=float, default=0.5,
                    help=argparse.SUPPRESS)
    ap.add_argument("--fuzz-out", default="", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.fuzz_worker:
        data = measure_fuzz(chains=args.chains, seed=args.fuzz_seed,
                            length=args.fuzz_length, explore=args.fuzz_explore,
                            log=lambda *_a: None)
        os.makedirs(os.path.dirname(os.path.abspath(args.fuzz_out)), exist_ok=True)
        with open(args.fuzz_out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        return 0

    if args.list:
        for key, title, _fn in EXHIBIT_ORDER:
            print(f"{key:22s} {title}")
        return 0

    def log(m):
        print(m, flush=True)

    os.makedirs(WORK, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    t0 = time.time()
    log("[measure] 実測(キャッシュがあれば読む。--refresh で測り直し)")
    data = {
        "champions": _cache("champions", lambda: measure_champions(log),
                            args.refresh, log),
        "trajectory": _cache("trajectory",
                             lambda: measure_trajectory(gens=args.gens, log=log),
                             args.refresh, log),
        "seed_sweep": _cache("seed_sweep", lambda: measure_seed_sweep(log=log),
                             args.refresh, log),
        "fuzz": _cache("fuzz", lambda: measure_fuzz(chains=args.chains, log=log),
                       args.refresh, log),
        "reach": _cache("reach", lambda: measure_reachability(log), args.refresh, log),
        "gate": _cache("gate", lambda: measure_gate(log=log), args.refresh, log),
        "silent": _cache("silent", lambda: measure_silent(log), args.refresh, log),
        "robust": load_robust(log),
        "coverage_archive": load_coverage_archive(),
    }

    wanted = [k.strip() for k in args.only.split(",") if k.strip()] or \
        [k for k, _t, _f in EXHIBIT_ORDER]
    results, failures = {}, []
    for key, title, fn in EXHIBIT_ORDER:
        if key not in wanted:
            continue
        log(f"[build] {title}")
        try:
            results[key] = fn(data, log)
        except Exception as exc:                          # honest: 失敗は隠さない
            import traceback
            traceback.print_exc()
            failures.append((key, str(exc)))
            log(f"[FAIL] {key}: {exc}")

    meta = {"generated_by": "tools/gen_wingevo_gallery.py",
            "exhibits": {k: [{kk: v[kk] for kk in
                              ("stem", "kind", "info", "numbers", "provenance")}
                             for v in vs] for k, vs in results.items()},
            "measurement_config": {
                "locked_split": LOCKED, "fuzz_chains": args.chains,
                "trajectory_gens": args.gens}}
    if len(results) == len(EXHIBIT_ORDER):
        write_exhibit_md(results, meta, log)
    else:
        log("  (部分実行なので docs/articles/exhibits/wingevo.md は書き換えない)")

    log(f"=== done in {time.time() - t0:.1f}s ===")
    for key, _title, _fn in EXHIBIT_ORDER:
        for item in results.get(key, []):
            i = item["info"]
            if item["kind"] == "gif":
                log(f"  {item['stem']:32s} gif {i['gif_bytes'] / 1e6:5.2f} MB  "
                    f"{i['frames']:3d} frames  {i['size']}  colors={i['colors']}")
            else:
                log(f"  {item['stem']:32s} png {i['png_bytes'] / 1e3:6.0f} kB  "
                    f"{i['size']}  sha {i['png_sha256'][:12]}")
    if failures:
        log(f"failures: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
