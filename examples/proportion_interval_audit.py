"""小標本の検出率と誤警報率を、点推定だけでなく片側信頼限界で報告する。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs


def main():
    detected = fs.ledger.proportion_interval(10, 10, sides="lower")
    false_calls = fs.ledger.proportion_interval(0, 20, sides="upper")
    required = fs.ledger.trials_for_all_success(0.90)
    print("10/10 detection: estimate=%.3f, 95%% lower=%.4f" %
          (detected["estimate"], detected["lower"]))
    print("0/20 false calls: estimate=%.3f, 95%% upper=%.4f" %
          (false_calls["estimate"], false_calls["upper"]))
    print("POD >= 0.90 at one-sided 95%% confidence requires %d/%d" %
          (required, required))


if __name__ == "__main__":
    main()
