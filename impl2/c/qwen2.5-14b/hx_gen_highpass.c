#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double cutoff = 0.05 + 0.45 * a;
    const double pi = 3.14159265358979323846;

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // フィルタの生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // DC成分を中心に移動した正規化周波数座標
            double normalized_y = (y + 0.5 - h / 2.0) / (h / 2.0);
            double normalized_x = (x + 0.5 - w / 2.0) / (w / 2.0);

            // 正規化周波数半径
            double r = sqrt(normalized_y * normalized_y + normalized_x * normalized_x);

            // ハイパスフィルタの適用
            if (r > cutoff) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
