#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数の計算
    double mu = 0.08 + 0.25 * a;
    double sigma = 0.03 + 0.05 * a;
    double dt = 0.10 + 0.15 * a;
    int steps = 1 + (int)(19 * b);

    // ガウシアンカーネルのパラメータ
    double R = 1.0; // パラメータ R は固定値として 1.0 を使用
    double K_radius = 0.5; // ガウシアンカーネルのピーク位置

    // 画像の端を周期境界条件で処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double u = in[y * w + x];
            double U = 0.0;

            // U の計算
            for (int dy = -R; dy <= R; ++dy) {
                for (int dx = -R; dx <= R; ++dx) {
                    double r = sqrt(dx * dx + dy * dy);
                    double K = exp(-0.5 * ((r - K_radius) / R) * ((r - K_radius) / R));
                    U += K * in[(y + dy + h) % h * w + (x + dx + w) % w];
                }
            }

            // G(U) の計算
            double GU = 2 * exp(-pow(U - mu, 2) / (2 * sigma * sigma)) - 1;

            // u の更新
            u += dt * GU;
            u = fmax(0.0, fmin(1.0, u)); // u のクリッピング

            // 出力画像に書き込み
            out[y * w + x] = u;
        }
    }
}
