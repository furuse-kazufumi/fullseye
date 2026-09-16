void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Prewitt オペレータのマスク
    const int mask_x[3][3] = {
        {-1, 0, 1},
        {-1, 0, 1},
        {-1, 0, 1}
    };
    const int mask_y[3][3] = {
        {-1, -1, -1},
        {0, 0, 0},
        {1, 1, 1}
    };

    // 出力画像の高さと幅
    int out_h = h;
    int out_w = w;

    // 出力画像の各ピクセルに対して計算
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            double gx = 0.0;
            double gy = 0.0;

            // Prewitt オペレータのマスクを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int iy = y + ky;
                    int ix = x + kx;

                    // 画像の境界を越えた場合は境界値を 0 として扱う
                    if (iy < 0 || iy >= h || ix < 0 || ix >= w) {
                        continue;
                    }

                    // Prewitt オペレータのマスクを適用
                    gx += mask_x[ky + 1][kx + 1] * in[iy * w + ix];
                    gy += mask_y[ky + 1][kx + 1] * in[iy * w + ix];
                }
            }

            // 方向を [0, 1] の範囲に変換
            double direction = atan2(gy, gx) / (2 * M_PI) + 0.5;
            if (direction < 0) {
                direction += 1.0;
            }

            // 出力画像に結果を格納
            out[y * w + x] = direction;
        }
    }
}
