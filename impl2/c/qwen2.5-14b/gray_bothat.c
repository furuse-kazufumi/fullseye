#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、つまみ b は無視する。つまみ a は {0.1, 0.5, 0.9} の範囲で効果があると想定。
    // つまみ a が 0.1, 0.5, 0.9 のとき、構造要素のサイズは {3, 5, 7} となる。
    // つまみ a が 0.25, 0.49, 0.75 で効果が切り替わるとの情報から、
    // つまみ a は 0.1 から 0.9 まで 0.2 の間隔で効果があると仮定する。
    // つまみ a が 0.1 から 0.9 以外の値の場合、最も近い 0.1, 0.3, 0.5, 0.7, 0.9 のいずれかに丸める。
    int kernel_size = (a < 0.3) ? 3 : (a < 0.7) ? 5 : 7;

    // ブラックトップハット変換はクロージングと元画像の差分を計算する。
    // ここでは単純な矩形構造要素を用いてクロージングを実装する。
    // 画像の端は境界値を用いる。

    // クロージングの結果を格納する一時的な画像
    double* closing = (double*)malloc(h * w * sizeof(double));
    if (closing == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // クロージングの実装
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, in[ny * w + nx]);
                    } else {
                        // 画像の端の場合、境界値を用いる
                        max_val = fmax(max_val, in[y * w + x]);
                    }
                }
            }
            closing[y * w + x] = max_val;
        }
    }

    // ブラックトップハット変換の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = closing[y * w + x] - in[y * w + x];
        }
    }

    // 画像の最大値で正規化
    double max_out = 0.0;
    for (int i = 0; i < h * w; i++) {
        max_out = fmax(max_out, out[i]);
    }
    if (max_out > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_out;
        }
    }

    // メモリ解放
    free(closing);
}
