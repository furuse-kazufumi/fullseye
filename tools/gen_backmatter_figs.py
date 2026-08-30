# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_backmatter_figs — Qiita 総集編記事の後半(文字砂漠)に挿す図版を生成する.
Generate figures for the back half of the Fullseye retrospective article.

方針 / Policy (honest disclosure):
  でっち上げの飾りは作らない。各図の数値は必ず次のどちらか:
    (a) 実測  -- このスクリプトがその場でリポジトリの実装を実行して測った値
    (b) 記事既載 -- 記事 docs/articles/fullseye_overview_qiita_ja.md に既に
                    記録されている実績値(創作ではない)
  各図の関数に (a)/(b) の別をコメントで明記する。

生成物 / Outputs (docs/articles/assets/):
  fig_ci_waterfall.png    -- CI 章: 失敗テスト数の推移 約80→9→1→0 (b)記事既載
  fig_kabsch_margin.png   -- バグ/CI 章: カメラ縮退検定の 14 桁マージン (a)実測
  fig_bug4_curvature.png  -- バグ④章: 合成球 curvedness vs 理論 1/R (a)実測
  fig_rag_corpus.png      -- RAG 章: 実在 per-op ノートのパネル + 3 ステップ
                             (内容はすべて実ファイル/実実行からの引用)
  fig_optional_extras.png -- 限界/導入章: pyproject.toml の extras 依存マップ
                             (パッケージ一覧は pyproject から機械読取)
  fig_*_thumb.jpg         -- 各図の 720px 幅 JPEG サムネ (q85)

