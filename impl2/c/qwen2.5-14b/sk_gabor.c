#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書では端の扱いが明示的に定義されていないが、端の画素を重複させて折り返すとある。
    // これは scipy の reflect モードに相当し、ここではその手法を採用する。

    // Gabor フィルタのパラメータ設定
    double frequency = 0.1 + 0.3 * a;  // 周波数の範囲は 0.1 から 0.4
    double theta = 0;  // 方向は固定で水平方向 (0 ラジアン)

    // Gabor フィルタのカーネルを生成
    // ここでは、Gabor フィルタのカーネルを手動で生成する。
    // 実際の実装では、この部分はライブラリ関数や事前計算されたカーネルを使用する可能性がある。
    int kernel_size = 31;  // カーネルのサイズ (奇数)
    double sigma = 1.0 / (2 * M_PI * frequency);  // ガウスカーネルの標準偏差
    double lambda = 1.0 / frequency;  // 波長
    double gamma = 0.5;  // 方向性のパラメータ
    double psi = 0;  // 位相シフト

    // カーネルの初期化
    double kernel[kernel_size * kernel_size];
    for (int ky = 0; ky < kernel_size; ky++) {
        for (int kx = 0; kx < kernel_size; kx++) {
            int ky_center = (kernel_size - 1) / 2;
            int kx_center = (kernel_size - 1) / 2;
            double ky_pos = ky - ky_center;
            double kx_pos = kx - kx_center;
            double kx_rot = kx_pos * cos(theta) - ky_pos * sin(theta);
            double ky_rot = kx_pos * sin(theta) + ky_pos * cos(theta);
            double g = exp(-(kx_rot * kx_rot + ky_rot * ky_rot * gamma * gamma) / (2 * sigma * sigma));
            double f = cos(2 * M_PI * frequency * kx_rot + psi);
            kernel[ky * kernel_size + kx] = g * f;
        }
    }

    // 画像の各画素に対して Gabor フィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int ky_center = (kernel_size - 1) / 2;
                    int kx_center = (kernel_size - 1) / 2;
                    int y_pos = y + ky - ky_center;
                    int x_pos = x + kx - kx_center;
                    // 端の画素を重複させて折り返す
                    if (y_pos < 0) y_pos = -y_pos - 1;
                    if (y_pos >= h) y_pos = 2 * h - y_pos - 1;
                    if (x_pos < 0) x_pos = -x_pos - 1;
                    if (x_pos >= w) x_pos = 2 * w - x_pos - 1;
                    sum += in[y_pos * w + x_pos] * kernel[ky * kernel_size + kx];
                }
            }
            out[y * w + x] = fabs(sum);
        }
    }

    // 出力を最大値で正規化
    double max_val = 0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) max_val = out[i];
    }
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_val;
    }
}
