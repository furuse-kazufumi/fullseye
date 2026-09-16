#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の半径を計算
    int radius = (int)(a * 5 + 0.5); // 0.5 は丸め誤差を補正する
    radius = fmax(1, fmin(radius, 5)); // 半径は 1 から 5 の間

    // 出力画像を入力画像と同じにする
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 膨張処理
    for (int r = 1; r <= radius; ++r) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double max_val = in[y * w + x];
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            max_val = fmax(max_val, in[ny * w + nx]);
                        }
                    }
                }
                out[y * w + x] = max_val;
            }
        }
    }

    // 収縮処理
    for (int r = 1; r <= radius; ++r) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double min_val = out[y * w + x];
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            min_val = fmin(min_val, out[ny * w + nx]);
                        }
                    }
                }
                out[y * w + x] = min_val;
            }
        }
    }

    // 出力を [0,1] にクリップ
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = fmax(0.0, fmin(1.0, out[y * w + x]));
        }
    }
}
