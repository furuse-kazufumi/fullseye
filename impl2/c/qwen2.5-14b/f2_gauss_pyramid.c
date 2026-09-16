#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は無視する
    (void)b;

    // ピラミッドのレベルを決定
    int level = (int)(a * 4 + 0.5); // 0.17, 0.49, 0.83 で切り替わるため、0.17 から 0.83 までの範囲を 4 つのレベルに分割
    if (level < 1) level = 1;
    if (level > 4) level = 4;

    // ピラミッドのレベルに応じた処理
    for (int l = 0; l < level; ++l) {
        int h2 = h >> l;
        int w2 = w >> l;
        double* tmp = (double*)malloc(h2 * w2 * sizeof(double));

        // ブラーとダウンサンプリング
        for (int y = 0; y < h2; ++y) {
            for (int x = 0; x < w2; ++x) {
                double sum = 0.0;
                int count = 0;
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        int y2 = y * 2 + dy;
                        int x2 = x * 2 + dx;
                        if (y2 >= 0 && y2 < h && x2 >= 0 && x2 < w) {
                            sum += in[y2 * w + x2];
                            ++count;
                        }
                    }
                }
                tmp[y * w2 + x] = sum / count;
            }
        }

        // テンポラリを解放
        if (l < level - 1) {
            free(tmp);
        } else {
            // 最終レベルの場合は出力にコピー
            for (int y = 0; y < h2; ++y) {
                for (int x = 0; x < w2; ++x) {
                    out[y * w + x] = tmp[y * w2 + x];
                }
            }
            free(tmp);
        }
    }
}
