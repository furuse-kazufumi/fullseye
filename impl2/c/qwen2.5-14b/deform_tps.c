#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double amp = 0.15 * a * fmin(h, w); // 幅振幅
    const double freq = 0.5 + 1.5 * b;        // 周波数
    const int grid_size = 5;                   // グリッドサイズ (5x5)
    const int grid_half = grid_size / 2;       // グリッドの半分

    // グリッド上のコントロールポイントの座標を計算
    double control_points[grid_size * grid_size * 2];
    for (int y = 0; y < grid_size; ++y) {
        for (int x = 0; x < grid_size; ++x) {
            int idx = (y * grid_size + x) * 2;
            double nx = (x - grid_half) / (grid_half * 2.0);
            double ny = (y - grid_half) / (grid_half * 2.0);
            control_points[idx] = nx;
            control_points[idx + 1] = ny;
        }
    }

    // コントロールポイントを動かす
    for (int i = 0; i < grid_size * grid_size; ++i) {
        int idx = i * 2;
        double nx = control_points[idx];
        double ny = control_points[idx + 1];
        double dx = amp * sin(2 * M_PI * freq * nx);
        double dy = amp * cos(2 * M_PI * freq * ny);
        control_points[idx] += dx;
        control_points[idx + 1] += dy;
    }

    // 画像の各ピクセルに対して変形を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double src_x = x;
            double src_y = y;
            // バックワードマップを適用
            for (int cy = 0; cy < grid_size; ++cy) {
                for (int cx = 0; cx < grid_size; ++cx) {
                    int idx = (cy * grid_size + cx) * 2;
                    double nx = control_points[idx];
                    double ny = control_points[idx + 1];
                    double dx = nx - (cx - grid_half) / (grid_half * 2.0);
                    double dy = ny - (cy - grid_half) / (grid_half * 2.0);
                    double r = sqrt(dx * dx + dy * dy);
                    double t = r * r * log(r + 1e-6);
                    src_x += t * (x - cx + grid_half);
                    src_y += t * (y - cy + grid_half);
                }
            }
            // ビリニア補間で出力画像を生成
            int x1 = (int)floor(src_x);
            int y1 = (int)floor(src_y);
            int x2 = x1 + 1;
            int y2 = y1 + 1;
            double u = src_x - x1;
            double v = src_y - y1;
            double w11 = (1 - u) * (1 - v);
            double w12 = u * (1 - v);
            double w21 = (1 - u) * v;
            double w22 = u * v;
            double value = w11 * in[y1 * w + x1] + w12 * in[y1 * w + x2] +
                           w21 * in[y2 * w + x1] + w22 * in[y2 * w + x2];
            out[y * w + x] = value;
        }
    }
}
