#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓の一辺の長さを計算 (a は [0, 1] の範囲で、3 から 9 にマッピング)
    int window_size = (int)(3 + 6 * a);
    if (window_size % 2 == 0) window_size++; // 奇数に調整

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像を初期化
    memset(out, 0, sizeof(double) * h * w);

    // 各ピクセルについて処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 窓内のピクセルについて処理
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界外のピクセルは無視 (ゼロパディング)
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
            double stddev = sqrt(variance);

            // 出力に標準偏差を代入
            out[y * w + x] = stddev;
        }
    }

    // 出力を正規化 (最大値で割る)
    double max_stddev = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_stddev) {
            max_stddev = out[i];
        }
    }

    if (max_stddev > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_stddev;
        }
    }
}
