#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double Du = 0.16;
    const double Dv = 0.08;
    const double F = 0.02 + 0.06 * a;
    const double K = 0.05 + 0.02 * b;
    const int T = 8 + (int)(20 * a);

    // 一時的な配列を確保
    double *u = (double*)malloc(h * w * sizeof(double));
    double *v = (double*)malloc(h * w * sizeof(double));
    double *lap_u = (double*)malloc(h * w * sizeof(double));
    double *lap_v = (double*)malloc(h * w * sizeof(double));

    // 初期化
    for (int i = 0; i < h * w; i++) {
        u[i] = 1.0 - in[i]; // u は入力画像の補集合
        v[i] = in[i];       // v は入力画像
    }

    // Laplacian 関数
    void laplacian(const double* in, int h, int w, double* out) {
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

    // Gray-Scott モデルの時間発展
    for (int t = 0; t < T; t++) {
        laplacian(u, h, w, lap_u);
        laplacian(v, h, w, lap_v);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double lap_u_val = lap_u[idx];
                double lap_v_val = lap_v[idx];
                double u_val = u[idx];
                double v_val = v[idx];

                // u の更新
                u[idx] += Du * lap_u_val - u_val * v_val * v_val + F * (1.0 - u_val);
                // v の更新
                v[idx] += Dv * lap_v_val + u_val * v_val * v_val - (F + K) * v_val;
            }
        }
    }

    // 出力画像を生成
    for (int i = 0; i < h * w; i++) {
        out[i] = v[i]; // v の値を出力画像にコピー
    }

    // メモリを解放
    free(u);
    free(v);
    free(lap_u);
    free(lap_v);
}
