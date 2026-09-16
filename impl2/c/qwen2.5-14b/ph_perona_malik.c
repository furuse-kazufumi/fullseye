#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺の境界をどのように扱うか: ここでは、境界の値をそのまま使用する。
    // これは、境界の値が入力画像の範囲内にあると仮定している。

    // パラメータの初期化
    int steps = (int)(a * 100); // つまみ a から反復回数を計算
    double k = b; // つまみ b がエッジのしきい値 k として直接使用

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // Perona-Malik の非等方拡散の適用
    for (int step = 0; step < steps; step++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 各方向の勾配の計算
                double dx = (x < w - 1) ? in[y * w + x + 1] - in[y * w + x] : 0;
                double dy = (y < h - 1) ? in[(y + 1) * w + x] - in[y * w + x] : 0;

                // Perona-Malik の伝導率 g(s)
                double g = 1 / (1 + pow(sqrt(dx * dx + dy * dy) / k, 2));

                // 各方向の拡散項の計算
                double diffusion_x = g * dx;
                double diffusion_y = g * dy;

                // 出力画像の更新
                temp[y * w + x] = in[y * w + x] + diffusion_x + diffusion_y;
            }
        }
        // 一時的な画像を出力画像にコピー
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] = temp[y * w + x];
            }
        }
        free(temp);
    }
}
