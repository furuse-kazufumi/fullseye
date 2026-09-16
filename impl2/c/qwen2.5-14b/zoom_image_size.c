void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 出力画像の高さと幅を計算
    int out_h = h * (0.5 + a);
    int out_w = w * (0.5 + b);

    // Bilinear interpolation を使用してリサンプリング
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            // 入力画像の座標を計算
            double in_y = (y + 0.5) / (0.5 + a) - 0.5;
            double in_x = (x + 0.5) / (0.5 + b) - 0.5;

            // Bilinear interpolation のための近傍ピクセルの座標
            int y0 = (int)in_y;
            int x0 = (int)in_x;
            int y1 = y0 + 1;
            int x1 = x0 + 1;

            // 座標の範囲外処理: 切り捨て
            if (y0 < 0) y0 = 0;
            if (x0 < 0) x0 = 0;
            if (y1 >= h) y1 = h - 1;
            if (x1 >= w) x1 = w - 1;

            // Bilinear interpolation の計算
            double dx = in_x - x0;
            double dy = in_y - y0;
            double w00 = (1 - dx) * (1 - dy);
            double w01 = dx * (1 - dy);
            double w10 = (1 - dx) * dy;
            double w11 = dx * dy;

            // 出力画像のピクセル値を計算
            double out_val = w00 * in[y0 * w + x0] + w01 * in[y0 * w + x1] +
                             w10 * in[y1 * w + x0] + w11 * in[y1 * w + x1];

            // 出力画像に書き込み
            out[y * out_w + x] = out_val;
        }
    }
}
