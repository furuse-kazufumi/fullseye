"""ピラミッドの関門 — 粗い階層は細かい階層の順位を保存しているか。

正本 = ``docs/HIGHSPEED_VISION.md``。

## なぜ要るか(ユーザー、2026-08-25)

> マッチングアルゴリズムは大体ピラミッドサーチだけど、輝度相関値や形状一致スコアで
> やってる。**ピラミッドになるものが何か** ってところを考えないといけない

ピラミッドの正体は解像度ではなく **証拠を担う量の階層** である。そして
ピラミッドになれる条件は 1 つに絞れる:

> **粗い階層のスコアが、細かい階層のスコアの順位(あるいは上界)を保存すること。**

branch-and-bound の admissibility そのもの。保存しなければ、枝刈りが真の最適解を
**静かに** 捨てる。静かに、というのが厄介で、探索は最後まで走り切って
それらしい答えを返す。

## 今日この失敗を実際にやった

afterman の実験 NB。AR2 の「内側 800 ステップ訓練」は、最終性能という細かい量に
対する **粗い階層** だった。粗い階層で出した順位を細かい階層で検算していなかったので、
6.4 倍という差の内訳を誤って解釈していた
(正しくは 打ち切り 1.25 倍 x NORM を切る 8.5 倍)。

**この道具があれば事前に防げた。**

## 何を返すか

- **Spearman ρ** —— 粗↔細の順位相関。1.0 なら完全に保存
- **上位 k の残存率** —— 細かい階層での真の上位 k が、粗い階層の上位 m に何割残るか。
  枝刈り幅 m を決めるのはこの数字であって ρ ではない
- **上界性** —— 粗いスコアが細かいスコアの上界になっているか(admissible か)。
  なっていれば閾値による枝刈りが安全

    import pyramid_gate as PG
    PG.check(coarse_fn, fine_fn, candidates)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class GateResult:
    rho: float                  # Spearman 順位相関
    keep: dict                  # {(k, m): 残存率}
    admissible: float           # 粗 >= 細 が成り立つ割合(大きいほど上界に近い)
    n: int
    coarse: np.ndarray
    fine: np.ndarray

    def verdict(self, need: float = 1.0) -> str:
        """**上位 k の残存率で判定する。Spearman rho では判定しない。**

        最初は rho で判定していたが、それは誤りだった。候補の大半は雑音の位置で、
        そこの順位は最初から意味が無い。rho はその雑音に支配される。
        実際に測ると 3 軸とも rho 0.57〜0.67 と冴えないのに、上位 k の残存率は
        全て 1.00 だった。**枝刈りに効くのは「良い候補が残るか」だけ。**
        実際のピラミッドサーチが粗い階層の雑さに耐えるのはこれが理由。
        """
        if not self.keep:
            return "判定不能"
        v = min(self.keep.values())
        if v >= need:
            return "使える"
        if v >= 0.8:
            return "条件つき(枝刈り幅を広げれば使える)"
        return "**使えない**(真の上位を粗い階層が落としている)"

    def report(self, name: str = "") -> str:
        L = [f"  {name}" if name else ""]
        L.append(f"   判定 -> {self.verdict()}"
                 f"   (参考: Spearman rho = {self.rho:.3f}。**判定には使わない**)")
        L.append(f"   粗 >= 細 の割合(上界性) = {self.admissible:.2f}"
                 f"  {'(閾値枝刈りが安全)' if self.admissible > 0.95 else '(閾値枝刈りは危険)'}")
        for (k, m), v in sorted(self.keep.items()):
            L.append(f"   真の上位 {k} が 粗い階層の上位 {m} に残る割合 = {v:.2f}")
        return "\n".join(x for x in L if x)


def _rank(x):
    return np.argsort(np.argsort(np.asarray(x, dtype=float)))


def spearman(a, b) -> float:
    ra, rb = _rank(a), _rank(b)
    if ra.std() < 1e-12 or rb.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def check(coarse, fine, candidates=None, keep_pairs=((1, 3), (1, 5), (3, 10)),
          higher_is_better: bool = True) -> GateResult:
    """粗い評価と細かい評価を候補に当てて、ピラミッドとして使えるか判定する。

    coarse / fine は候補を受け取ってスコアを返す関数、または既に計算済みの配列。
    """
    if callable(coarse):
        c = np.array([float(coarse(x)) for x in candidates], dtype=float)
        f = np.array([float(fine(x)) for x in candidates], dtype=float)
    else:
        c = np.asarray(coarse, dtype=float)
        f = np.asarray(fine, dtype=float)
    if not higher_is_better:              # 小さいほど良い場合は符号を反転
        c, f = -c, -f
    ok = np.isfinite(c) & np.isfinite(f)
    c, f = c[ok], f[ok]
    rho = spearman(c, f)

    order_c = np.argsort(-c)
    order_f = np.argsort(-f)
    keep = {}
    for k, m in keep_pairs:
        if k > len(f) or m > len(f):
            continue
        top_f = set(order_f[:k].tolist())
        top_c = set(order_c[:m].tolist())
        keep[(k, m)] = len(top_f & top_c) / k

    # 上界性: スケールが違うので、順位でなく「粗が細を下回らない」割合を
    # 同一スケールに正規化してから見る
    def _norm(v):
        s = v.max() - v.min()
        return (v - v.min()) / s if s > 1e-12 else np.zeros_like(v)
    admissible = float((_norm(c) >= _norm(f) - 1e-9).mean())
    return GateResult(rho=rho, keep=keep, admissible=admissible, n=int(ok.sum()),
                      coarse=c, fine=f)


# --------------------------------------------------------------------------
# 実例 1 — 画像照合で「何がピラミッドになるか」を 3 軸で比べる
# --------------------------------------------------------------------------
def matching_axes(n_cand: int = 60, size: int = 128, seed: int = 0,
                  target: str = "thick") -> dict:
    """輝度相関の探索に対し、3 つの粗視化軸の admissibility を測る。

        解像度   —— 画像を 1/4 に間引いて相関
        ビット幅 —— 輝度を 2 bit に量子化して相関
        点数     —— モデルの画素を 1/16 に間引いて相関

    候補 = 画像上のいろいろな位置。細かい階層 = 原寸・全点での正規化相関。
    """
    rng = np.random.default_rng(seed)
    # 細い線を含む場面。間引きで壊れやすいものを意図的に入れる
    img = rng.normal(0, 0.15, (size, size))
    img[30:34, 10:110] += 1.4                       # 太い横棒
    img[60:61, 10:110] += 1.4                       # **細い横線**(1 px)
    img[80:110, 40:44] += 1.4                       # 縦棒
    # target="thick" は太い棒(4 px)、"thin" は 1 px の細線からモデルを切る。
    # **細線は解像度の粗視化で消える**ので、軸の良し悪しがここで分かれるはず
    if target == "thin":
        tpl = img[57:63, 50:70].copy()
        anchors = ((57, 50), (28, 50), (78, 40))
    else:
        tpl = img[28:36, 50:70].copy()
        anchors = ((28, 50), (57, 50), (78, 40))
    tpl = tpl - tpl.mean()
    th, tw = tpl.shape

    # **良い候補どうしの区別** を問う。3 つの構造(太い棒 / 細い線 / 縦棒)の
    # 周りに小さくずらした候補を密に置く。雑音の位置を並べても順位は無意味なので、
    # 「上位に残るか」を問うにはこの作り方でないといけない
    pos = []
    for (r0, c0) in anchors:
        for dr in (-3, -2, -1, 0, 1, 2, 3):
            for dc in (-4, -2, 0, 2, 4):
                pos.append((max(0, min(size - th, r0 + dr)),
                            max(0, min(size - tw, c0 + dc))))
    pos += [(int(rng.integers(0, size - th)), int(rng.integers(0, size - tw)))
            for _ in range(max(0, n_cand - len(pos)))]

    def ncc(patch, t):
        p = patch - patch.mean()
        d = np.sqrt((p ** 2).sum() * (t ** 2).sum())
        return float((p * t).sum() / d) if d > 1e-12 else 0.0

    def fine(rc):
        r, c = rc
        return ncc(img[r:r + th, c:c + tw], tpl)

    def _box2(a):
        """2x2 の面積平均で縮小。**面積は平均に対して閉じている**ので
        1 px の細線も「半分の濃さの線」として残る。"""
        h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
        return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean((1, 3))

    def coarse_res(rc):
        """**単純な間引き**。1 px の細線は運が悪いと丸ごと消える。"""
        r, c = rc
        return ncc(img[r:r + th:2, c:c + tw:2], tpl[::2, ::2])

    def coarse_area(rc):
        """**面積平均で縮小**(本来のピラミッドの作り方)。"""
        r, c = rc
        return ncc(_box2(img[r:r + th, c:c + tw]), _box2(tpl))

    def coarse_region(rc):
        """**一度 2 値の領域にしてから面積平均**(= 被覆率のピラミッド)。

        ユーザーの観察(2026-08-25): HALCON の find_shape 系は一度カクカクした
        領域にしているように見える、縮小構造を画像に近い扱いにするためでは。
        原理としては、点の有無を **面積の被覆率** に変換すると、平均に対して
        閉じるので縮小しても壊れない。
        """
        r, c = rc
        b = (img[r:r + th, c:c + tw] > 0.7).astype(float)
        m = (tpl > 0.7 * (tpl.std() + 1e-9)).astype(float)
        return ncc(_box2(b), _box2(m))

    def coarse_bits(rc):
        r, c = rc
        q = np.round(img[r:r + th, c:c + tw] * 1.5) / 1.5     # 粗い量子化
        return ncc(q, np.round(tpl * 1.5) / 1.5)

    def coarse_pts(rc):
        r, c = rc
        m = tpl.ravel()
        idx = np.argsort(-np.abs(m))[: max(4, m.size // 16)]  # 強い点だけ残す
        p = img[r:r + th, c:c + tw].ravel()[idx]
        t = m[idx]
        p = p - p.mean()
        t = t - t.mean()
        d = np.sqrt((p ** 2).sum() * (t ** 2).sum())
        return float((p * t).sum() / d) if d > 1e-12 else 0.0

    return {"解像度 1/2(間引き)": check(coarse_res, fine, pos),
            "解像度 1/2(面積平均)": check(coarse_area, fine, pos),
            "領域化してから面積平均": check(coarse_region, fine, pos),
            "ビット幅を粗く": check(coarse_bits, fine, pos),
            "モデル点数 1/16": check(coarse_pts, fine, pos)}


def _keep1(r):
    return min(r.keep.values()) if r.keep else 0.0


def main():
    print("ピラミッドの関門 — 粗い階層は細かい階層の上位を残すか")
    for target, label in (("thick", "太い棒(4 px)をモデルにする"),
                          ("thin", "**細い線(1 px)** をモデルにする")):
        print(f"\n=== {label} ===")
        res = matching_axes(target=target)
        for name, r in res.items():
            print("")
            print(r.report(name))
        best = max(res, key=lambda k: (_keep1(res[k]), res[k].rho))
        print(f"\n  -> この場面で使える軸: **{best}**"
              f"(上位残存 {_keep1(res[best]):.2f})")


if __name__ == "__main__":
    main()
