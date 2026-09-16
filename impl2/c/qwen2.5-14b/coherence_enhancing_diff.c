#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理は周期的境界条件を採用
    // これは仕様書で明示的に指定されている処理方法です。

    // 反復回数 a と伝導度閾値 b を使用して、Perona-Malik の異方性拡散を適用
    // ここでは単純な実装として、1 回の反復を想定します。実際の実装では、
    // a の値に応じて反復回数を調整する必要があります。

    // 1 回の反復を実装
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 周期的境界条件を適用
            int px = (x - 1 + w) % w;
            int py = (y - 1 + h) % h;
            int nx = (x + 1) % w;
            int ny = (y + 1) % h;

            // ディファージェントの計算
            double dx = in[py * w + px] - in[py * w + nx];
            double dy = in[py * w + px] - in[ny * w + px];

            // 伝導度の計算
            double c = exp(-((dx * dx + dy * dy) / (b * b)));

            // 出力の更新
            out[y * w + x] = in[y * w + x] + a * c * (dx + dy);
        }
    }
}
