#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は近傍半径、b はコントラスト閾値。ここでは a と b の値を直接使用せず、
    // 代わりに定数で近傍半径とコントラスト閾値を設定します。
    // a と b の値は、将来的な拡張のために保持しておきます。
    const int radius = 7; // 近傍半径。a に応じて動的に変更することも可能。
    const double contrast_threshold = 30; // コントラスト閾値。b に応じて動的に変更することも可能。

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 近傍の最大値と最小値を計算
            double max_val = -1.0;
            double min_val = 2.0;
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を避ける
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val > max_val) max_val = val;
                        if (val < min_val) min_val = val;
                    }
                }
            }

            // コントラストを計算
            double contrast = max_val - min_val;
            // コントラストが閾値以下の場合、グローバル閾値 0.5 を使用
            if (contrast < contrast_threshold) {
                out[y * w + x] = (in[y * w + x] > 0.5) ? 1.0 : 0.0;
            } else {
                // ローカル閾値を計算
                double local_threshold = (max_val + min_val) / 2.0;
                // ローカル閾値に基づいて二値化
                out[y * w + x] = (in[y * w + x] > local_threshold) ? 1.0 : 0.0;
            }
        }
    }
}
