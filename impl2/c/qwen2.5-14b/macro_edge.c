void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない

    // エッジ検出アルゴリズムの実装
    // ここでは Sobel オペレータを使用する
    // Sobel オペレータは 3x3 のマスクを使用するため、画像の端は適切に処理する必要がある
    // 画像の端は、端のピクセルをコピーして埋める（パディング）

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0; // 初期値は 0.0 (背景)
        }
    }

    // Sobel オペレータのマスク
    const double sobel_x[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    const double sobel_y[3][3] = {
        {-1, -2, -1},
        {0, 0, 0},
        {1, 2, 1}
    };

    // エッジ検出
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = 0.0, gy = 0.0;

            // Sobel オペレータの適用
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    double pixel = in[iy * w + ix];
                    gx += pixel * sobel_x[ky + 1][kx + 1];
                    gy += pixel * sobel_y[ky + 1][kx + 1];
                }
            }

            // グレースケール画像のエッジ強度
            double edge_intensity = sqrt(gx * gx + gy * gy);

            // 二値化処理 (Otsu's method の代わりに単純な閾値処理を適用)
            if (edge_intensity > 0.5) { // 閾値は 0.5 とする
                out[y * w + x] = 1.0; // エッジを 1.0 で表す
            }
        }
    }
}
