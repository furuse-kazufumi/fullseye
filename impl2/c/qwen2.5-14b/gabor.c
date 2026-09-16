#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書では端の扱いが明示的に指定されていないため、端の画素を重複させて折り返す方法を採用する。
    // これは scipy の既定の border_mode "reflect" に準拠している。

    // Gabor フィルタのパラメータ設定
    double theta = M_PI * a;  // 方向 θ
    double nu = 0.1 + 0.3 * b;  // 空間周波数 ν

    // Gabor フィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(3.0 / nu);  // 3σ の範囲をカバーする
    kernel_size = kernel_size + 1 - kernel_size % 2;  // カーネルサイズを奇数にする

    // Gabor フィルタのカーネルを生成
    double kernel[kernel_size * kernel_size];
    double sum_kernel = 0.0;
    for (int ky = 0; ky < kernel_size; ky++) {
        for (int kx = 0; kx < kernel_size; kx++) {
            int ky_center = (kernel_size - 1) / 2;
            int kx_center = (kernel_size - 1) / 2;
            double ky_pos = ky - ky_center;
            double kx_pos = kx - kx_center;
            double ky_rot = ky_pos * cos(theta) + kx_pos * sin(theta);
            double kx_rot = -ky_pos * sin(theta) + kx_pos * cos(theta);
            double gabor_value = exp(-0.5 * (nu * nu * (ky_rot * ky_rot + kx_rot * kx_rot) + (kx_rot * kx_rot) / (0.5625 * 0.5625))) * cos(2 * M_PI * nu * ky_rot);
            kernel[ky * kernel_size + kx] = gabor_value;
            sum_kernel += fabs(gabor_value);
        }
    }

    // 画像の各画素に対して Gabor フィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double filtered_value = 0.0;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int ky_center = (kernel_size - 1) / 2;
                    int kx_center = (kernel_size - 1) / 2;
                    int y_pos = y + ky - ky_center;
                    int x_pos = x + kx - kx_center;
                    // 端の画素を重複させて折り返す
                    if (y_pos < 0) y_pos = -y_pos;
                    if (y_pos >= h) y_pos = 2 * h - y_pos - 1;
                    if (x_pos < 0) x_pos = -x_pos;
                    if (x_pos >= w) x_pos = 2 * w - x_pos - 1;
                    filtered_value += in[y_pos * w + x_pos] * kernel[ky * kernel_size + kx];
                }
            }
            out[y * w + x] = filtered_value / sum_kernel;
        }
    }
}
