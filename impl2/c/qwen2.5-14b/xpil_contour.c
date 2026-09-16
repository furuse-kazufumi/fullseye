void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。固定カーネルを使用する。
    // 画像の端の処理については、端の画素は入力値のまま出力する。
    // 画像の中心画素の計算は 3x3 のカーネルを使用する。
    // カーネルは [-1,-1,-1; -1,8,-1; -1,-1,-1] で、出力は (8*中心 - 8 近傍の和) + 255 を 0〜255 に飽和させる。
    // 入力は [0,1] にクリップして 255 でスケーリングし、出力を 255 でスケーリングして [0,1] に戻す。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (y == 0 || y == h - 1 || x == 0 || x == w - 1) {
                // 画像の端の画素は入力値のまま出力する。
                out[y * w + x] = in[y * w + x];
            } else {
                // 中心画素の計算
                int center = y * w + x;
                int sum = 0;
                // 近傍の和を計算
                for (int ky = -1; ky <= 1; ++ky) {
                    for (int kx = -1; kx <= 1; ++kx) {
                        if (ky == 0 && kx == 0) continue; // 中心画素は除く
                        int nx = x + kx;
                        int ny = y + ky;
                        sum += in[ny * w + nx];
                    }
                }
                // 出力の計算
                int value = (8 * in[center] - sum) + 255;
                // 0〜255 にクリップ
                value = value < 0 ? 0 : (value > 255 ? 255 : value);
                // [0,1] にスケーリング
                out[y * w + x] = value / 255.0;
            }
        }
    }
}
