"""仮想工場の鋳造ホイールX線検査。

外から来るもの: WEF 2025の重大欠陥見逃し98.1%減、既存CT/X線PoCの物理構成。
自作: 気孔・引け巣・介在物と重大度規則、探索・holdout評価。
門: 検出器は画素だけを読み、真値は独立照合にだけ使う。
"""
import examplefig as figs
from lighthouse_vfactory_cli import main


def save_figure(name, image, caption):
    return figs.save(name, image, caption=caption)


if __name__ == "__main__":
    status = main("wheel", save_figure)
    if figs.errors(): print("図の書き出しで失敗:", "; ".join(figs.errors()))
    raise SystemExit(status)
