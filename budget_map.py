"""予算地図 — (対象の速さ x 雑音)の各作動点で、時間予算つき適応度が何を選ぶか。"""
import json
from pathlib import Path
import vloop_evolve as E

POINTS = [(1.0, 0.001), (2.0, 0.001), (1.0, 0.005), (2.0, 0.005)]
rows = []
for sp, nz in POINTS:
    E.SPEED, E.NOISE_P = sp, nz
    E._FRAMES.clear()
    print(f"\n=== 速さ {sp}x / 雑音 p={nz} ===", flush=True)
    r = {}
    for fit in ("static", "loop"):
        print(f"  適応度 {'A(精度だけ)' if fit=='static' else 'B(時間予算)'}",
              flush=True)
        r[fit] = E.evolve(fit, seed=0)
    a, b = r["static"], r["loop"]
    a_loop = E.loop_score(a["gene"], a["ms"])
    rows.append({"speed": sp, "noise": nz,
                 "A": E.describe(a["gene"]), "A_mm": a["err"] * 1000,
                 "A_ms": a["ms"], "A_loop": a_loop,
                 "B": E.describe(b["gene"]), "B_mm": b["err"] * 1000,
                 "B_ms": b["ms"], "B_loop": b["fit"],
                 "A_win": bool(a["gene"]["use_window"]),
                 "B_win": bool(b["gene"]["use_window"]),
                 "A_meth": int(a["gene"]["method"]),
                 "B_meth": int(b["gene"]["method"]),
                 "A_stride": int(a["gene"]["stride"]),
                 "B_stride": int(b["gene"]["stride"])})
    print(f"  -> A {rows[-1]['A']}  閉ループ {a_loop:.4f}")
    print(f"     B {rows[-1]['B']}  閉ループ {b['fit']:.4f}", flush=True)

print("\n\n予算地図")
print(f"{'速さ':>5}{'雑音':>9}{'適応度Aが選ぶ':>42}{'A閉ループ':>10}"
      f"{'適応度Bが選ぶ':>42}{'B閉ループ':>10}{'B/A':>7}")
for r in rows:
    print(f"{r['speed']:>5.0f}{r['noise']:>9.4f}{r['A']:>42}{r['A_loop']:>10.4f}"
          f"{r['B']:>42}{r['B_loop']:>10.4f}{r['A_loop']/max(r['B_loop'],1e-9):>7.2f}")
print("\nアルゴリズムの選択(0=重心 1=テンプレート)と窓の有無")
for r in rows:
    print(f"  速さ{r['speed']:.0f}x p={r['noise']:.4f}  "
          f"A: 手法{r['A_meth']} 窓{r['A_win']} 間引き{r['A_stride']}  |  "
          f"B: 手法{r['B_meth']} 窓{r['B_win']} 間引き{r['B_stride']}")
Path("out").mkdir(exist_ok=True)
Path("out/budget_map.json").write_text(json.dumps(rows, ensure_ascii=False,
                                                  indent=2), encoding="utf-8")
print("\n-> out/budget_map.json")
