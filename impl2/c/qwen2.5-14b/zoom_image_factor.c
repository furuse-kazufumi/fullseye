void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 縦方向と横方向のスケーリングファクター
    double scale_height = 0.7 + 0.6 * a;
    double scale_width = 0.7 + 0.6 * b;

    // 出力画像の高さと幅
    int out_h = (int)(h * scale_height);
    int out_w = (int)(w * scale_width);

    // 反射で画像の端を埋めるための補間関数
    double interpolate(double* img, int h, int w, double y, double x) {
        // 座標を画像の範囲内に収める
        int y0 = (int)floor(y);
        int x0 = (int)floor(x);
        int y1 = y0 + 1;
        int x1 = x0 + 1;

        // 反射で画像の端を埋める
        if (y0 < 0) y0 = -y0;
        if (x0 < 0) x0 = -x0;
        if (y1 >= h) y1 = 2 * h - y1 - 1;
        if (x1 >= w) x1 = 2 * w - x1 - 1;

        // バイリニア補間
        double v00 = img[y0 * w + x0];
        double v01 = img[y0 * w + x1];
        double v10 = img[y1 * w + x0];
        double v11 = img[y1 * w + x1];
        double dx = x - floor(x);
        double dy = y - floor(y);
        return v00 * (1 - dx) * (1 - dy) + v01 * dx * (1 - dy) + v10 * (1 - dx) * dy + v11 * dx * dy;
    }

    // 出力画像の各ピクセルを計算
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            double in_y = y / (double)out_h * h;
            double in_x = x / (double)out_w * w;
            out[y * out_w + x] = interpolate((double*)in, h, w, in_y, in_x);
        }
    }
}
