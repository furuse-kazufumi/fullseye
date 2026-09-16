#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 2 * (int)(a * 6) + 3;
    int half_window = window_size / 2;

    // 画像の端を処理するためのパディング
    // ここでは端の値を 0 でパディングする
    int padded_h = h + 2 * half_window;
    int padded_w = w + 2 * half_window;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));

    // 元の画像をパディングされた画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + half_window) * padded_w + (x + half_window)] = in[y * w + x];
        }
    }

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // Sauvola のアルゴリズムの実装
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 局所窓内の平均と標準偏差の計算
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int py = y + dy + half_window;
                    int px = x + dx + half_window;
                    double val = padded_in[py * padded_w + px];
                    sum += val;
                    sum_sq += val * val;
                    count++;
                }
            }

            double mean = sum / count;
            double std_dev = sqrt((sum_sq / count) - (mean * mean));

            // Sauvola のしきい値の計算
            double threshold = mean * (1.0 + (std_dev / (mean + 1e-6)));

            // 二値化処理
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // メモリの解放
    free(padded_in);
}
