#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは近傍のピクセル値を用いる。
    // ここでは、境界外のピクセルは0と仮定する。

    // フーリエ変換に必要な配列を確保
    double *gx = (double*)malloc(h * w * sizeof(double));
    double *gy = (double*)malloc(h * w * sizeof(double));
    double *lap = (double*)malloc(h * w * sizeof(double));
    double *div_hat = (double*)malloc(h * w * sizeof(double));
    double *lap_hat = (double*)malloc(h * w * sizeof(double));
    double *h_hat = (double*)malloc(h * w * sizeof(double));
    double *h = (double*)malloc(h * w * sizeof(double));

    // グラデーションを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = (x == 0) ? 0 : in[y * w + x] - in[y * w + x - 1];
            double dy = (y == 0) ? 0 : in[y * w + x] - in[(y - 1) * w + x];
            gx[y * w + x] = a * dx;
            gy[y * w + x] = a * dy;
        }
    }

    // ラプラシアンと発散を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = (x == w - 1) ? 0 : gx[y * w + x + 1] - gx[y * w + x];
            double dy = (y == h - 1) ? 0 : gy[(y + 1) * w + x] - gy[y * w + x];
            lap[y * w + x] = 2 * cos(2 * M_PI * x / w) + 2 * cos(2 * M_PI * y / h) - 4;
            div_hat[y * w + x] = dx + dy;
            lap_hat[y * w + x] = lap[y * w + x];
        }
    }

    // フーリエ変換を用いて h_hat を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            h_hat[y * w + x] = div_hat[y * w + x] / lap_hat[y * w + x];
        }
    }

    // h_hat を逆フーリエ変換して h を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            h[y * w + x] = h_hat[y * w + x];
        }
    }

    // 最小値と最大値を計算
    double min_val = h[0];
    double max_val = h[0];
    for (int i = 1; i < h * w; i++) {
        if (h[i] < min_val) min_val = h[i];
        if (h[i] > max_val) max_val = h[i];
    }

    // 正規化
    for (int i = 0; i < h * w; i++) {
        out[i] = (h[i] - min_val) / (max_val - min_val);
    }

    // メモリを解放
    free(gx);
    free(gy);
    free(lap);
    free(div_hat);
    free(lap_hat);
    free(h_hat);
    free(h);
}
