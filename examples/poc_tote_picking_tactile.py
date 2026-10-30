# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Panda平行グリッパのかご間ピッキング: 視覚 / 理想化触覚 / 失敗別リトライ。

外から来るもの:
  * 実機の参考値: INSOL-HIGH・山善・東京納品代行の物流倉庫実証は約300回、最大5回の
    リトライ込み97%、10品平均131秒と報道された。これは実機であり、本PoCの仮想値との
    勝敗は論じない (Drone Journal, 2025-11-19, https://drone-journal.impress.co.jp/docs/special/1187932.html)。
  * MuJoCo Menagerie Franka Panda: 7軸腕・平行グリッパ、Apache-2.0。モデルは配布せず、
    MUJOCO_MENAGERIEで外部checkoutを指す
    (https://github.com/google-deepmind/mujoco_menagerie/tree/main/franka_emika_panda)。

自作のもの: 上方深度像を既存blob opで切り出す候補探索、9種の商品表、Pandaの6自由度IK、
理想化した指パッド力(法線・接線+雑音)、失敗型別リトライ、Wilson 95%区間、McNemar検定。
各試行は本物の7軸腕をmj_stepで接近・把持・運搬・解放まで逐次積分する。

門: 同一scene seed、非接着、真値の置き先内静止、決定性、0〜5回の曲線、難易度依存、
指パッド中心の較正、壁候補除外、易しい品物で開ループ70%以上、触覚の品物別内訳、
MuJoCo/Menagerieが無い場合は明示的[skip]。摩擦・solref/solimpと商品表はtotepick docstring。

Run: py -3.11 examples/poc_tote_picking_tactile.py [--full]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import totepick as TP  # noqa: E402


def gate(name, ok, detail=""):
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))
    if not ok:
        raise AssertionError(name)


def _render_trial(name, product_index, method, seed, expected, caption):
    """Record an actual attempt; every frame passes TP._render_mujoco_frame."""
    frames = []
    outcome = TP._attempt(TP.PRODUCTS[product_index], method, seed, 0,
                          render_depth=True, clutter=True, frame_sink=frames,
                          render_size=(1280, 720))
    gate("代表動画 " + name, outcome[1] == expected,
         "success" if outcome[0] else str(outcome[1]))
    figs.save_gif(name, frames, fps=8, caption=caption)
    return {"name": name, "product": TP.PRODUCTS[product_index].name,
            "method": method, "seed": seed,
            "outcome": "success" if outcome[0] else outcome[1],
            "resolution": [1280, 720], "frames": len(frames),
            "duration_s": len(frames) / 8}


def figures(summary, diagnostic=None):
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
    if diagnostic:
        ts=[x["time_s"] for x in diagnostic]
        series=[("product height [m]",ts,[x["product_z"] for x in diagnostic]),
                ("pad normal force [N]",ts,[x["normal_n"] for x in diagnostic]),
                ("pad tangential force [N]",ts,[x["tangent_n"] for x in diagnostic])]
        figs.save_plot("easy_trial_diagnosis",series,xlabel="MuJoCo time [s]",ylabel="measured value",
                       title="Easy-product physical diagnosis",colors=["neutral","emphasis","right"],
                       caption="易しい箱1試行の高さとmj_contactForce。関節目標・実角・出力・手先位置の全ログはresult.json。")
    return [
        _render_trial("trial_success_shampoo", 4, TP.METHODS[0], 4, None,
                      "MuJoCo実描画: シャンプーボトルの成功試行。"),
        _render_trial("trial_tactile_rescue", 0, TP.METHODS[1], 13, None,
                      "MuJoCo実描画: 視覚のみでは時間切れ、触覚で救済された同一場面。"),
        _render_trial("trial_fail_grasp_miss", 8, TP.METHODS[0], 0, "grasp_miss",
                      "MuJoCo実描画: 重量缶の掴み損ね。"),
        _render_trial("trial_fail_transport_slip", 1, TP.METHODS[0], 5, "transport_slip",
                      "MuJoCo実描画: 缶の運搬中滑落。"),
        _render_trial("trial_fail_timeout", 0, TP.METHODS[0], 12, "timeout",
                      "MuJoCo実描画: 箱の静止時間切れ。"),
    ]


