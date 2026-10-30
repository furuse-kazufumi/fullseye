"""仮想工場のSMT AOI検査。

外から来るもの: WEF 2023 AI版の不良率99%減、既存solder_fillet_aoiの3色照明。
自作: 5欠陥の外観像、固定閾値基準、探索・holdout評価。
門: 検出器は画像以外を受け取らず、乱数で判定しない。
"""
import examplefig as figs
from lighthouse_vfactory_cli import main


def save_figure(name, image, caption):
    return figs.save(name, image, caption=caption)


if __name__ == "__main__":
    status = main("smt", save_figure)
    if figs.errors(): print("図の書き出しで失敗:", "; ".join(figs.errors()))
    raise SystemExit(status)
