#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は [-1, 1] に正規化
    double dy = (a - 0.5) * 2.0;
    double dx = (b - 0.5) * 2.0;

    // 出力画像の各画素を設定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 平行移動後の座標を計算
            int ny = y + dy;
            int nx = x + dx;

            // 座標が画像の範囲外の場合、循環シフトを適用
            if (ny < 0) ny += h;
            if (ny >= h) ny -= h;
            if (nx < 0) nx += w;
            if (nx >= w) nx -= w;

            // 入力画像の値を出力画像にコピー
            out[y * w + x] = in[ny * w + nx];
        }
    }
}
