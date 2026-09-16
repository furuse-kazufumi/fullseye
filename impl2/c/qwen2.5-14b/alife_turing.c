#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double Da = 0.02;
    const double Dh = 0.15 + 1.05 * a;
    const double mu_a = 0.5;
    const double mu_h = 0.5;
    const double rho = 1.0;
    const double rho0 = 0.1;
    const int T = 5 + (int)(25 * b);

    // テンポラリ配列の確保
    double *A = (double*)malloc(h * w * sizeof(double));
    double *H = (double*)malloc(h * w * sizeof(double));
    double *temp = (double*)malloc(h * w * sizeof(double));

    // 初期化
    for (int i = 0; i < h * w; i++) {
        A[i] = in[i];
        H[i] = 1.0; // 初期抑制レベル
    }

    // ラプラシアンの計算用関数
    void laplacian(const double* in, double* out, int h, int w) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double lap = -4 * in[idx];
                lap += in[(y - 1 + h) % h * w + (x + w) % w]; // 上
                lap += in[(y + 1 + h) % h * w + (x + w) % w]; // 下
                lap += in[y * w + (x - 1 + w) % w];            // 左
                lap += in[y * w + (x + 1 + w) % w];            // 右
                out[idx] = lap;
            }
        }
    }

    // シミュレーションの実行
    for (int t = 0; t < T; t++) {
        // A の更新
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double lap_A = laplacian(A, temp, h, w)[idx];
                A[idx] = Da * lap_A + rho * pow(A[idx], 2) / H[idx] - mu_a * A[idx] + rho0;
            }
        }

        // H の更新
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double lap_H = laplacian(H, temp, h, w)[idx];
                H[idx] = Dh * lap_H + rho * pow(A[idx], 2) - mu_h * H[idx];
            }
        }
    }

    // 最終的な A の値を出力にコピー
    for (int i = 0; i < h * w; i++) {
        out[i] = A[i];
    }

    // メモリの解放
    free(A);
    free(H);
    free(temp);
}
