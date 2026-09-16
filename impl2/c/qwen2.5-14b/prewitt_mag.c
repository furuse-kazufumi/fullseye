void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Prewitt フィルタのカーネル
    const double prewitt_x[3][3] = {
        {-1, 0, 1},
        {-1, 0, 1},
        {-1, 0, 1}
    };
    const double prewitt_y[3][3] = {
        {-1, -1, -1},
        {0, 0, 0},
        {1, 1, 1}
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各ピクセルに対して計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double gx = 0.0, gy = 0.0;

            // Prewitt フィルタを適用
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の処理: 入力画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    gx += in[ny * w + nx] * prewitt_x[ky + 1][kx + 1];
                    gy += in[ny * w + nx] * prewitt_y[ky + 1][kx + 1];
                }
            }

            // ユークリッドノルムを計算
            double mag = sqrt(gx * gx + gy * gy);
            out[y * w + x] = mag;

            // 出力画像の最大値を更新
            if (mag > max_out) max_out = mag;
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_out;
    }
}