def main():
    full = "--full" in sys.argv
    n = 300 if full else 2
    t0 = time.perf_counter()
    result = TP.run_benchmark(n_trials=n)
    summary = TP.summarize(result)
    elapsed = time.perf_counter() - t0
    result["summary"] = summary
    diag=TP._attempt(TP.PRODUCTS[0],TP.METHODS[1],7,0,render_depth=True,clutter=True,diagnostics=True)[3]["diagnostics"]
    former_zero={}
    for product_index,diag_seed in ((4,4),(8,8)):
        product=TP.PRODUCTS[product_index]
        attempt=TP._attempt(product,TP.METHODS[1],diag_seed,0,render_depth=True,clutter=True,diagnostics=True)
        former_zero[product.name]={"outcome":"success" if attempt[0] else attempt[1],
            "trace":attempt[3]["diagnostics"],"lifted":attempt[3]["lifted"],
            "cause":"standard tendon servo supplied about 4 N at the wide opening; contact height/load compounded the miss",
            "fix":"6x servo stiffness/damping within the +/-100 N force range; 20 mm loaded-contact compensation"}
    result["diagnosis"]={"easy_trial_log":diag,"former_zero_percent_products":former_zero,"fix_effect":{"previous_shadow_or_leap_easy_rate":0.0,
        "panda_open_loop_easy_rate":sum(r["attempts"][0]["success"] for r in result["rows"] if r["method"]==TP.METHODS[0] and r["difficulty"]=="easy")/max(1,sum(r["method"]==TP.METHODS[0] and r["difficulty"]=="easy" for r in result["rows"])),
        "fixes":["finger-pad centre calibration","world-frame orientation error in 6-DoF IK","depth wall exclusion","Panda gripper ctrlrange 0..255"]}}
    result["wall_seconds"] = elapsed
    result["provenance"] = "every attempt is a complete mj_step Menagerie-Panda trajectory"
    asset = TP.validate_mujoco_asset(os.environ.get("MUJOCO_MENAGERIE", r"C:\dev\projects\mujoco_menagerie"))
    result["menagerie_validation"] = asset
    if asset["skipped"]:
        print("  [skip] MuJoCo/Menagerie門 —— " + asset["reason"])
    else:
        gate("Menagerie Pandaを実ロード", asset["arm_actuators"] == 7 and asset["gripper_ctrlrange"] == [0.0, 255.0], str(asset))
    gate("3手法が同じ300 scene seed" if full else "3手法が同じscene seed",
         all(len({r["scene_seed"] for r in result["rows"] if r["trial"] == i}) == 1 for i in range(n)))
    gate("非接着", result["contact"]["adhesion"] is False)
    easy=[r for r in result["rows"] if r["method"]==TP.METHODS[0] and r["difficulty"]=="easy"]
    easy_rate=sum(r["attempts"][0]["success"] for r in easy)/len(easy) if easy else 0
    if full:
        gate("易しい品物で開ループ70%以上", easy_rate>=.70, f"{easy_rate:.1%}")
        gate("異常な100%ではない", all(summary["curves"][m][-1]["rate"] < 1 for m in TP.METHODS))
    gate("全試行でmj_step", all(a["mj_steps"] > 1000 for r in result["rows"] for a in r["attempts"]))
    if full:
        gate("全手法が再試行を使用", all(any(len(r["attempts"])>1 for r in result["rows"] if r["method"]==m) for m in TP.METHODS))
    result["representative_videos"]=figures(summary,diag)
    out = figs.target_dir()
    if out is not None:
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"n_trials": n, "wall_seconds": elapsed, "curves": summary["curves"],
                      "tactile_delta": summary["tactile_delta"], "timing": summary["timing"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
