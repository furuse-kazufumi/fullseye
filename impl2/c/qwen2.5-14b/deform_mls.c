#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int grid_size = 5; // 5x5 のグリッド
    const double amp = 0.12 * a * fmin(h, w); // 振幅
    const double alpha = 0.5 + 1.5 * b; // 重みの減衰

    // 5x5 のグリッド上の制御点の座標を計算
    double grid[grid_size * grid_size * 2];
    for (int i = 0; i < grid_size; ++i) {
        for (int j = 0; j < grid_size; ++j) {
            int idx = (i * grid_size + j) * 2;
            grid[idx] = (i + 0.5) / grid_size; // x 座標
            grid[idx + 1] = (j + 0.5) / grid_size; // y 座標
        }
    }

    // 各ピクセルに対して重み付き最小二乗法を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double px = x / (w - 1.0); // 正規化された x 座標
            double py = y / (h - 1.0); // 正規化された y 座標

            // 各制御点に対する重みを計算
            double weights[grid_size * grid_size];
            for (int i = 0; i < grid_size * grid_size; ++i) {
                double dx = px - grid[i * 2];
                double dy = py - grid[i * 2 + 1];
                weights[i] = 1.0 / pow(dx * dx + dy * dy, alpha);
            }

            // 重み付き最小二乗法を適用
            double sum_weights = 0.0;
            double sum_x = 0.0;
            double sum_y = 0.0;
            for (int i = 0; i < grid_size * grid_size; ++i) {
                sum_weights += weights[i];
                sum_x += grid[i * 2] * weights[i];
                sum_y += grid[i * 2 + 1] * weights[i];
            }
            double wx = sum_x / sum_weights;
            double wy = sum_y / sum_weights;

            // 新しい座標を計算
            double qx = wx + amp * sin(2 * M_PI * px);
            double qy = wy + amp * cos(2 * M_PI * py);

            // 新しい座標から出力画像のピクセルを取得
            int qx_int = (int)qx;
            int qy_int = (int)qy;
            if (qx_int >= 0 && qx_int < w && qy_int >= 0 && qy_int < h) {
                out[y * w + x] = in[qy_int * w + qx_int];
            } else {
                // 範囲外の場合は、端のピクセルをコピー
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
