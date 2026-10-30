"""仮想工場の開先3D点群検査。

外から来るもの: WEF 2025の開先欠陥90%減、既存CAD/scan・ICP PoCの実寸表現。
自作: CAD開先、欠測・外れ値を含むscan、角度幾何、学習/holdout評価。
門: 計測器は点群だけを読み、姿勢・欠陥真値を読まない。
"""
import examplefig as figs
from lighthouse_vfactory_cli import main


def save_figure(name, image, caption):
    return figs.save(name, image, caption=caption)


if __name__ == "__main__":
    status = main("bevel", save_figure)
    if figs.errors(): print("図の書き出しで失敗:", "; ".join(figs.errors()))
    raise SystemExit(status)
