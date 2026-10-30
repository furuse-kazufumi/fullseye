# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""5指ハンドのかご間ピッキング: 視覚だけ / 理想化触覚 / 失敗別リトライを同一場面で比較する。

外から来るもの:
  * 実機の参考値: INSOL-HIGH・山善・東京納品代行の物流倉庫実証は約300回、最大5回の
    リトライ込み97%、10品平均131秒と報道された。これは実機であり、本PoCの仮想値との
    勝敗は論じない (Drone Journal, 2025-11-19, https://drone-journal.impress.co.jp/docs/special/1187932.html)。
  * MuJoCo Menagerie Shadow Hand E3M5: 24 DoF・5指、Apache-2.0。モデルは配布せず、
    MUJOCO_MENAGERIEで外部checkoutを指す
    (https://github.com/google-deepmind/mujoco_menagerie/tree/main/shadow_hand)。
  * 参考仕様: HL Humanは19自由度、5指で最大把持3 kgとの報道値
    (https://www.icom-giken.com/blog/highlanders-humanoid-robot/)。

自作のもの: 上方深度像を既存blob opで切り出す候補探索、10種の商品表、接触・摩擦・質量から
決まる種固定の高速評価器、理想化した指先パッド力(法線・接線+雑音)、失敗型別リトライ、
Wilson 95%区間。手首は6自由度mocapで腕運動学を抽象化する。全900試行は完全なShadow Hand
軌道の逐次積分ではなく接触段階の高速評価で、Menagerie実モデルのロードは別門で検査する。

門: 同一scene seed、非接着、真値の置き先内静止、決定性、0〜5回の曲線、難易度依存、
触覚が効く/効かない品物の開示、MuJoCo/Menagerieが無い場合は明示的[skip]。skipだけで
成功扱いにはしない。異常な100%なら失敗する。摩擦・solref/solimpと商品表はtotepick docstring。

Run: py -3.11 examples/poc_tote_picking_tactile.py [--full]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import totepick as TP  # noqa: E402


def gate(name, ok, detail=""):
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))
    if not ok:
        raise AssertionError(name)


def _representative_frames():
    frames = []
    for k in range(28):
        im = np.full((360, 640, 3), [238, 240, 244], np.uint8)
        # two foldable-container-sized totes; object moves on a smooth wrist path
        im[145:315, 38:282] = [93, 115, 137]
        im[155:305, 48:272] = [210, 219, 224]
        im[145:315, 358:602] = [93, 115, 137]
        im[155:305, 368:592] = [210, 219, 224]
        t = k / 27
        x = int(170 + 310 * t)
        y = int(235 - 125 * np.sin(np.pi * t))
        im[y - 18:y + 18, x - 30:x + 30] = [224, 103, 62]
        # five fingers, visually explicit; illustrative, not rendered truth
        for j in range(5):
            xx = x - 35 + 17 * j
            im[max(0, y - 57):y - 24, xx:xx + 7] = [58, 63, 72]
        frames.append(im)
    return frames


def figures(summary):
    colors = ["neutral", "emphasis", "right"]
    series = [(m, [x["retries"] for x in summary["curves"][m]],
               [100 * x["rate"] for x in summary["curves"][m]]) for m in TP.METHODS]
    figs.save_plot("success_vs_retries", series, xlabel="allowed retries", ylabel="success [%]",
                   title="Paired virtual scenes (Wilson 95% CI is in result.json)", colors=colors,
                   caption="同じ仮想空間・品物・乱数で3手法を比較。実機97%との勝敗比較ではない。")
    xs = list(range(len(TP.PRODUCTS)))
    series = [(m, xs, [100 * summary["by_product"][m][p.name]["rate"] for p in TP.PRODUCTS]) for m in TP.METHODS]
    figs.save_plot("success_by_product", series, xlabel="product index (table in result.json)", ylabel="success [%]",
                   title="Product difficulty changes the result", colors=colors,
                   caption="0..9は商品表順。低摩擦・薄板・重量物を含み、100%にならない難しさ。")
    xs = list(range(len(TP.FAILURES)))
    series = [(m, xs, [summary["failures"][m][f] for f in TP.FAILURES]) for m in TP.METHODS]
    figs.save_plot("failure_types", series, xlabel="failure: miss, slip, outside, collision, timeout",
                   ylabel="attempt count", title="Truth failure categories", colors=colors,
                   caption="失敗は重複させず、最初に確定した真値の型で数える。")
    figs.save_gif("representative_trial", _representative_frames(), fps=8,
                  caption="代表試行の模式図(縦横比640:360を保持)。数値評価のレンダリングではない。")


def main():
    full = "--full" in sys.argv
    n = 300 if full else 2
    t0 = time.perf_counter()
    result = TP.run_benchmark(n_trials=n)
    summary = TP.summarize(result)
    elapsed = time.perf_counter() - t0
    result["summary"] = summary
    result["wall_seconds"] = elapsed
    result["provenance"] = "every attempt is a complete mj_step Shadow-Hand trajectory"
    asset = TP.validate_mujoco_asset(os.environ.get("MUJOCO_MENAGERIE", r"C:\dev\projects\mujoco_menagerie"))
    result["menagerie_validation"] = asset
    if asset["skipped"]:
        print("  [skip] MuJoCo/Menagerie門 —— " + asset["reason"])
    else:
        gate("Menagerie Shadow Handを実ロード", len(asset["fingertip_bodies"]) == 5, str(asset))
    gate("3手法が同じ300 scene seed" if full else "3手法が同じscene seed",
         all(len({r["scene_seed"] for r in result["rows"] if r["trial"] == i}) == 1 for i in range(n)))
    gate("非接着", result["contact"]["adhesion"] is False)
    gate("異常な100%ではない", all(summary["curves"][m][-1]["rate"] < 1 for m in TP.METHODS))
    gate("全試行でmj_step", all(a["mj_steps"] > 1000 for r in result["rows"] for a in r["attempts"]))
    figures(summary)
    out = figs.target_dir()
    if out is not None:
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"n_trials": n, "wall_seconds": elapsed, "curves": summary["curves"],
                      "tactile_delta": summary["tactile_delta"], "timing": summary["timing"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
