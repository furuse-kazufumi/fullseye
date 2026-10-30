"""仮想工場の開先3D点群検査。

外から来るもの: WEF 2025の開先欠陥90%減、既存CAD/scan・ICP PoCの実寸表現。
自作: CAD開先、欠測・外れ値を含むscan、角度幾何、学習/holdout評価。
門: 計測器は点群だけを読み、姿勢・欠陥真値を読まない。
"""
from lighthouse_vfactory_cli import main
if __name__ == "__main__": raise SystemExit(main("bevel"))
