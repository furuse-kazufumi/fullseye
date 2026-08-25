"""ピラミッドの深さを自動で決める — NumLevels を目視でなく実測で選ぶ。

## 一次ソースで確認したこと(2026-08-25)

MVTec HALCON の shape-based matching について、外部 AI 経由で一次資料を確認:

  - **モデルの構築は各階層ごとに画像ピラミッド上で行う。単一のエッジマップを
    間引くのではない**
  - ピラミッドは「平滑化してから間引く」
  - スコアは勾配方向の余弦(Steger, DAGM 2000)
  - **細い/小さい構造で NumLevels を下げねばならないのは、平滑化と縮小で
    その構造が消え、勾配がコントラスト閾値を下回ってモデル点が抽出されなくなるから**

出典: http://download.mvtec.com/halcon-9.0-solution-guide-ii-b-shape-based-matching.pdf
      https://www.mvtec.com/doc/halcon/12/en/create_shape_model.html
      https://www.mvtec.com/doc/halcon/11/en/inspect_shape_model.html

## ここでやること

MVTec の推奨手順は「inspect_shape_model で各階層を **目視** して、細部が消えて
いたら NumLevels を下げる」。それを実測に置き換える。

各階層 L について:
  - その階層で抽出できたモデル点の数(消えていないか)
  - **その階層のスコアが、原寸のスコアの上位を残すか**(pyramid_gate の関門)

を測り、両方が保たれる最大の L を NumLevels として返す。**目視でなく数字で決まる。**
"""
from __future__ import annotations

import numpy as np

import pyramid_gate as PG
from pyramid_edge import box2, edge_model, grad, score


def scene(size=192, seed=0):
    rng = np.random.default_rng(seed)
    img = rng.normal(0, 0.10, (size, size))
    img[40:52, 20:170] += 1.5                 # 太い棒 12 px
    img[90:91, 20:170] += 1.5                 # **細い線 1 px**
    img[120:170, 60:64] += 1.5                # 縦棒 4 px
    return img


def pyramid(img, n):
    out = [img]
    for _ in range(n):
        out.append(box2(out[-1]))
    return out


def choose_levels(img, box, max_levels=5, keep_need=1.0, min_pts=12):
    """(各階層の測定, 推奨 NumLevels) を返す。"""
    r0, r1, c0, c1 = box
    th, tw = r1 - r0, c1 - c0
    pyr = pyramid(img, max_levels)
    tpl0 = img[r0:r1, c0:c1]
    m0 = edge_model(tpl0)

    # 候補は原寸で「良い候補どうし」。粗い階層では格子に落ちるので、
    # **粗い格子より広い間隔**で置く(前回これを怠って比較が無効になった)
    step = 2 ** max_levels
    pos = [(max(0, min(img.shape[0] - th, r0 + dr * step)),
            max(0, min(img.shape[1] - tw, c0 + dc * step)))
           for dr in (-2, -1, 0, 1, 2) for dc in (-2, -1, 0, 1, 2)]

    def fine(rc):
        return score(m0, img, rc[0], rc[1])

    rows = []
    best = 0
    for L in range(0, max_levels + 1):
        s = 2 ** L
        tplL = pyr[L][r0 // s:max(r0 // s + 2, r1 // s),
                      c0 // s:max(c0 // s + 2, c1 // s)]
        mL = edge_model(tplL)
        npts = 0 if mL is None else len(mL[0])

        def coarse(rc, mL=mL, L=L, s=s):
            return score(mL, pyr[L], rc[0] // s, rc[1] // s)

        g = PG.check(coarse, fine, pos)
        keep = min(g.keep.values()) if g.keep else 0.0
        ok = (npts >= min_pts) and (keep >= keep_need)
        rows.append({"level": L, "size": pyr[L].shape[0], "pts": npts,
                     "keep": keep, "rho": g.rho, "ok": ok})
        if ok:
            best = L
        else:
            break
    return rows, best


def main():
    img = scene()
    print("ピラミッドの深さを実測で決める(目視の代わり)")
    print("  場面: 太い棒 12px / **細い線 1px** / 縦棒 4px")
    for name, box in (("太い棒 12px", (40, 52, 60, 140)),
                      ("**細い線 1px**", (86, 96, 60, 140)),
                      ("縦棒 4px", (120, 170, 58, 68))):
        rows, best = choose_levels(img, box)
        print(f"\n  --- モデル = {name} ---")
        print(f"  {'階層':>4}{'画像':>7}{'モデル点数':>10}{'上位残存':>9}"
              f"{'rho':>7}   判定")
        for r in rows:
            print(f"  {r['level']:>4}{r['size']:>7}{r['pts']:>10}"
                  f"{r['keep']:9.2f}{r['rho']:7.3f}   "
                  f"{'○' if r['ok'] else '× ここで壊れる'}")
        print(f"  -> 推奨 NumLevels = {best + 1}(階層 0..{best})")


if __name__ == "__main__":
    main()
