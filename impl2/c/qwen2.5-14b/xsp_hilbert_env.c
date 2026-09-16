#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        // 行方向のヒルベルト変換の結果を格納する一時配列
        double hilbert_result[w];
        // 行を [-0.5, 0.5] に平行移動
        for (int x = 0; x < w; x++) {
            hilbert_result[x] = in[y * w + x] - 0.5;
        }

        // 1次元ヒルベルト変換の実装
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            // 周期的な境界条件を適用
            for (int k = 0; k < w; k++) {
                int idx = (x - k + w) % w; // 周期的なインデックス
                sum += hilbert_result[idx] * sin(M_PI * k / w);
            }
            out[y * w + x] = fabs(sum) / w; // 瞬時振幅を正規化
        }
    }
}