Run:  py -3.11 tools/gen_backmatter_figs.py [--figs ci,kabsch,curvature,rag,extras]
"""
from __future__ import annotations

import argparse
import os
import sys
import tomllib

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

# 既存図版 (tools/gen_article_assets.py ほか) と同じダークテーマ定数
BG, FG, MUTED = "#0b0d12", "#e7e9ee", "#8b91a0"
GRID = "#232833"
PANEL = "#131722"
BLUE, ORANGE, GREEN, RED, PURPLE = "#58a6ff", "#f0883e", "#3fb950", "#f85149", "#bc8cff"

matplotlib.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False
MONO_JP = "MS Gothic"  # 等幅かつ日本語グリフを持つフォント(コード引用パネル用)


def _style_ax(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=MUTED, labelcolor=FG)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    ax.title.set_color(FG)


def _save(fig, name: str) -> None:
    out_png = os.path.join(ASSETS_DIR, name + ".png")
    fig.savefig(out_png, dpi=115, facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    im = Image.open(out_png).convert("RGB")
    w, h = im.size
    im = im.resize((720, max(1, h * 720 // w)), Image.LANCZOS)
    im.save(os.path.join(ASSETS_DIR, name + "_thumb.jpg"), "JPEG", quality=85)
    print(f"[ok] {name}.png ({w}x{h}) + {name}_thumb.jpg")


# --------------------------------------------------------------------------- #
# fig 1: CI 失敗テスト数のウォーターフォール
# 数値の出所: (b) 記事既載 — 「数字で見る推移」節の 約80 → 9 → 1 → 0、
#   ローカルフルスイート 6224 passed、CI マトリクス 3.10/3.11/3.12。
#   各波の原因注記も記事の第1波/第2波/最終波の節の記載どおり。創作なし。
# --------------------------------------------------------------------------- #
def fig_ci_waterfall() -> None:
    stages = ["初回 CI", "第1波を修正", "第2波を修正\n(CI 全 green, v0.1.0)", "最終波を修正\n(v0.1.1 即日公開)"]
    values = [80, 9, 1, 0]
    labels = ["約80", "9", "1", "0"]
    notes = [
        "torch を無条件 import\n(feat_harris/spin/shot/fpfh\n→ import ops3d が即死)",
        "残り9件は1件ずつ性質が別:\n・np.cross の2D対応廃止 (numpy 2.x)\n・BLAS の丸め方向で nan\n・縮退検定すり抜け (Py3.12)\n・GCC UBSan の検出漏れ",
        "recon3d が scikit-image を\n無条件 import\n(クリーン venv 検証で発見)",
        "CI green +\ncore-minimal ジョブ拡大\n(素インストールを毎回検証)",
    ]
    x = np.arange(4)
    fig, ax = plt.subplots(figsize=(12.8, 7.2), facecolor=BG)
    _style_ax(ax)
    bars = ax.bar(x, values, width=0.52, color=BLUE, edgecolor=BG, linewidth=1.5, zorder=3)
    bars[3].set_color(GREEN)
    bars[3].set_height(0.0)
    # 段差を繋ぐステップ線(推移を目で追えるように)
    for i in range(3):
        ax.plot([x[i] + 0.26, x[i + 1] - 0.26], [values[i], values[i]],
                color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=2)
        ax.annotate("", xy=(x[i + 1] - 0.26, values[i + 1] + 0.5),
                    xytext=(x[i + 1] - 0.26, values[i]),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0))
    for i, (v, lab) in enumerate(zip(values, labels)):
        ax.text(x[i], v + 2.5, lab, ha="center", va="bottom", fontsize=26,
                fontweight="bold", color=GREEN if v == 0 else FG)
        ax.text(x[i], -13.5, notes[i], ha="center", va="top", fontsize=10.5,
                color=MUTED, linespacing=1.45)
    ax.text(3.28, 3.0, "✓", ha="center", va="bottom", fontsize=19, color=GREEN)
    ax.set_xticks(x, stages, fontsize=12)
    ax.set_ylim(0, 95)
    ax.set_xlim(-0.55, 3.55)
    ax.set_ylabel("失敗テスト数(件)", fontsize=12)
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    ax.set_title("公開前夜 ―― CI 失敗テスト数の推移(3波 + 最終確認1件)", fontsize=16, pad=14)
    ax.text(0.0, 1.013, "", transform=ax.transAxes)
    fig.text(0.5, 0.005,
             "数値は記事記載の実績値。ローカルフルスイートは 6224 passed / "
             "CI は Python 3.10・3.11・3.12 マトリクス + 「numpy+scipy だけで動く」最小構成ジョブ",
             ha="center", fontsize=10.5, color=MUTED)
    fig.subplots_adjust(bottom=0.30, top=0.90)
    _save(fig, "fig_ci_waterfall")


# --------------------------------------------------------------------------- #
# fig 2: カメラ縮退検定(視差の存在検定)の 14 桁マージン
# 数値の出所: (a) 実測 — camera.recover_pose の第一関門と同一の計算
#   (視線ベクトル集合を Kabsch 最適回転で重ね、残差の中央値を見る)を
#   このスクリプトがその場で実行して測る。合成シーン: 8° 回転で
#   純回転ペア(縮退)と 回転+並進 0.5(健全)を比較。
#   記事既載の 3.5e-16 / 1.8e-2 とオーダー一致することも assert で確認。
# --------------------------------------------------------------------------- #
def _measure_kabsch_gate():
    import camera  # noqa: F401  (recover_pose の縮退拒否も併せて実確認する)

    rng = np.random.default_rng(0)
    K = np.array([[800.0, 0, 320], [0, 800, 240], [0, 0, 1]])
    X = rng.uniform([-2, -2, 4], [2, 2, 8], (60, 3))

    def project(X, R, t):
        Xc = X @ R.T + t
        uv = (Xc / Xc[:, 2:3]) @ K.T
        return uv[:, :2]

    def gate_resid(a, b):
        # camera.recover_pose 冒頭の「視差の存在検定」と同じ式
        r1 = np.column_stack([a, np.ones(len(a))]) @ np.linalg.inv(K).T
        r2 = np.column_stack([b, np.ones(len(b))]) @ np.linalg.inv(K).T
        r1 /= np.linalg.norm(r1, axis=1, keepdims=True)
        r2 /= np.linalg.norm(r2, axis=1, keepdims=True)
        U, _, Vt = np.linalg.svd(r2.T @ r1)
        S = np.diag([1.0, 1.0, np.sign(np.linalg.det(U @ Vt))])
        Rf = U @ S @ Vt
        return float(np.median(np.linalg.norm(r2 - r1 @ Rf.T, axis=1)))

    c, s = np.cos(np.deg2rad(8)), np.sin(np.deg2rad(8))
    Rrot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    uv1 = project(X, np.eye(3), np.zeros(3))
    deg = gate_resid(uv1, project(X, Rrot, np.zeros(3)))          # 純回転 = 縮退
    ok = gate_resid(uv1, project(X, Rrot, np.array([0.5, 0, 0])))  # 並進あり = 健全
    # 実装そのものも縮退ペアを拒否することを確認 (honest gate の実挙動)
    import camera as cam
    E = cam.essential_matrix(uv1, project(X, Rrot, np.array([0.5, 0, 0])), K)
    try:
        cam.recover_pose(E, uv1, project(X, Rrot, np.zeros(3)), K)
        raise AssertionError("recover_pose should reject the degenerate pair")
    except ValueError:
        pass
    # 記事既載値 3.5e-16 / 1.8e-2 とオーダーが一致するかの確認(ズレたら実測値を採用)
    assert 1e-17 < deg < 1e-14, deg
    assert 1e-3 < ok < 1e-1, ok
    return deg, ok


def fig_kabsch_margin() -> None:
    deg, ok = _measure_kabsch_gate()
    digits = np.log10(ok / deg)
    print(f"    measured: degenerate={deg:.3g}  healthy={ok:.3g}  margin={digits:.1f} digits")
    fig, ax = plt.subplots(figsize=(12.8, 6.4), facecolor=BG)
    _style_ax(ax)
    y = [1, 0]
    left = 1e-17
    ax.barh(y[0], deg, left=0, height=0.42, color=RED, zorder=3)
    ax.barh(y[1], ok, height=0.42, color=BLUE, zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(left, 1.0)
    ax.set_ylim(-0.75, 1.95)
    ax.set_yticks(y, ["縮退ペア\n(純回転・視差ゼロ)", "健全ペア\n(回転 + 並進)"], fontsize=13)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    ax.set_xlabel("視線ベクトルを単一回転(Kabsch)で重ねた残差の中央値(対数軸)", fontsize=12)
    ax.set_title("縮退ステレオペアの検定 ―― 視差の存在そのものを測ると 14 桁で分離する",
                 fontsize=15.5, pad=14)
    ax.text(deg * 2.2, y[0], f"{deg:.1e}", va="center", fontsize=16,
            fontweight="bold", color=FG)
    ax.text(ok * 2.2, y[1], f"{ok:.1e}", va="center", fontsize=16,
            fontweight="bold", color=FG)
    # 判定しきい値 (camera.recover_pose 実装の 1e-9)
    ax.axvline(1e-9, color=ORANGE, lw=1.4, ls=(0, (5, 3)), zorder=2)
    ax.text(1e-9, 1.86, "判定しきい値 1e-9\n(recover_pose 実装値)", ha="center",
            va="top", fontsize=11, color=ORANGE, linespacing=1.4,
            bbox=dict(facecolor=BG, edgecolor="none", pad=2.5))
    # マージンのブラケット
    yb = -0.45
    ax.annotate("", xy=(ok, yb), xytext=(deg, yb),
                arrowprops=dict(arrowstyle="<|-|>", color=GREEN, lw=1.6))
    ax.text(np.sqrt(deg * ok), yb - 0.02, f"約 {digits:.1f} 桁のマージン",
            ha="center", va="top", fontsize=14, fontweight="bold", color=GREEN)
    fig.text(0.5, -0.02,
             "本図の 2 値は camera.recover_pose の視差検定と同一の計算をこの場で再実測したもの"
             "(合成シーン: 8° 回転、並進 0.5)。記事本文の 3.5×10⁻¹⁶ / 1.8×10⁻² と同オーダー。",
             ha="center", fontsize=10.5, color=MUTED)
    fig.subplots_adjust(left=0.17, bottom=0.16, top=0.89)
    _save(fig, "fig_kabsch_margin")


# --------------------------------------------------------------------------- #
# fig 3: バグ④(曲率 32 倍)の修正後検証 — 合成球の curvedness vs 理論 1/R
# 数値の出所: (a) 実測 — curvature3d.curvedness を半径 R の Fibonacci 球
#   (2000 点, k=25) に対しその場で実行。理論線 1/R(球では k1=k2=1/R なので
#   curvedness C=√((k1²+k2²)/2)=1/R)。破線 1/(32R) は (b) 記事既載の
#   「修正前は絶対値だけが 1/32」という系統誤差の位置(参照線であり実測ではない)。
# --------------------------------------------------------------------------- #
def fig_bug4_curvature() -> None:
    import curvature3d

    def fib_sphere(n, R):
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = np.pi * (1 + 5 ** 0.5) * i
        return R * np.column_stack(
            [np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)])

    radii = np.array([0.5, 1.0, 2.0, 4.0, 8.0])
    med, q25, q75 = [], [], []
    for R in radii:
        cv = curvature3d.curvedness(fib_sphere(2000, R), k=25)
        med.append(float(np.median(cv)))
        q25.append(float(np.percentile(cv, 25)))
        q75.append(float(np.percentile(cv, 75)))
    med = np.array(med)
    ratio = float(np.mean(med * radii))
    print(f"    measured: median-curvedness x R = {ratio:.4f} (theory 1.0)")
    rr = np.geomspace(0.4, 10, 50)
    fig, ax = plt.subplots(figsize=(11.6, 7.6), facecolor=BG)
    _style_ax(ax)
    ax.plot(rr, 1 / rr, color=BLUE, lw=2.0, zorder=2, label="理論値 1/R(球の曲率)")
    ax.plot(rr, 1 / (32 * rr), color=MUTED, lw=1.6, ls=(0, (5, 4)), zorder=2,
            label="バグ④修正前の系統誤差 1/(32R)(記事記載)")
    ax.errorbar(radii, med, yerr=[med - np.array(q25), np.array(q75) - med],
                fmt="o", ms=9, color=ORANGE, ecolor=ORANGE, elinewidth=1.4,
                capsize=4, zorder=3, label="実測 curvedness 中央値(IQR 誤差棒)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("合成球の半径 R", fontsize=12.5)
    ax.set_ylabel("curvedness  C = √((k₁²+k₂²)/2)", fontsize=12.5)
    ax.set_title("バグ④の修正後検証 ―― 半径 R の球で曲率の絶対値が 1/R に乗る",
                 fontsize=15.5, pad=14)
    ax.grid(True, which="both", color=GRID, lw=0.6, zorder=0)
    leg = ax.legend(fontsize=11.5, facecolor=PANEL, edgecolor=GRID, labelcolor=FG,
                    loc="lower left")
    leg.get_frame().set_alpha(0.9)
    ax.annotate("修正前はこの線に乗っていた\n(比率は正しく、絶対値だけ 1/32)",
                xy=(5.0, 1 / (32 * 5.0)), xytext=(1.6, 3.4e-2),
                fontsize=11, color=MUTED, linespacing=1.45,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0))
    ax.text(0.985, 0.975,
            f"実測: 中央値 × R = {ratio:.3f}\n"
            "(+%.1f%% は k=25 近傍の二次曲面\nフィットによる離散化ぶん)" % ((ratio - 1) * 100),
            transform=ax.transAxes, ha="right", va="top", fontsize=11.5,
            color=FG, linespacing=1.5,
            bbox=dict(facecolor=PANEL, edgecolor=GRID, boxstyle="round,pad=0.5"))
    fig.text(0.5, 0.005,
             "実測: curvature3d.curvedness を Fibonacci 球 2000 点(k=25)へその場で実行。"
             "球では k₁=k₂=1/R なので C=1/R が厳密な理論値になる。",
             ha="center", fontsize=10.5, color=MUTED)
    fig.subplots_adjust(bottom=0.12, top=0.90)
    _save(fig, "fig_bug4_curvature")


# --------------------------------------------------------------------------- #
# fig 4: RAG コーパスの実物パネル + 「grep → 型を繋ぐ → 自己検証」3 ステップ
# 内容の出所: 左パネルは実在ファイル docs/ops/2d/smoothing/bilateral.md からの
#   引用のみ(実行時に読み込む。存在しなければ fail)。ステップ③の PASS 行は
#   (a) 実測 — examples/gallery2d_smoothing_rank.py をその場で subprocess 実行し、
#   実出力から PASS 行を捕捉して描く(PASS しなければ図の生成自体を fail)。
#   存在しない記述は作らない。
# --------------------------------------------------------------------------- #
def _run_worked_example() -> str:
    import subprocess
    p = subprocess.run([sys.executable, os.path.join(REPO, "examples",
                        "gallery2d_smoothing_rank.py")],
                       capture_output=True, text=True, cwd=REPO, timeout=600)
    for ln in reversed((p.stdout or "").splitlines()):
        if ln.startswith("PASS:"):
            return ln.strip()
    raise SystemExit("worked example did not PASS — refusing to fake the output:\n"
                     + (p.stdout or "")[-800:] + (p.stderr or "")[-800:])


def fig_rag_corpus() -> None:
    pass_line = _run_worked_example()
    print(f"    worked example output: {pass_line}")
    note_path = os.path.join(REPO, "docs", "ops", "2d", "smoothing", "bilateral.md")
    with open(note_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    # 引用する行(実ファイルの行のみ): frontmatter 全体 + 本文の要点行
    fm_end = lines.index("---", 1)
    front = lines[: fm_end + 1]
    picks = [ln for ln in lines[fm_end + 1:] if ln.startswith((
        "# bilateral", "- **データ種**", "- **呼び出し**", "- **HALCON 相当**"))]
    chain_hdr = "## 型が繋がる次の op(`image` を入力に取れる)"
    i = lines.index(chain_hdr)
    chain_line = lines[i + 2]
    ex_hdr = "## 実行できる例(この op を実際に呼ぶ検証済みサンプル)"
    j = lines.index(ex_hdr)
    ex_lines = [ln for ln in lines[j + 1: j + 5] if ln.startswith("- ")]
    prov_line = next(ln for ln in lines if ln.startswith("*Provenance:"))
    # 表示テキスト(md リンクは [name](path) → name に畳む。行の内容自体は原文)
    import re

    def flat(s):
        return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    fig = plt.figure(figsize=(14.6, 8.4), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    fig.text(0.03, 0.955, "RAG の中身は「grep できる Markdown」―― per-op ノート約1000枚の実物",
             fontsize=17, color=FG, fontweight="bold")
    fig.text(0.03, 0.915, "docs/ops/2d/smoothing/bilateral.md(実ファイルからの引用。ベクタ DB も埋め込みも不使用)",
             fontsize=11.5, color=MUTED)

    # ---- 左: ノート実物パネル
    panel = FancyBboxPatch((2.5, 6), 53, 80, boxstyle="round,pad=1.2",
                           facecolor=PANEL, edgecolor=GRID, lw=1.2)
    ax.add_patch(panel)
    ytxt = 83.0
    hi_keys = ("op:", "in:", "out:", "halcon:", "examples:", "author:", "license:", "version:")
    for ln in (front + [""] + picks + ["", chain_hdr, flat(chain_line), ""]
               + [ex_hdr] + [flat(x) for x in ex_lines] + ["", flat(prov_line)]):
        disp = flat(ln)
        if len(disp) > 62:
            disp = disp[:61] + "…"
        color = FG
        weight = "normal"
        if ln.strip().startswith(hi_keys):
            color = BLUE if ln.strip().startswith(("in:", "out:")) else ORANGE
            weight = "bold" if ln.strip().startswith(("in:", "out:")) else "normal"
        elif ln.startswith("#"):
            color = GREEN
            weight = "bold"
        elif ln == "---":
            color = MUTED
        ax.text(4.5, ytxt, disp, fontsize=9.6, color=color, family=MONO_JP,
                va="top", fontweight=weight)
        ytxt -= 3.35

    # ---- 右: 3 ステップ
    steps = [
        ("① 引く(grep)", BLUE,
         "$ grep -ri \"bilateral\" docs/ops\n→ docs/ops/2d/smoothing/bilateral.md\n\n"
         "ベクタ検索ではなく素の grep。\ngrep できる環境ならそのまま RAG になる"),
        ("② 型を繋ぐ", PURPLE,
         "in: image → out: image\n\n「型が繋がる次の op」リンクをたどり\n"
         "image → 領域 → 特徴量 と\n型が繋がる順にパイプラインを組む"),
        ("③ worked example で自己検証", GREEN,
         "$ py -3.11 examples/gallery2d_smoothing_rank.py\n\n" + pass_line + "\n\n"
         "AI 自身が PASS を確認してから答える\n(↑この環境で実行した実出力)"),
    ]
    ybox = 62.5
    for title, color, body in steps:
        box = FancyBboxPatch((60, ybox), 36.5, 22, boxstyle="round,pad=1.0",
                             facecolor=PANEL, edgecolor=color, lw=1.6)
        ax.add_patch(box)
        ax.text(62, ybox + 19.4, title, fontsize=13.5, color=color, fontweight="bold",
                va="top")
        ax.text(62, ybox + 14.6, body, fontsize=9.4, color=FG, family=MONO_JP,
                va="top", linespacing=1.55)
        if ybox > 15:
            ax.add_patch(FancyArrowPatch((78, ybox - 0.8), (78, ybox - 5.2),
                                         arrowstyle="-|>", mutation_scale=22,
                                         color=MUTED, lw=1.4))
        ybox -= 27.5
    _save(fig, "fig_rag_corpus")


# --------------------------------------------------------------------------- #
# fig 5: コアと optional extras の依存マップ
# 内容の出所: (a) 機械読取 — pyproject.toml の [project] dependencies と
#   [project.optional-dependencies] を tomllib でパースして描く。
#   グルーピング(見出し)のみ表示上の整理で、中身のパッケージ列は原文どおり。
# --------------------------------------------------------------------------- #
def fig_optional_extras() -> None:
    with open(os.path.join(REPO, "pyproject.toml"), "rb") as f:
        py = tomllib.load(f)
    core = py["project"]["dependencies"]
    extras = py["project"]["optional-dependencies"]
    groups = [  # 見出しは表示上の整理。extras 名と中身は pyproject 原文
        ("画像 I/O・処理", ["opencv", "skimage", "pil", "wavelets", "extra"], BLUE),
        ("GPU・3D ツールキット", ["gpu", "threed"], PURPLE),
        ("GUI・動画・音声", ["gui", "video", "audio"], GREEN),
        ("3D データ・点群 I/O", ["volume", "raster", "gltf", "lidar", "pcd"], ORANGE),
        ("産業 I/O", ["serial", "modbus", "mqtt", "opcua"], RED),
        ("開発・一括", ["dev", "all"], MUTED),
    ]
    covered = {n for _, ns, _ in groups for n in ns}
    missing = sorted(set(extras) - covered)
    if missing:  # pyproject に extras が増えたら図が黙って古びないように fail
        raise SystemExit(f"pyproject extras not in figure groups: {missing}")

    fig = plt.figure(figsize=(14.6, 9.0), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(-7, 100)
    fig.text(0.03, 0.955, "コアは numpy + scipy だけ ―― 重い依存はぜんぶ optional extras",
             fontsize=17, color=FG, fontweight="bold")
    fig.text(0.03, 0.915, "pyproject.toml の実定義から機械生成(fullseye v%s)。"
             "extras が無ければ該当 op だけが静かに無効化される(graceful degradation)"
             % py["project"]["version"], fontsize=11.5, color=MUTED)

    # 中央コア
    cx, cy = 21, 46
    corebox = FancyBboxPatch((cx - 13, cy - 10), 26, 20, boxstyle="round,pad=1.2",
                             facecolor="#16233a", edgecolor=BLUE, lw=2.2)
    ax.add_patch(corebox)
    ax.text(cx, cy + 5.5, "core", fontsize=16, color=BLUE, fontweight="bold",
            ha="center")
    ax.text(cx, cy - 0.5, "\n".join(core), fontsize=12, color=FG, family=MONO_JP,
            ha="center", va="center", linespacing=1.7)
    ax.text(cx, cy - 7.2, "(必須依存はこの2つだけ)", fontsize=10, color=MUTED,
            ha="center")

    # core → extras 全体への矢印(1 本。箱ごとの矢印は線が交差して読めないので廃止)
    ax.add_patch(FancyArrowPatch((cx + 14.5, cy), (40.2, cy),
                                 arrowstyle="-|>", mutation_scale=22,
                                 color=MUTED, lw=1.8))
    ax.text((cx + 14.5 + 40.2) / 2, cy + 2.2, "+ extras\n(opt-in)", ha="center",
            va="bottom", fontsize=11, color=MUTED, linespacing=1.4)

    # グループ箱を 2 列で(中身のパッケージ列は pyproject 原文どおり)
    def _lines_for(names):
        out = []
        for n in names:
            if n == "all":  # 一覧が長大なので件数のみ(len は pyproject から機械算出)
                out.append((f"[all]  = 一括 ({len(extras['all'])} packages)", True))
                continue
            out.append((f"[{n}]", True))
            for pkg in extras[n]:
                out.append(("   " + pkg, False))
        return out

    col_x = [42, 71.5]
    col_y = [88.5, 88.5]
    for gi, (gname, names, color) in enumerate(groups):
        col = gi % 2
        body = _lines_for(names)
        h = 4.6 + sum(2.2 if is_hdr else 2.9 for _, is_hdr in body)
        x0 = col_x[col]
        y0 = col_y[col] - h
        box = FancyBboxPatch((x0, y0), 26.5, h, boxstyle="round,pad=0.9",
                             facecolor=PANEL, edgecolor=color, lw=1.5)
        ax.add_patch(box)
        ax.text(x0 + 1.6, y0 + h - 0.9, gname, fontsize=12.5, color=color,
                fontweight="bold", va="top")
        yy = y0 + h - 4.6
        for txt, is_hdr in body:
            ax.text(x0 + 1.6, yy, txt, fontsize=10.3 if is_hdr else 9.2,
                    color=color if is_hdr else FG, family=MONO_JP, va="top")
            yy -= 2.2 if is_hdr else 2.9
        col_y[col] = y0 - 3.0
    ax.text(50, -4.5,
            "pip install fullseye = core のみ / pip install \"fullseye[opencv,gui]\" のように"
            "必要な extras だけを選んで追加する",
            ha="center", va="center", fontsize=10.5, color=MUTED)
    _save(fig, "fig_optional_extras")


# --------------------------------------------------------------------------- #
FIGS = {
    "ci": fig_ci_waterfall,
    "kabsch": fig_kabsch_margin,
    "curvature": fig_bug4_curvature,
    "rag": fig_rag_corpus,
    "extras": fig_optional_extras,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--figs", default="ci,kabsch,curvature,rag,extras",
                    help="comma-separated subset of: " + ",".join(FIGS))
    args = ap.parse_args()
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for name in args.figs.split(","):
        name = name.strip()
        if name not in FIGS:
            raise SystemExit(f"unknown fig: {name} (choose from {list(FIGS)})")
        print(f"[gen] {name}")
        FIGS[name]()


if __name__ == "__main__":
    main()
