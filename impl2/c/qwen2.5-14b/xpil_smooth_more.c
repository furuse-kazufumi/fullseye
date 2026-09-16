void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 5x5 カーネルの重み
    const int kernel[5][5] = {
        {1, 1, 1, 1, 1},
        {1, 5, 5, 5, 1},
        {1, 5, 44, 5, 1},
        {1, 5, 5, 5, 1},
        {1, 1, 1, 1, 1}
    };

    // 出力画像の各画素を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            int count = 0;

            // カーネルを適用
            for (int ky = -2; ky <= 2; ++ky) {
                for (int kx = -2; kx <= 2; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 画像の範囲外はスキップ
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    // 重みを加算
                    sum += in[ny * w + nx] * kernel[ky + 2][kx + 2];
                    count += kernel[ky + 2][kx + 2];
                }
            }

            // 重みの合計で割る
            out[y * w + x] = sum / count;
        }
    }
}
