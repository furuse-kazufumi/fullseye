#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * (w + h) / 2); // 窓サイズは a によって決まる
    window_size = window_size > 0 ? window_size : 1; // 窓サイズが 0 以下なら 1 に

    // ε の設定
    double epsilon = b; // b が ε に相当

    // メンバと標準偏差の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            // 窓内のピクセルを取得
            for (int dy = -window_size; dy <= window_size; dy++) {
                for (int dx = -window_size; dx <= window_size; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;
                    // 端の処理: 端画素を重複させて折り返す
                    if (nx < 0) nx = -nx;
                    if (ny < 0) ny = -ny;
                    if (nx >= w) nx = 2 * w - nx - 2;
                    if (ny >= h) ny = 2 * h - ny - 2;
                    sum += in[ny * w + nx];
                    count++;
                }
            }
            double mean = sum / count;
            double variance = 0.0;
            for (int dy = -window_size; dy <= window_size; dy++) {
                for (int dx = -window_size; dx <= window_size; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;
                    if (nx < 0) nx = -nx;
                    if (ny < 0) ny = -ny;
                    if (nx >= w) nx = 2 * w - nx - 2;
                    if (ny >= h) ny = 2 * h - ny - 2;
                    double diff = in[ny * w + nx] - mean;
                    variance += diff * diff;
                }
            }
            variance /= count;
            double std_dev = sqrt(variance);
            // 出力の計算
            out[y * w + x] = (in[y * w + x] - mean) / (std_dev + epsilon);
            // 出力を [0, 1] の範囲に収める
            if (out[y * w + x] < 0) out[y * w + x] = 0;
            if (out[y * w + x] > 1) out[y * w + x] = 1;
        }
    }
}
