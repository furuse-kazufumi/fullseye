void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a は最大シフト量を設定します。つまみ b はシフトの方向を設定します。
    // b < 0.5 なら右にシフト、b >= 0.5 なら左にシフトします。
    // 画像の端は反射境界を使用して処理します。

    double peak_shift = 0.25 * w * a;
    int shift_direction = (b < 0.5) ? 1 : -1;

    // ヘルパー関数: 反射境界でピクセルを取得します。
    double get_pixel_reflect(const double* img, int h, int w, int y, int x) {
        if (x < 0) x = -x - 1;
        if (x >= w) x = 2 * w - x - 1;
        if (y < 0) y = -y - 1;
        if (y >= h) y = 2 * h - y - 1;
        return img[y * w + x];
    }

    // メイン処理: 各ピクセルに対してシフトを適用します。
    for (int y = 0; y < h; ++y) {
        int shift = (int)(peak_shift * (y - h / 2.0) * shift_direction);
        for (int x = 0; x < w; ++x) {
            int src_x = x - shift;
            out[y * w + x] = get_pixel_reflect(in, h, w, y, src_x);
        }
    }
}
