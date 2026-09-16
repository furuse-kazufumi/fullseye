#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ボカシ半径と強調量を計算
    int radius = 1 + 4 * a;
    int percent = 50 + 200 * b;

    // 画像の端を処理する際の境界外ピクセルの処理
    // 端のピクセルは同じ端のピクセルとみなす
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            int count = 0;

            // 端のピクセルを考慮して、周囲のピクセルを取得
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;
                    sum += in[ny * w + nx];
                    ++count;
                }
            }

            // 平均値を計算
            double avg = sum / count;

            // 強調量を適用
            double diff = in[y * w + x] - avg;
            double enhanced = in[y * w + x] + diff * percent / 100.0;

            // 出力画像に書き込み
            out[y * w + x] = enhanced;
        }
    }
}
