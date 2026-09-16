void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Scharr オペレータのカーネル
    const double scharr_x[3][3] = {
        {-3, 0, 3},
        {-10, 0, 10},
        {-3, 0, 3}
    };
    const double scharr_y[3][3] = {
        {3, 10, 3},
        {0, 0, 0},
        {-3, -10, -3}
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各ピクセルに対して Scharr オペレータを適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = 0.0, gy = 0.0;

            // Scharr オペレータのカーネルを適用
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    gx += scharr_x[ky + 1][kx + 1] * in[iy * w + ix];
                    gy += scharr_y[ky + 1][kx + 1] * in[iy * w + ix];
                }
            }

            // エッジ強度を計算
            double edge_strength = sqrt(gx * gx + gy * gy);

            // 出力画像の最大値を更新
            if (edge_strength > max_out) {
                max_out = edge_strength;
            }

            // 出力画像にエッジ強度を格納
            out[y * w + x] = edge_strength;
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_out;
    }
}
