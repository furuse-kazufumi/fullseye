#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // スケールパラメータの計算
    double sigma = 0.5 + 2.5 * a;

    // 2次微分のカーネルの計算
    double dx2 = 1.0 / (sigma * sigma);
    double dxy = -1.0 / (sigma * sigma);
    double dy2 = 1.0 / (sigma * sigma);

    // Hessian行列の各要素のカーネル
    double kernel[3][3] = {
        {dx2, dxy, dx2},
        {dxy, dy2, dxy},
        {dx2, dxy, dx2}
    };

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // Hessian行列式の計算
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double dxx = 0.0, dyy = 0.0, dxy = 0.0;

            // Hessian行列の各要素の計算
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    double value = in[iy * w + ix];
                    dxx += value * kernel[ky + 1][kx + 1];
                    if (kx != 0) {
                        dxy += value * kernel[ky + 1][kx + 1];
                    }
                    if (ky != 0) {
                        dyy += value * kernel[ky + 1][kx + 1];
                    }
                }
            }

            // Hessian行列式の計算
            double det = dxx * dyy - dxy * dxy;

            // 出力画像への書き込み
            out[y * w + x] = det;
        }
    }

    // 出力画像の正規化
    double max_val = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] > max_val) {
                max_val = out[y * w + x];
            }
        }
    }
    if (max_val > 0.0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] /= max_val;
            }
        }
    }
}
