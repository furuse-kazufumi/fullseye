#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は窓の一辺を {3,5,7,9} で振る。b は未使用。
    int window_size = (int)(a * 4 + 1); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    window_size = (window_size % 2 == 0) ? window_size + 1 : window_size; // 奇数に保つ

    // 窓サイズが画像サイズを超える場合は、窓サイズを画像サイズに合わせる
    if (window_size > h) window_size = h;
    if (window_size > w) window_size = w;

    // 窓の半径
    int r = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 各ピクセルの局所的な標準偏差を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 窓内のピクセルを処理
            for (int dy = -r; dy <= r; dy++) {
                for (int dx = -r; dx <= r; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の境界外を処理するための補間
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        sum += pixel;
                        sum_sq += pixel * pixel;
                        count++;
                    }
                }
            }

            // 平均と分散を計算
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            double std_dev = sqrt(variance);

            // 出力画像に標準偏差を設定
            out[y * w + x] = std_dev;
        }
    }

    // 出力画像を最大値で正規化
    double max_val = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] > max_val) {
                max_val = out[y * w + x];
            }
        }
    }
    if (max_val > 0.0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] /= max_val;
            }
        }
    }
}
