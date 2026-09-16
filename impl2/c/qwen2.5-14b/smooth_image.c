#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の処理は、入力画像の端を重複させて折り返す (reflect) とします。
    // これは仕様書で指定されている端の扱いです。

    // ガウシアンフィルタのシグマを計算
    double sigma = 0.5 + 2.0 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(3 * sigma);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを計算
    double kernel[kernel_size];
    double sum = 0.0;
    for (int i = 0; i < kernel_size; i++) {
        int x = i - kernel_size / 2;
        kernel[i] = exp(-(x * x) / (2 * sigma * sigma));
        sum += kernel[i];
    }
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // ガウシアンフィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の処理
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    sum += in[ny * w + nx] * kernel[ky + kernel_size / 2] * kernel[kx + kernel_size / 2];
                }
            }
            out[y * w + x] = sum;
        }
    }
}
