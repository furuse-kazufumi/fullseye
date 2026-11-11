# -*- coding: utf-8 -*-
"""Qiita 記事「GPU に載せれば速い」は op ごとに違う、の図。

**測定は回さない。** 数字は全部、コミット済みの実測ログと生成物から読む:

* ``docs/perf/logs/crossover/cpu_*.jsonl`` / ``gpu.jsonl``      -- 単独 op の格子(図 1)
* ``docs/perf/logs/crossover/gpipe.jsonl`` / ``pipe_cpu.jsonl`` -- パイプラインの内訳(図 2、GIF)
* ``docs/perf/logs/crossover/before_after*.jsonl``             -- 規則の before / after(図 3)
* ``docs/perf/pipeline_routes.json``                           -- レシピ 220 本の経路(図 4)

読み方は ``tools/gen_device_rules.py`` と同じ(``status == "ok"`` の行だけ、同じ鍵は後の行が勝つ)。
記事の本文に書いた数字は ``check_numbers`` で門にしてあり、ログと食い違えば図を書かずに落ちる。

出力: ``docs/articles/assets/gpu_auto/``

* ``gpu_route_coverage.png``   -- 全 op のうち GPU 経路を持つ割合と内訳(gpu_route.routes で数える)
* ``gpu_crossover_by_op.png``  -- threshold / median / gaussian / gamma の CPU÷GPU を一辺 64〜4096 で
* ``gpu_round_trips.gif``      -- 全段 GPU の鎖と、途中に CPU 段が 1 つ挟まる鎖を時間に比例して流す
  (``gpu_round_trips_last.png`` = その最後の絵)
* ``gpu_rule_before_after.png`` -- 1 回目の決め方(14 点が遅い)と 2 回目(0 点)
* ``gpu_recipe_routes.png``    -- レシピ 220 本・578 段の on=gpu/cpu と CPU に残る理由

使い方: ``py -3.11 tools/gen_gpu_article_figures.py``(再実行で同じ図。PNG/GIF のバイトはフォントと
Pillow の版で変わるので regen_all の ``--check`` には入れない)。
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "docs" / "perf" / "logs" / "crossover"
ROUTES = ROOT / "docs" / "perf" / "pipeline_routes.json"
OUT = ROOT / "docs" / "articles" / "assets" / "gpu_auto"

#: 揺れの幅(tools/gen_device_rules.py と同じ値。検査は cpu_not_worse と同じ式)
TOLERANCE = 0.10
FLOOR_S = 50e-6

#: 1 回目の before / after(決め方を直す前)は 2026-11-03 の 12 時台に測った 568 点。
#: 同じファイルの 22 時台の 104 行は、規則を直した後に領域の解析の族を足して測った行なので、
#: 「直す前の決め方」の図には入れない(2 回目のファイルにも同じ族の別の測定が入っている)。
RUN1_UNTIL = "2026-11-03T13:00"

# ---- 色(dataviz の既定パレット、light。categorical の先頭 3 色は all-pairs で検証済み) ---- #
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
BLUE = "#2a78d6"     # GPU
ORANGE = "#eb6834"   # CPU
AQUA = "#1baf7a"     # 転送 / その他
VIOLET = "#6250d6"   # native(規模の図だけ。隣は AQUA と灰色で、BLUE とは隣り合わない)
TINT_GPU = "#e3eefb"
TINT_CPU = "#fbe7dd"
TINT_TIE = "#efeeea"

FAMILIES = ("Yu Gothic", "Meiryo", "Noto Sans JP", "BIZ UDGothic")


# ----------------------------------------------------------------------------- ログ
def read_logs(pattern: str) -> list:
    """``tools/gen_device_rules.read_logs`` と同じ読み方(ファイル名順、空行は飛ばす)。"""
    rows = []
    for path in sorted(LOGS.glob(pattern)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"ログが無い: {pattern}")
    return rows


def grid_points() -> tuple[dict, dict]:
    """単独 op の格子 ``{(op, side, n): row}``(CPU, GPU)。状態 ok 以外も持つ(欠測を書くため)。"""
    cpu = {(r["op"], r["side"], r["n"]): r for r in read_logs("cpu_*.jsonl") if "side" in r}
    gpu = {(r["op"], r["side"], r["n"]): r for r in read_logs("gpu.jsonl") if "side" in r}
    return cpu, gpu


def speedup(cpu: dict, gpu: dict, op: str, side: int, n: int):
    c, g = cpu.get((op, side, n)), gpu.get((op, side, n))
    if not c or not g or c.get("status") != "ok" or g.get("status") != "ok":
        return None
    return c["wall_s"] / g["wall_s"]


def pipe_row(name: str, variant: str, side: int = 2048, n: int = 1) -> tuple[dict, float]:
    g = [r for r in read_logs("gpipe.jsonl") if (r["pipeline"], r["variant"], r["side"], r["n"]) ==
         (name, variant, side, n) and r.get("status") == "ok"]
    c = [r for r in read_logs("pipe_cpu.jsonl") if (r["pipeline"], r["variant"], r["side"], r["n"]) ==
         (name, variant, side, n) and r.get("status") == "ok"]
    if not g or not c:
        raise SystemExit(f"鎖の点が無い: {name} {variant} {side} {n}")
    return g[-1], c[-1]["wall_s"]


def slower(r: dict) -> bool:
    """after(CPU)が before(GPU)より揺れの幅を超えて遅い = ``not cpu_not_worse``。"""
    return not (r["after_s"] <= r["before_s"] * (1 + TOLERANCE) or r["after_s"] - r["before_s"] <= FLOOR_S)


def before_after() -> tuple[list, list]:
    run1 = [r for r in read_logs("before_after.jsonl") if r["kind"] == "op" and r["at"] < RUN1_UNTIL]
    run2 = [r for r in read_logs("before_after_2.jsonl") if r["kind"] == "op"]
    return run1, run2


def recipes() -> tuple[list, dict]:
    d = json.loads(ROUTES.read_text(encoding="utf-8"))
    rs = [r for r in d["recipes"] if len(r["stages"]) >= 2]
    return rs, d["summary"]


# ----------------------------------------------------------------------------- 門
def _near(value: float, want: float, digits: int) -> bool:
    return round(value, digits) == round(want, digits)


def check_numbers() -> dict:
    """記事の本文の数字をログから計算し直して照合する。食い違えば落ちる(図を書く前に)。"""
    cpu, gpu = grid_points()
    ms = {k: cpu[k]["wall_s"] * 1e3 for k in [("threshold", 4096, 1), ("median", 4096, 1)]}
    gms = {k: gpu[k]["wall_s"] * 1e3 for k in [("threshold", 4096, 1), ("median", 4096, 1)]}
    problems = []
    for key, want_c, want_g in [(("threshold", 4096, 1), 138.52, 186.56), (("median", 4096, 1), 8564, 192.10)]:
        if not (_near(ms[key], want_c, 0) and _near(gms[key], want_g, 1)):
            problems.append(f"{key}: ログ {ms[key]:.2f} / {gms[key]:.2f} ms、記事 {want_c} / {want_g}")
    # 記事の表の言い分(勝ち始める寸法)をそのまま門にする
    def first_gpu(op, n):
        for s in (64, 128, 256, 512, 1024, 2048, 4096):
            v = speedup(cpu, gpu, op, s, n)
            # GPU の勝ち = 揺れの幅(10 %)かつ 50 µs を超えて速い(報告の表と同じ言い方)
            if v is not None and v >= 1 + TOLERANCE and                     cpu[(op, s, n)]["wall_s"] - gpu[(op, s, n)]["wall_s"] > FLOOR_S:
                return s
        return None
    claims = {("threshold", 1): None, ("threshold", 16): None, ("median", 1): 64, ("median", 16): 64,
              ("gaussian", 1): 512, ("gaussian", 16): 64, ("gamma", 1): 256, ("gamma", 16): 64}
    for (op, n), want in claims.items():
        got = first_gpu(op, n)
        if got != want:
            problems.append(f"{op} {n} 枚: GPU が勝ち始める一辺 ログ {got}、記事 {want}")
    if speedup(cpu, gpu, "gamma", 1024, 16) >= 1 + TOLERANCE:
        problems.append("gamma 16 枚の一辺 1024 が GPU の勝ちになっている(記事は「1024 で再び CPU」)")

    pa, ca = pipe_row("scratch_surface", "all")
    pm, cm = pipe_row("scratch_surface", "mixed")
    ra, rm = ca / pa["wall_s"], cm / pm["wall_s"]
    if not (_near(ra, 13.3, 1) and _near(rm, 1.3, 1)):
        problems.append(f"scratch_surface 倍率 ログ {ra:.2f} / {rm:.2f}、記事 13.3 / 1.3")
    if (pa["up_n"], pa["down_n"], pm["up_n"], pm["down_n"]) != (1, 1, 2, 2):
        problems.append(f"往復の回数 ログ all {pa['up_n']} / mixed {pm['up_n']}、記事 1 / 2")
    if not _near(pa["wall_s"] * 1e3, 64.81, 2) or not _near(pm["wall_s"] * 1e3, 690.96, 2):
        problems.append("scratch_surface の GPU 計がずれた")

    run1, run2 = before_after()
    n1, n2 = sum(map(slower, run1)), sum(map(slower, run2))
    if (n1, n2) != (14, 0):
        problems.append(f"遅くなった点 ログ {n1} / {n2}、記事 14 / 0")
    if len(run2) != 578 or not _near(sum(r["before_s"] for r in run2), 4.363, 3) \
            or not _near(sum(r["after_s"] for r in run2), 0.900, 3):
        problems.append("2 回目の点数・合計が記事(578 点、4.363 s → 0.900 s)と違う")

    rs, summary = recipes()
    a = summary["after"]
    reasons = {}
    for r in rs:
        for s in r["after"]["stages"]:
            if s["on"] == "cpu":
                reasons[s["reason"]] = reasons.get(s["reason"], 0) + 1
    zero = sum(1 for r in rs if r["after"]["n_gpu_stages"] == 0)
    if (len(rs), a["stages"], a["gpu_stages"], a["all_gpu_recipes"], a["transfers"], zero) != \
            (220, 578, 199, 33, 126, 115):
        problems.append(f"レシピの集計が記事と違う: {len(rs)} {a} 0 段 {zero}")
    if reasons != {"not_listed": 344, "below_measured_size": 25, "chain_only": 10}:
        problems.append(f"CPU に残る理由が記事と違う: {reasons}")
    if problems:
        raise SystemExit("記事の数字とログが食い違う:\n  " + "\n  ".join(problems))
    return {"ratio_all": ra, "ratio_mixed": rm, "slow1": n1, "slow2": n2, "n1": len(run1), "n2": len(run2)}


# ----------------------------------------------------------------------------- 描画の下ごしらえ
def _family() -> str:
    from matplotlib import font_manager as fm
    names = {f.name for f in fm.fontManager.ttflist}
    for fam in FAMILIES:
        if fam in names:
            return fam
    raise SystemExit("日本語フォントが見つからない(" + " / ".join(FAMILIES) + ")")


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": _family(), "font.size": 13, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.spines.top": False,
        "axes.spines.right": False, "axes.unicode_minus": False,
    })
    return plt


def _save(fig, name: str) -> Path:
    path = OUT / name
    with warnings.catch_warnings():
        # 字形の無い文字(豆腐)の警告だけを失敗にする(他の依存の非推奨警告は混ぜない)
        warnings.filterwarnings("error", message=r".*(Glyph|missing from).*")
        fig.savefig(path, dpi=100)
    import matplotlib.pyplot as plt
    plt.close(fig)
    _check_image(path)
    return path


def _check_image(path: Path) -> None:
    """空・一色の絵を弾く(書けた ≠ 意味のある絵)。"""
    from PIL import Image
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGB"), dtype=np.float64)
    if a.size == 0 or float(np.ptp(a)) < 100 or float(a.std()) < 5:
        raise SystemExit(f"{path.name}: 絵が空か一色(ptp {np.ptp(a):.0f}, std {a.std():.1f})")


SIDES = (64, 128, 256, 512, 1024, 2048, 4096)


# ----------------------------------------------------------------------------- 図 1
def fig_crossover() -> Path:
    plt = _mpl()
    from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator
    cpu, gpu = grid_points()
    panels = [("threshold", "4096 でも CPU が速い"), ("median", "64 から GPU"),
              ("gaussian", "1 枚は 512 から GPU"), ("gamma", "勝ち負けが行ったり来たり")]
    fig, axes = plt.subplots(1, 4, figsize=(12, 5.4), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.80, bottom=0.19, wspace=0.08)
    hi = 1 + TOLERANCE
    for k, (ax, (op, sub)) in enumerate(zip(axes, panels)):
        ax.axhspan(hi, 200, color=TINT_GPU, zorder=0, lw=0)
        ax.axhspan(0.05, 1 / hi, color=TINT_CPU, zorder=0, lw=0)
        ax.axhspan(1 / hi, hi, color=TINT_TIE, zorder=0, lw=0)
        ax.axhline(1, color=MUTED, lw=1, zorder=1)
        for n, color, ls, mk in ((1, INK, "-", "o"), (16, INK2, (0, (4, 2)), "s")):
            xs = [s for s in SIDES if speedup(cpu, gpu, op, s, n) is not None]
            ys = [speedup(cpu, gpu, op, s, n) for s in xs]
            ax.plot(xs, ys, color=color, ls=ls, lw=2, marker=mk, ms=7, mec=SURFACE, mew=1.5, zorder=3,
                    label=f"{n} 枚")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_ylim(0.1, 100)
        ax.set_xlim(48, 5500)
        ax.xaxis.set_major_locator(FixedLocator([64, 256, 1024, 4096]))
        ax.xaxis.set_minor_locator(FixedLocator([128, 512, 2048]))
        ax.set_xticklabels(["64", "256", "1024", "4096"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(FixedLocator([0.1, 0.3, 1, 3, 10, 30, 100]))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_yticklabels(["0.1", "0.3", "1", "3", "10", "30", "100"])
        ax.grid(True, which="major", axis="y", color=GRID, lw=0.8, zorder=0)
        ax.set_title(f"{op}\n", fontsize=17, fontweight="bold", loc="left", pad=2)
        ax.text(0.0, 1.02, sub, transform=ax.transAxes, fontsize=13, color=INK2, va="bottom")
        ax.set_xlabel("画像の一辺(画素)")
        if k == 0:
            ax.set_ylabel("GPU の速さ = CPU 時間 ÷ GPU 時間(倍)")
        if k == 1:
            ax.text(56, 0.14, "CPU が速い", color="#b4461b", fontsize=13, fontweight="bold", va="center")
        if k == 2:
            ax.text(56, 60, "GPU が速い", color=BLUE, fontsize=13, fontweight="bold", va="center")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=2, frameon=False, fontsize=13,
               bbox_to_anchor=(0.985, 0.995))
    fig.text(0.075, 0.955, "GPU が勝ち始める大きさは op ごとに違う", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.075, 0.012, "転送込み・常駐後の中央値(RTX 5090 / 24 論理コア)。灰色の帯は揺れの幅 ±10 %(差が 50 µs 未満の点も引き分け)。\n"
             "median 16 枚の一辺 4096 は欠測(CPU 打ち切り)。出典 docs/perf/logs/crossover/",
             fontsize=11, color=INK2)
    return _save(fig, "gpu_crossover_by_op.png")


# ----------------------------------------------------------------------------- 図 3
def fig_before_after() -> Path:
    plt = _mpl()
    from matplotlib.ticker import FixedLocator, NullLocator
    run1, run2 = before_after()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), sharey=True)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.80, bottom=0.19, wspace=0.07)
    titles = [("1 回目: 引き分けも CPU に倒した", run1), ("2 回目: はっきり負けた点だけ CPU", run2)]
    for ax, (title, rows) in zip(axes, titles):
        bad = [r for r in rows if slower(r)]
        ok = [r for r in rows if not slower(r)]
        ax.axhspan(1 + TOLERANCE, 3, color=TINT_CPU, lw=0, zorder=0)
        ax.axhline(1, color=MUTED, lw=1, zorder=1)
        ax.axhline(1 + TOLERANCE, color=INK2, lw=1.2, ls=(0, (4, 2)), zorder=1)
        ax.scatter([r["before_s"] * 1e3 for r in ok], [r["after_s"] / r["before_s"] for r in ok],
                   s=16, color=MUTED, alpha=0.55, lw=0, zorder=2, label="遅くならなかった点")
        ax.scatter([r["before_s"] * 1e3 for r in bad], [r["after_s"] / r["before_s"] for r in bad],
                   s=70, color=ORANGE, edgecolor=SURFACE, lw=1.5, zorder=3, label="揺れを超えて遅くなった点")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(0.01, 3)
        ax.set_xlim(0.1, 600)
        ax.yaxis.set_major_locator(FixedLocator([0.01, 0.03, 0.1, 0.3, 1, 3]))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_yticklabels(["0.01", "0.03", "0.1", "0.3", "1", "3"])
        ax.xaxis.set_major_locator(FixedLocator([0.1, 1, 10, 100]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xticklabels(["0.1", "1", "10", "100"])
        ax.grid(True, axis="y", color=GRID, lw=0.8, zorder=0)
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left", pad=26)
        tb = sum(r["before_s"] for r in rows)
        ta = sum(r["after_s"] for r in rows)
        ax.text(0.0, 1.015, f"{len(rows)} 点・合計 {tb:.2f} s → {ta:.2f} s", transform=ax.transAxes,
                fontsize=12.5, color=INK2, va="bottom")
        ax.text(0.97, 0.93, f"遅くなった点 {len(bad)}", transform=ax.transAxes, ha="right", va="top",
                fontsize=19, fontweight="bold", color="#b4461b" if bad else INK)
        ax.text(0.13, 1.25, "揺れの幅 +10 %", fontsize=11, color=INK2, va="bottom")
        ax.set_xlabel("before(CUDA があれば常に GPU)の時間 ms")
    axes[0].set_ylabel("after ÷ before(1 未満 = CPU に回して速くなった)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper right", ncol=2, frameon=False, fontsize=12.5, bbox_to_anchor=(0.985, 0.995))
    fig.text(0.085, 0.955, "決め方を直すと、遅くなる点が 14 → 0", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.085, 0.012, "after = device=\"auto\"(規則が CPU に回した点だけを測る)。遅い = 10 % かつ 50 µs を超えて遅い。\n"
             "1 回目は 2026-11-03 の 568 点、2 回目は材料に使っていない測定。出典 docs/perf/logs/crossover/before_after*.jsonl",
             fontsize=11, color=INK2)
    return _save(fig, "gpu_rule_before_after.png")


# ----------------------------------------------------------------------------- 図 4
def fig_recipe_routes() -> Path:
    plt = _mpl()
    from matplotlib.patches import Rectangle
    rs, _ = recipes()
    color_of = {None: BLUE, "not_listed": ORANGE, "below_measured_size": AQUA, "chain_only": AQUA}
    groups = {}
    for r in rs:
        groups.setdefault(r["after"]["n_transfers"], []).append(r)
    order = sorted(groups)
    fig = plt.figure(figsize=(12, 5.2))
    ax = fig.add_axes([0.02, 0.17, 0.96, 0.58])
    cw, gap_group, max_st = 1.0, 24.0, max(len(r["stages"]) for r in rs)
    x = 0.0
    for t in order:
        rows = sorted(groups[t], key=lambda r: (-r["after"]["n_gpu_stages"] / len(r["stages"]),
                                                -len(r["stages"]), r["recipe"]))
        x0 = x
        for r in rows:
            for i, s in enumerate(r["after"]["stages"]):
                ax.add_patch(Rectangle((x + 0.08, max_st - i - 1 + 0.06), cw - 0.16, 0.88,
                                       color=color_of[s["reason"] if s["on"] == "cpu" else None], lw=0))
            x += cw
        ax.text(x0, max_st + 1.15, f"往復 {t} 回", fontsize=15, fontweight="bold", color=INK, va="bottom")
        ax.text(x0, max_st + 0.25, f"{len(rows)} 本", fontsize=12.5, color=INK2, va="bottom")
        x += gap_group
    ax.set_xlim(-0.5, x - gap_group + 22)
    ax.set_ylim(-0.1, max_st + 2.3)
    ax.axis("off")
    ax.text(-0.5, -0.45, "1 列 = 1 本のレシピ。上から 1 段目、2 段目 …", fontsize=11.5, color=INK2, va="top")
    a = {}
    for r in rs:
        for s in r["after"]["stages"]:
            key = "gpu" if s["on"] == "gpu" else ("not_listed" if s["reason"] == "not_listed" else "other")
            a[key] = a.get(key, 0) + 1
    other = {}
    for r in rs:
        for s in r["after"]["stages"]:
            if s["on"] == "cpu" and s["reason"] != "not_listed":
                other[s["reason"]] = other.get(s["reason"], 0) + 1
    legend = [(BLUE, f"GPU {a['gpu']} 段"), (ORANGE, f"CPU: GPU 経路が無い(not_listed){a['not_listed']} 段"),
              (AQUA, f"CPU: その他の理由 {a['other']} 段(below_measured_size {other['below_measured_size']}・"
                     f"chain_only {other['chain_only']})")]
    lx = 0.02
    for c, label in legend:
        fig.patches.append(Rectangle((lx, 0.035), 0.014, 0.035, color=c, transform=fig.transFigure, figure=fig))
        t = fig.text(lx + 0.02, 0.052, label, fontsize=12.5, color=INK, va="center")
        fig.canvas.draw()
        bb = t.get_window_extent().transformed(fig.transFigure.inverted())
        lx = bb.x1 + 0.025
    fig.text(0.02, 0.93, "レシピ 220 本・578 段を explain_pipeline に通すと、半分は GPU の段が 0", fontsize=20,
             fontweight="bold", color=INK)
    fig.text(0.02, 0.865, "一辺 2048・device=\"auto\"・assume_cuda=True。往復の見込みの合計 126 回。"
             "出典 docs/perf/pipeline_routes.json", fontsize=12.5, color=INK2)
    return _save(fig, "gpu_recipe_routes.png")


# ----------------------------------------------------------------------------- 図 0(規模)
#: 2026-11-02 の損益分岐の報告(docs/perf/gpu_crossover_2026-11-02.md の「要点」)時点の手書き経路の数
ACCEL_2026_11_02 = 90


def route_counts() -> dict:
    """``docs/OP_INDEX.json`` の全 op に ``gpu_route.routes`` を当てて数える(GPU は使わない)。

    手書き経路(accel)は ``accel_bridge`` の表から来るので torch が import できる環境で数える
    (torch が無いと accel の経路ごと消え、数が変わる —— 記事の CI の節と同じ理由)。
    """
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        raise SystemExit("torch が import できない環境では accel の経路が数えられない") from exc
    sys.path.insert(0, str(ROOT))
    import gpu_route
    idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    names = [o["name"] for o in idx["ops"]]
    if len(names) != idx["n_ops"] or len(set(names)) != len(names):
        raise SystemExit("OP_INDEX.json の op 名が n_ops と合わないか重複がある")
    kinds = {k: 0 for k in ("accel", "native", "shadow")}
    uses: dict = {}
    excl = {"accel": 0, "native": 0, "shadow_only": 0}
    accel_and_shadow = native_and_shadow = 0
    any_route = 0
    for n in names:
        rs = gpu_route.routes(n)
        ks = {r.kind for r in rs}
        if not ks:
            continue
        any_route += 1
        for k in ks:
            kinds[k] += 1
        for r in rs:
            uses[(r.kind, r.use)] = uses.get((r.kind, r.use), 0) + 1
        if "accel" in ks:
            excl["accel"] += 1
            accel_and_shadow += "shadow" in ks
        elif "native" in ks:
            excl["native"] += 1
            native_and_shadow += "shadow" in ks
        else:
            excl["shadow_only"] += 1
    if excl["accel"] + excl["native"] + excl["shadow_only"] != any_route:
        raise SystemExit("排他の内訳の合計が経路を持つ op の数と合わない")
    rules = json.loads((ROOT / "fullseye" / "data" / "DEVICE_RULES.json").read_text(encoding="utf-8"))
    return {"n_ops": len(names), "any": any_route, "kinds": kinds, "uses": uses, "excl": excl,
            "accel_and_shadow": accel_and_shadow, "native_and_shadow": native_and_shadow,
            "min_ratio": rules["shadow"]["min_ratio"], "n_shadow_rules": len(rules["shadow"]["ops"])}


def fig_coverage(c: dict) -> Path:
    plt = _mpl()
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(12, 5.0))
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.66])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    N, A = c["n_ops"], c["any"]
    # 上の帯: 全 op のうち GPU 経路のある割合
    y1, h = 0.70, 0.17
    ax.add_patch(Rectangle((0, y1), A / N, h, color=BLUE, lw=0))
    ax.add_patch(Rectangle((A / N + 0.002, y1), 1 - A / N - 0.002, h, color="#dddcd7", lw=0))
    ax.text(0.008, y1 + h / 2, f"GPU 経路あり {A:,}", color=SURFACE, fontsize=15, fontweight="bold", va="center")
    ax.text(0.992, y1 + h / 2, f"GPU 経路なし {N - A:,}(CPU だけで走る)", color=INK, fontsize=15,
            ha="right", va="center")
    ax.text(0, y1 + h + 0.03, f"全 {N:,} op", fontsize=13, color=INK2, va="bottom")
    # 下の帯: 経路のある op の内訳(排他。優先順 accel > native > shadow)
    y2 = 0.20
    e = c["excl"]
    parts = [(BLUE, e["accel"], "手書き(torch)", f"{e['accel']}"),
             (AQUA, e["shadow_only"], "許可リスト(CuPy)だけ", f"{e['shadow_only']}"),
             (VIOLET, e["native"], "native", f"{e['native']}")]
    x = 0.0
    for col, n, label, num in parts:
        w = n / A
        ax.add_patch(Rectangle((x, y2), w - 0.003, h, color=col, lw=0))
        if w > 0.12:
            ax.text(x + 0.008, y2 + h / 2, f"{label} {num}", color=SURFACE if col != AQUA else INK,
                    fontsize=15, fontweight="bold", va="center")
        else:
            ax.text(x + w, y2 - 0.04, f"{label} {num}", color=INK, fontsize=13, ha="right", va="top")
        x += w
    # 2 本の帯をつなぐ台形(上の 767 を下で広げた)
    ax.fill([0, A / N, 1, 0], [y1, y1, y2 + h, y2 + h], color="#e3eefb", lw=0, zorder=0)
    ax.text(0, y2 - 0.04, f"手書き {c['kinds']['accel']} のうち {c['accel_and_shadow']} は許可リストにも在る",
            fontsize=12, color=INK2, va="top")
    fig.text(0.02, 0.92, f"{N:,} op のうち {A:,}({A / N:.0%})に GPU 経路がある", fontsize=21,
             fontweight="bold", color=INK)
    k = c["kinds"]
    fig.text(0.02, 0.855, f"種類別(重なりあり): 許可リスト {k['shadow']} / 手書き {k['accel']}"
             f"(11/02 時点 {ACCEL_2026_11_02})/ native {k['native']}。数え方 gpu_route.routes(name)", fontsize=13,
             color=INK2)
    fig.text(0.02, 0.015, "許可リスト = 掃引で CPU と一致し、単独で 5 倍以上 / 常駐で 5 倍以上 / 常駐で 1〜5 倍と測れた op。\n"
             "経路があっても、device=\"auto\" は大きさを見て CPU に残すことがある", fontsize=11.5, color=INK2)
    return _save(fig, "gpu_route_coverage.png")


# ----------------------------------------------------------------------------- 図 2(GIF)
class _Fonts:
    """Pillow の字形と、豆腐の検査(描いた全文字が cmap に在るか)。"""

    def __init__(self):
        from matplotlib import font_manager as fm
        from fontTools.ttLib import TTCollection, TTFont
        fam = _family()
        self.paths = {w: fm.findfont(fm.FontProperties(family=fam, weight=w), fallback_to_default=False)
                      for w in ("regular", "bold")}
        self.cmaps = {}
        for w, p in self.paths.items():
            f = TTCollection(p).fonts[0] if p.lower().endswith(".ttc") else TTFont(p)
            self.cmaps[w] = set(f.getBestCmap())
        self.cache = {}
        self.missing = set()

    def get(self, size: int, bold: bool = False):
        from PIL import ImageFont
        key = (size, bold)
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(self.paths["bold" if bold else "regular"], size)
        return self.cache[key]

    def note(self, s: str, bold: bool) -> None:
        cm = self.cmaps["bold" if bold else "regular"]
        self.missing |= {ch for ch in s if not ch.isspace() and ord(ch) not in cm}


def _lane_phases(row: dict, chain: list, cpu_ops: set) -> list:
    """鎖を時間の区間に分ける: [(kind, label, ms)]。kind = up / down / gpu / cpu。

    ログが持つのは種類ごとの合計(往路の合計、復路の合計、kernel の合計、CPU 段の合計)なので、
    区間ごとの値は合計を回数で等分した概算(kernel は GPU 段の数で等分)。合計は実測のまま。
    """
    n_gpu = sum(1 for op in chain if op not in cpu_ops)
    up = row["up_s"] * 1e3 / row["up_n"]
    down = row["down_s"] * 1e3 / row["down_n"]
    kern = row["kernel_s"] * 1e3 / n_gpu
    cpu_each = row["cpu_s"] * 1e3 / max(1, row["cpu_n"])
    phases, on_gpu = [], False
    for op in chain:
        if op in cpu_ops:
            if on_gpu:
                phases.append(("down", "戻す", down))
                on_gpu = False
            phases.append(("cpu", op, cpu_each))
        else:
            if not on_gpu:
                phases.append(("up", "送る", up))
                on_gpu = True
            phases.append(("gpu", op, kern))
    if on_gpu:
        phases.append(("down", "戻す", down))
    return phases


def fig_round_trips(nums: dict) -> Path:
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(ROOT / "tools"))
    import bench_gpu_crossover as B                              # PIPELINES(鎖の段の並び)だけを読む
    chains = {v: [op for op, _a, _b in B.PIPELINES["scratch_surface"][v]] for v in ("all", "mixed")}
    cpu_ops = {"clahe"}                                         # 記事: 挟んだ GPU 経路の無い段
    if set(chains["mixed"]) - set(chains["all"]) != cpu_ops:
        raise SystemExit(f"mixed の差分が clahe でない: {chains}")
    ra, ca = pipe_row("scratch_surface", "all")
    rm, cm = pipe_row("scratch_surface", "mixed")
    lanes = [
        ("全段 GPU", _lane_phases(ra, chains["all"], cpu_ops), ca * 1e3, ra, nums["ratio_all"]),
        ("CPU 段が 1 つ挟まる", _lane_phases(rm, chains["mixed"], cpu_ops), cm * 1e3, rm, nums["ratio_mixed"]),
    ]
    for _name, ph, _c, row, _r in lanes:
        if abs(sum(p[2] for p in ph) - row["wall_s"] * 1e3) > 0.05:
            raise SystemExit("区間の合計が実測の計と合わない")

    W, H = 960, 540
    F = _Fonts()
    kind_color = {"up": AQUA, "down": AQUA, "gpu": BLUE, "cpu": ORANGE}
    short = {"gaussian": "gaussian", "tophat": "tophat", "threshold": "threshold", "erosion_circle": "erosion",
             "dilation_circle": "dilation", "clahe": "clahe"}
    t_max = 900.0                                    # バーの目盛の上限 ms(CPU だけの 868 ms が入る)
    bar_x0, bar_x1 = 40, 920
    anim_s = 7.0                                     # 690.96 ms の鎖を 7 秒で流す(両方の鎖で同じ倍率)
    slow = anim_s * 1e3 / (rm["wall_s"] * 1e3)       # 実時間 1 ms あたりの動画の ms
    fps = 20
    n_frames = int(anim_s * fps) + 2

    def txt(d, xy, s, size, bold=False, fill=INK, anchor="la"):
        F.note(s, bold)
        d.text(xy, s, font=F.get(size, bold), fill=fill, anchor=anchor)

    def frame(t_ms_real: float):
        im = Image.new("RGB", (W, H), SURFACE)
        d = ImageDraw.Draw(im)
        txt(d, (40, 22), "途中に CPU 段が 1 つ入ると、往復が増えて遅くなる", 30, True)
        for li, (name, phases, cpu_ms, row, ratio) in enumerate(lanes):
            y0 = 92 + li * 205
            n_trip = row["up_n"]
            txt(d, (40, y0), f"{name}(往復 {n_trip} 回)", 22, True)
            # 段の箱
            widths = [46 if k in ("up", "down") else 104 for k, _l, _m in phases]
            gap = 6
            total_w = sum(widths) + gap * (len(widths) - 1)
            x = bar_x0
            scale_box = min(1.0, (bar_x1 - bar_x0) / total_w)
            elapsed, acc = min(t_ms_real, sum(p[2] for p in phases)), 0.0
            for (kind, label, dur), w in zip(phases, widths):
                w = int(w * scale_box)
                state = "done" if elapsed >= acc + dur else ("now" if elapsed >= acc else "todo")
                col = kind_color[kind]
                box = (x, y0 + 40, x + w, y0 + 92)
                if state == "todo":
                    d.rounded_rectangle(box, 6, fill=SURFACE, outline=MUTED, width=2)
                    fg = INK2
                elif state == "now":
                    d.rounded_rectangle((box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3), 8, fill=col,
                                        outline=INK, width=3)
                    fg = SURFACE
                else:
                    d.rounded_rectangle(box, 6, fill=col)
                    fg = SURFACE
                lab = short.get(label, label)
                txt(d, ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), lab, 17 if kind in ("gpu", "cpu") else 16,
                    True, fg, "mm")
                acc += dur
                x += w + gap
            # 時間のバー
            by0, by1 = y0 + 112, y0 + 146
            d.rectangle((bar_x0, by0, bar_x1, by1), fill="#f3f2ee")
            acc = 0.0
            for kind, _label, dur in phases:
                seg0, seg1 = acc, min(acc + dur, elapsed)
                if seg1 > seg0:
                    xa = bar_x0 + (bar_x1 - bar_x0) * seg0 / t_max
                    xb = bar_x0 + (bar_x1 - bar_x0) * seg1 / t_max
                    d.rectangle((xa, by0, max(xa + 1, xb - 1), by1), fill=kind_color[kind])
                acc += dur
            xr = bar_x0 + (bar_x1 - bar_x0) * cpu_ms / t_max
            d.line((xr, by0 - 8, xr, by1 + 8), fill=INK, width=3)
            txt(d, (xr - 6, by1 + 10), f"CPU だけ {cpu_ms:.0f} ms", 16, False, INK2, "ra")
            xe = bar_x0 + (bar_x1 - bar_x0) * elapsed / t_max
            done = elapsed >= row["wall_s"] * 1e3 - 1e-9
            label = f"{elapsed:.0f} ms" + (f" → CPU の {ratio:.1f} 倍速い" if done else "")
            txt(d, (min(xe + 10, 440), by1 + 10), label, 22 if done else 18, done, INK if done else INK2)
        # 凡例
        lx, ly = 40, 506
        for col, lab in ((AQUA, "転送(送る・戻す)"), (BLUE, "GPU で計算"), (ORANGE, "CPU で計算")):
            d.rounded_rectangle((lx, ly - 9, lx + 18, ly + 9), 3, fill=col)
            txt(d, (lx + 26, ly), lab, 17, False, INK, "lm")
            lx += 26 + int(d.textlength(lab, font=F.get(17))) + 30
        txt(d, (920, ly), "scratch_surface・一辺 2048・1 枚", 15, False, INK2, "rm")
        return im

    frames, durations = [], []
    for i in range(n_frames):
        t_real = (i / fps) * 1e3 / slow
        frames.append(frame(t_real))
        durations.append(int(1000 / fps))
    durations[-1] = 3500                              # 最後の絵(両方の倍率が出た状態)で止める
    if F.missing:
        raise SystemExit("GIF に字形の無い文字: " + "".join(sorted(F.missing)))
    pal = frames[-1].quantize(colors=48, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    path = OUT / "gpu_round_trips.gif"
    q[0].save(path, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=True, disposal=1)
    # 最後の絵を静止図としても置く(GIF が動かない環境と、記事の写しの確認用)
    frames[-1].save(OUT / "gpu_round_trips_last.png")
    _check_image(path)
    a0 = np.asarray(frames[0], dtype=np.float64)
    a1 = np.asarray(frames[fps], dtype=np.float64)
    if float(np.abs(a1 - a0).mean()) < 0.5:
        raise SystemExit("GIF の最初の 1 秒で絵が動いていない")
    size = path.stat().st_size
    if size > 3 * 1024 * 1024:
        raise SystemExit(f"GIF が 3 MB を超えた: {size}")
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    nums = check_numbers()
    cov = route_counts()
    want = {"n_ops": 3810, "any": 767, "kinds": {"accel": 157, "native": 17, "shadow": 701},
            "min_ratio": 5.0, "n_shadow_rules": 701}
    got = {k: cov[k] for k in want}
    if got != want:
        raise SystemExit(f"GPU 経路の数が記事と違う: {got} != {want}")
    for p in (fig_coverage(cov), fig_crossover(), fig_round_trips(nums), fig_before_after(),
              fig_recipe_routes()):
        print(p.relative_to(ROOT).as_posix(), p.stat().st_size)
    print("倍率 %.1f → %.1f / 遅くなった点 %d / %d(%d 点 / %d 点)" % (
        nums["ratio_all"], nums["ratio_mixed"], nums["slow1"], nums["slow2"], nums["n1"], nums["n2"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
