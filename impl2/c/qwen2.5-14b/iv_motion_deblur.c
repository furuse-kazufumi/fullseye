#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ブラーの長さと角度を計算
    int L = 3 + (int)(a * 10); // ブラーの長さ (3..13 px)
    double theta = b * M_PI; // ブラーの角度 (0..180 deg)

    // PSF (Point Spread Function) を生成
    double psf[L][L];
    for (int i = 0; i < L; i++) {
        for (int j = 0; j < L; j++) {
            psf[i][j] = 0.0;
        }
    }

    // PSF の中心を計算
    int center = (L - 1) / 2;

    // PSF の生成
    for (int i = 0; i < L; i++) {
        for (int j = 0; j < L; j++) {
            double dx = j - center;
            double dy = i - center;
            double dist = sqrt(dx * dx + dy * dy);
            if (dist <= center) {
                psf[i][j] = exp(-dist * dist / (2 * (a * 0.1 + 0.1)));
            }
        }
    }

    // PSF を回転
    double rotated_psf[L][L];
    for (int i = 0; i < L; i++) {
        for (int j = 0; j < L; j++) {
            rotated_psf[i][j] = 0.0;
        }
    }

    for (int i = 0; i < L; i++) {
        for (int j = 0; j < L; j++) {
            double dx = j - center;
            double dy = i - center;
            double x = dx * cos(theta) - dy * sin(theta);
            double y = dx * sin(theta) + dy * cos(theta);
            int x_idx = x + center;
            int y_idx = y + center;
            if (x_idx >= 0 && x_idx < L && y_idx >= 0 && y_idx < L) {
                rotated_psf[i][j] = psf[(int)y_idx][(int)x_idx];
            }
        }
    }

    // Wiener deconvolution を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int i = 0; i < L; i++) {
                for (int j = 0; j < L; j++) {
                    int py = y + i - center;
                    int px = x + j - center;
                    if (py >= 0 && py < h && px >= 0 && px < w) {
                        sum += rotated_psf[i][j] * in[py * w + px];
                    }
                }
            }
            out[y * w + x] = sum;
        }
    }
}
