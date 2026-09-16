void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は円盤半径を決定する。1+int(a*3) で 1〜4 の範囲。
    int radius = 1 + (int)(a * 3);
    int kernel_size = 2 * radius + 1;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 各画素について、近傍の画素を調べて多数決を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 画像の範囲外の画素は無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] > 0.5) {
                            count++;
                        }
                    }
                }
            }
            // 近傍の過半数が 1 なら、出力画像の該当画素を 1 にする
            if (count > (kernel_size * kernel_size) / 2) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
