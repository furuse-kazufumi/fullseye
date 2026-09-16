void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない
    (void)a;
    (void)b;

    // Sobel カーネル
    const double sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    const double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // 出力画像の高さと幅
    int out_h = h;
    int out_w = w;

    // 出力画像の各ピクセルに対して Sobel オペレータを適用
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            double dx = 0.0;
            double dy = 0.0;

            // Sobel カーネルを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int iy = y + ky;
                    int ix = x + kx;

                    // 画像の端を処理する際、境界外のピクセルを 0 と仮定
                    if (iy < 0 || iy >= h || ix < 0 || ix >= w) {
                        continue;
                    }

                    dx += in[iy * w + ix] * sobel_x[ky + 1][kx + 1];
                    dy += in[iy * w + ix] * sobel_y[ky + 1][kx + 1];
                }
            }

            // arctan2(dy, dx) を [0, 1] に写像
            double angle = atan2(dy, dx);
            if (angle < 0) {
                angle += 2 * M_PI;
            }
            out[y * w + x] = angle / (2 * M_PI);
        }
    }
}
