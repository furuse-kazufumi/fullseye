# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op が **4 連結で見ているか 8 連結で見ているか**を、意味を知らずに測る。

region を食う/返す op 215 本のうち **168 本(78%)** が連結性に触れていない。そして
`connection` が numpy backend で 4 連結、cv2 backend で 8 連結になっていた件
(0.1.11 で修正)が示すとおり、この違いは **8x8 の市松を 32 個と 1 個に分ける**。

**端の規約には ``op(pad_P(x))[crop] == op(x)`` というカーネル非依存の恒等式があったが、
連結性にはそれが無い。** 代わりに「**同じ問いに違う答えが出る 3 つの入力**」を使う:

* ``A`` = 斜めだけで触れる 2 つの塊 —— 4 連結なら 2 個、8 連結なら 1 個
* ``B`` = ``A`` に橋を 1 つ足したもの —— **どちらの連結性でも 1 個**
* ``C`` = ``A`` の 2 つを引き離したもの —— **どちらの連結性でも 2 個**

op の意味は知らないが、``A`` の答えが ``B`` 型なら 8 連結、``C`` 型なら 4 連結だと
言える。比較は **元の 2 つの塊が占める画素だけ**に絞る(橋や位置の違いを見ないため)。

**この道具が測れるのは「成分の大きさ・個数で出力が変わる op」だけである。** 局所的な
形態学(収縮・膨張)は、塊がどの成分に属するかに関係なく同じ答えを返すので
`not_connectivity_dependent` に落ちる —— それは「連結性を使っていない」ではなく
**「この測り方では見えない」**という意味である。混同しないこと。

**幾何変換には使えない。** 分離ケースは 2 つ目の塊を別の場所へ動かすので、座標を
写す op(極座標変換など)では「連結性の違い」ではなく「配置の違い」を測ってしまう。
実際 `polar_trans_region_inv` が 8 連結と出たが、これは信用できないので契約には
書かなかった。**判定が出ることと、その判定が正しいことは別**である。

**どちらにも似ていない / 両方に等しく似ている op は「判定不能」と返す。**
連結性を使っていない op(点処理・平滑化)はここに落ちる —— それが正しい答えである。
推測で 4 か 8 を書けば、その推測が契約になってしまう。

使い方::

    py -3.11 tools/impl2/connect_probe.py --all-region --json docs/op_connectivity.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EPS = 1e-9
N = 20


def _cases() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """A(斜め接触) / B(橋あり=必ず 1 個) / C(分離=必ず 2 個) と、比較に使う面。

    **比較面は接触点から最も遠い角に置く。** 橋は塊の近傍を物理的に変えるので、
    接触点の近くを見ると「連結性の違い」ではなく「形の違い」を測ってしまう ——
    最初の版はそれで `boundary`(領域 − 収縮版)を 4 連結と誤判定した。連結性の
    効果は**大域(ラベル付け)**、形の効果は**局所**なので、遠い場所だけを見れば
    局所の違いは届かない。
    """
    a = np.zeros((N, N)); b = np.zeros((N, N)); c = np.zeros((N, N))
    b1 = (slice(2, 9), slice(2, 9))            # 7x7。接触は右下の角 (8,8)
    b2 = (slice(9, 16), slice(9, 16))          # 斜めだけで触れる
    for m in (a, b, c):
        m[b1] = 1.0
    a[b2] = 1.0
    b[b2] = 1.0
    b[9, 8] = 1.0                              # 橋 1 画素(4 連結でも繋がる)
    c[b2] = 1.0
    c[9:16, 9:16] = 0.0
    c[13:20, 13:20] = 1.0                      # 引き離した 2 つ目

    face = np.zeros((N, N), bool)
    face[2:5, 2:5] = True                      # **接触点から最も遠い角**だけを見る
    return a, b, c, face


