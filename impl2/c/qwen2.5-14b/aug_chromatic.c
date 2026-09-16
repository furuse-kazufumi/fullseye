#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 高さと幅の確認
    if (h <= 0 || w <= 0) {
        return; // 無効なサイズの場合は何もしない
    }

    // ガウシアンフィルタのパラメータ
    const int gaussian_radius = 1;
    const double gaussian_sigma = 1.0;

    // ガウシアンフィルタのカーネルを計算
    double gaussian_kernel[3 * 3];
    for (int ky = -gaussian_radius; ky <= gaussian_radius; ++ky) {
        for (int kx = -gaussian_radius; kx <= gaussian_radius; ++kx) {
            double distance = sqrt(kx * kx + ky * ky);
            gaussian_kernel[(ky + gaussian_radius) * 3 + (kx + gaussian_radius)] = exp(-distance * distance / (2 * gaussian_sigma * gaussian_sigma));
        }
    }

    // ガウシアンフィルタを適用
    double gaussian_filtered[h * w];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -gaussian_radius; ky <= gaussian_radius; ++ky) {
                for (int kx = -gaussian_radius; kx <= gaussian_radius; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx] * gaussian_kernel[(ky + gaussian_radius) * 3 + (kx + gaussian_radius)];
                    }
                }
            }
            gaussian_filtered[y * w + x] = sum;
        }
    }

    // エッジ強調フィルタを適用
    double edge_highlighted[h * w];
    int shift = 1 + (int)(4 * a);
    double edge_amplitude = 0.1 + 0.9 * b;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double edge = in[y * w + x] - gaussian_filtered[y * w + x];
            int nx = x + shift;
            if (nx >= 0 && nx < w) {
                edge_highlighted[y * w + x] = in[y * w + x] + edge_amplitude * edge;
            } else {
                edge_highlighted[y * w + x] = in[y * w + x];
            }
        }
    }

    // 出力画像を設定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = edge_highlighted[y * w + x];
        }
    }
}
