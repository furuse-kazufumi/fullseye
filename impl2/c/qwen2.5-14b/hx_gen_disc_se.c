void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径の計算
    double radius = (0.05 + 0.35 * a) * fmin(h, w) / 2.0;

    // 中心座標の計算
    int center_x = (w - 1) / 2;
    int center_y = (h - 1) / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // 円板の生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルの中心からの距離を計算
            double distance = sqrt((x - center_x) * (x - center_x) + (y - center_y) * (y - center_y));
            // 距離が半径以下の場合、出力画像の該当ピクセルを 1.0 に設定
            if (distance <= radius) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
