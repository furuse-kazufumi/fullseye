#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int steps = 1 + (int)(29 * a); // ステップ数
    const double dt = 0.05 + 0.2 * b;    // 時間ステップ
    const double eps = 1e-6;             // 小数の閾値

    // テンポラリ配列の確保
    double *u = (double*)malloc(h * w * sizeof(double));
    double *ux = (double*)malloc(h * w * sizeof(double));
    double *uy = (double*)malloc(h * w * sizeof(double));
    double *uxx = (double*)malloc(h * w * sizeof(double));
    double *uyy = (double*)malloc(h * w * sizeof(double));
    double *uxy = (double*)malloc(h * w * sizeof(double));
    double *div = (double*)malloc(h * w * sizeof(double));

    // 初期化
    for (int i = 0; i < h * w; i++) {
        u[i] = in[i];
    }

    // ステップの繰り返し
    for (int step = 0; step < steps; step++) {
        // u_x, u_y の計算
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                int idx_left = (x - 1 + w) % w + y * w;
                int idx_right = (x + 1) % w + y * w;
                int idx_up = (y - 1 + h) % h * w + x;
                int idx_down = (y + 1) % h * w + x;

                ux[idx] = (u[idx_right] - u[idx_left]) / 2.0;
                uy[idx] = (u[idx_down] - u[idx_up]) / 2.0;
            }
        }

        // u_xx, u_yy, u_xy の計算
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                int idx_left = (x - 1 + w) % w + y * w;
                int idx_right = (x + 1) % w + y * w;
                int idx_up = (y - 1 + h) % h * w + x;
                int idx_down = (y + 1) % h * w + x;

                uxx[idx] = (ux[idx_right] - ux[idx_left]) / 2.0;
                uyy[idx] = (uy[idx_down] - uy[idx_up]) / 2.0;
                uxy[idx] = (uy[idx_right] - uy[idx_left]) / 2.0;
            }
        }

        // div の計算
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                div[idx] = (uxx[idx] * uy[idx] * uy[idx] - 2 * ux[idx] * uxy[idx] * uy[idx] + uyy[idx] * ux[idx] * ux[idx]) / (ux[idx] * ux[idx] + uy[idx] * uy[idx] + eps);
            }
        }

        // u の更新
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                u[idx] += dt * div[idx];
            }
        }
    }

    // 最終的な結果を out にコピー
    for (int i = 0; i < h * w; i++) {
        out[i] = u[i];
    }

    // テンポラリ配列の解放
    free(u);
    free(ux);
    free(uy);
    free(uxx);
    free(uyy);
    free(uxy);
    free(div);
}
