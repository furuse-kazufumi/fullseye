#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の扱い: 端画素を重複させて折り返す (reflect)
    // これは、ガウシアンフィルタを適用する際に端の画素を適切に処理するために必要です。
    // 画像の端を処理するための補間関数を定義します。
    double interpolate(const double* img, int h, int w, int y, int x) {
        if (y < 0) y = -y - 1;
        if (y >= h) y = 2 * h - y - 1;
        if (x < 0) x = -x - 1;
        if (x >= w) x = 2 * w - x - 1;
        return img[y * w + x];
    }

    // ガウシアンフィルタのシグマを計算
    double sigma = 0.3 + 2.7 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(3 * sigma);
    if (kernel_size % 2 == 0) kernel_size++; // カーネルサイズは奇数でなければならない

    // ガウシアンカーネルを計算
    double kernel[kernel_size * kernel_size];
    double sum = 0.0;
    for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
        for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
            double distance = sqrt(kx * kx + ky * ky);
            kernel[(ky + kernel_size / 2) * kernel_size + kx + kernel_size / 2] = exp(-0.5 * (distance / sigma) * (distance / sigma));
            sum += kernel[(ky + kernel_size / 2) * kernel_size + kx + kernel_size / 2];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // ガウシアンフィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    value += kernel[(ky + kernel_size / 2) * kernel_size + kx + kernel_size / 2] * interpolate(in, h, w, y + ky, x + kx);
                }
            }
            out[y * w + x] = value;
        }
    }
}
