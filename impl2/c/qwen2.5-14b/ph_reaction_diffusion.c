#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double Du = 0.22; // u の拡散係数
    const double Dv = 0.06; // v の拡散係数
    const double F = 0.055; // 反応項の係数
    const double kappa = 0.062; // 消滅項の係数
    const double dt = 1.0; // 時間ステップ
    const double dx = 1.0; // 空間ステップ

    // 辺の境界値を決定
    // ここでは、境界値を入力画像の端の値をコピーするようにする。
    // これは、境界条件が周期的であると仮定していることに対応する。
    // 他の選択肢としては、境界値を固定値に設定することも可能である。

    // 一時的な配列を確保
    double *u = (double*)malloc(h * w * sizeof(double));
    double *v = (double*)malloc(h * w * sizeof(double));
    double *u_next = (double*)malloc(h * w * sizeof(double));
    double *v_next = (double*)malloc(h * w * sizeof(double));

    // 初期化
    for (int i = 0; i < h * w; i++) {
        u[i] = in[i];
        v[i] = 1.0 - in[i];
    }

    // 反応拡散モデルの計算
    for (int t = 0; t < 100; t++) { // 100ステップで計算
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                int idx = y * w + x;
                double lap_u = (u[idx - w] + u[idx + w] + u[idx - 1] + u[idx + 1] - 4 * u[idx]) / (dx * dx);
                double lap_v = (v[idx - w] + v[idx + w] + v[idx - 1] + v[idx + 1] - 4 * v[idx]) / (dx * dx);
                u_next[idx] = u[idx] + dt * (Du * lap_u - u[idx] * v[idx] * v[idx] + F * (1 - u[idx]));
                v_next[idx] = v[idx] + dt * (Dv * lap_v + u[idx] * v[idx] * v[idx] - (F + kappa) * v[idx]);
            }
        }

        // 辺の境界値をコピー
        for (int x = 0; x < w; x++) {
            u_next[x] = u[x];
            u_next[(h - 1) * w + x] = u[(h - 1) * w + x];
            v_next[x] = v[x];
            v_next[(h - 1) * w + x] = v[(h - 1) * w + x];
        }
        for (int y = 0; y < h; y++) {
            u_next[y * w] = u[y * w];
            u_next[y * w + w - 1] = u[y * w + w - 1];
            v_next[y * w] = v[y * w];
            v_next[y * w + w - 1] = v[y * w + w - 1];
        }

        // 配列の更新
        for (int i = 0; i < h * w; i++) {
            u[i] = u_next[i];
            v[i] = v_next[i];
        }
    }

    // 最終的な出力を計算
    for (int i = 0; i < h * w; i++) {
        out[i] = v[i] / (1.0 + v[i]); // 正規化
    }

    // メモリの解放
    free(u);
    free(v);
    free(u_next);
    free(v_next);
}
