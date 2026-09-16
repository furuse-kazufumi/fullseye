#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理: 入力画像の端を重複させて折り返す
    // これは、入力画像の端を周辺のピクセル値で埋める方法を採用しています。
    // これは仕様書で明示的に指定されていないため、この方法を選択しました。

    // ガウシアンフィルタのシグマを計算
    double sigma = 0.5 + 2.5 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(3 * sigma);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを計算
    double kernel[kernel_size];
    double sum = 0.0;
    for (int i = 0; i < kernel_size; i++) {
        double x = (i - kernel_size / 2) * 1.0;
        kernel[i] = exp(-x * x / (2 * sigma * sigma)) / (sqrt(2 * M_PI) * sigma);
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

    // ガウシアンフィルタリングを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double filtered_value = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の処理: 入力画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    filtered_value += in[ny * w + nx] * kernel[ky + kernel_size / 2] * kernel[kx + kernel_size / 2];
                }
            }
            out[y * w + x] = filtered_value;
        }
    }
}
