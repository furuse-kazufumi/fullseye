"""仮想工場のSMT AOI検査。

外から来るもの: WEF 2023 AI版の不良率99%減、既存solder_fillet_aoiの3色照明。
自作: 5欠陥の外観像、固定閾値基準、探索・holdout評価。
門: 検出器は画像以外を受け取らず、乱数で判定しない。
"""
from lighthouse_vfactory_cli import main
if __name__ == "__main__": raise SystemExit(main("smt"))