def _self_test() -> str:
    """**陽性対照**: 答えを知っている参照実装に同じ判定を当てて、道具が当てられるか。

    当てられない道具で op を判定すれば、出てくるのは事実ではなく思い込みになる。
    """
    from scipy import ndimage as ndi

    def keep_big(mask, structure, min_area=60):
        """**面積しきい値**で残す参照。連結性が変われば「blob1 が大きい塊の一部か」が
        変わり、blob1 の上の出力が変わる。最初は「最大成分を残す」を参照にしたが、
        それは 4 でも 8 でも blob1 を残すので**比較面に差が出ず**、陽性対照が
        NG になった —— 道具でなく**参照の選び方**が誤っていた。"""
        lab, n = ndi.label(mask > 0, structure=structure)
        if n == 0:
            return mask * 0.0
        sizes = ndi.sum(mask > 0, lab, range(1, n + 1))
        keep = {i + 1 for i, sz in enumerate(sizes) if sz >= min_area}
        return np.isin(lab, list(keep)).astype(np.float64)

    A, B, C, face = _cases()
    four = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    eight = np.ones((3, 3))
    verdicts = []
    for st, expect in ((four, 4), (eight, 8)):
        o = {k: keep_big(m, st) for k, m in (("diag", A), ("bridged", B), ("separate", C))}
        db = float(np.max(np.abs(o["diag"][face] - o["bridged"][face])))
        ds = float(np.max(np.abs(o["diag"][face] - o["separate"][face])))
        got = 8 if (db <= EPS and ds > EPS) else (4 if (ds <= EPS and db > EPS) else None)
        verdicts.append((expect, got))
    ok = all(e == g for e, g in verdicts)
    return "OK" if ok else f"NG {verdicts}"


def detect(op: str) -> dict:
    import fullseye as fs

    rec: dict = {"op": op}
    A, B, C, face = _cases()
    outs = {}
    for name, m in (("diag", A), ("bridged", B), ("separate", C)):
        try:
            o = np.asarray(fs.apply(m.copy(), op, a=0.5, b=0.5), np.float64)
        except Exception as e:
            return {**rec, "status": "not_applicable",
                    "reason": f"{type(e).__name__}: {e}"[:140]}
        if o.shape != m.shape or not np.isfinite(o).all():
            return {**rec, "status": "not_applicable", "reason": "形が違う/非有限"}
        outs[name] = o

    d_bridged = float(np.max(np.abs(outs["diag"][face] - outs["bridged"][face])))
    d_separate = float(np.max(np.abs(outs["diag"][face] - outs["separate"][face])))
    rec["diff_vs_bridged"] = d_bridged
    rec["diff_vs_separate"] = d_separate

    # 橋あり/分離で **そもそも答えが変わらない** op は、連結性を見ていない
    spread = float(np.max(np.abs(outs["bridged"][face] - outs["separate"][face])))
    rec["bridged_vs_separate"] = spread
    if spread <= EPS:
        rec["status"] = "not_connectivity_dependent"
        return rec

    if d_bridged <= EPS and d_separate > EPS:
        rec["status"] = "determined"; rec["connectivity"] = 8
    elif d_separate <= EPS and d_bridged > EPS:
        rec["status"] = "determined"; rec["connectivity"] = 4
    else:
        rec["status"] = "undetermined"
        rec["reason"] = "斜め接触の答えが、橋あり側とも分離側とも一致しない"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops")
    ap.add_argument("--all-region", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()

    names = [o.strip() for o in (a.ops or "").split(",") if o.strip()]
    if a.all_region:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color")
                  and o["in_sort"] == "region" and o["out_sort"] == "region"]
    names = list(dict.fromkeys(names))
    if not names:
        print("op を指定してください"); return 2

    st = _self_test()
    print(f"陽性対照(答えを知っている参照実装で判定できるか): {st}")
    if st != "OK":
        print("→ 道具が当てられないので op の判定はしない(思い込みを事実として出さない)")
        return 3

    out = []
    for op in names:
        try:
            r = detect(op)
        except Exception as e:
            r = {"op": op, "status": "not_applicable", "reason": f"{type(e).__name__}: {e}"[:140]}
        out.append(r)
        line = f"[{r['status']:28s}] {op:24s}"
        if r.get("connectivity"):
            line += f" {r['connectivity']} 連結"
        print(line)

    det = [r for r in out if r["status"] == "determined"]
    import collections
    print(f"\n確定 {len(det)} / {len(out)}: "
          + ", ".join(f"{k} 連結 {v}" for k, v in
                      collections.Counter(r["connectivity"] for r in det).most_common()))
    print(f"  連結性を見ていない: {sum(1 for r in out if r['status']=='not_connectivity_dependent')}")
    print(f"  判定不能: {sum(1 for r in out if r['status']=='undetermined')}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
