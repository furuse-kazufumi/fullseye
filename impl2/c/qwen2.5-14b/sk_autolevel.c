#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a は局所窓の半径を制御します。つまみ b は未使用です。
    int radius = (int)(a * 3 + 0.5); // つまみ a を 0 から 1 の範囲で 1 から 4 に変換
    if (radius < 1) radius = 1; // 最小半径は 1 に設定
    if (radius > 4) radius = 4; // 最大半径は 4 に設定

    // 局所窓のサイズを計算
    int window_size = 2 * radius + 1;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 局所オートレベル処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 局所窓内の最小値と最大値を計算
            double min_val = 1.0;
            double max_val = 0.0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val < min_val) min_val = val;
                        if (val > max_val) max_val = val;
                    }
                }
            }

            // 最小値と最大値が等しい場合、ノイズを避けるために 0 に設定
            if (min_val == max_val) {
                out[y * w + x] = 0.0;
            } else {
                // 画素値を 0 から 255 の範囲に引き伸ばす
                double val = in[y * w + x];
                out[y * w + x] = (val - min_val) / (max_val - min_val) * 255.0;
            }
        }
    }
}
