void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 楕円の中心座標
    int center_x = w / 2;
    int center_y = h / 2;

    // 楕円の半径
    double radius_x = 0.42 * w;
    double radius_y = 0.30 * h;

    // 角度の計算
    double start_angle = b * 2 * M_PI;
    double span_angle = (0.1 + a * (2 * M_PI - 0.1));

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 楕円の扇形領域の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 座標の正規化
            double norm_x = (x - center_x) / radius_x;
            double norm_y = (y - center_y) / radius_y;

            // 座標の極座標への変換
            double angle = atan2(norm_y, norm_x);
            double distance = sqrt(norm_x * norm_x + norm_y * norm_y);

            // 角度の範囲を 0 から 2π に正規化
            while (angle < 0) angle += 2 * M_PI;
            while (angle > 2 * M_PI) angle -= 2 * M_PI;

            // 楕円の扇形領域の判定
            if (distance <= 1.0 && angle >= start_angle && angle <= start_angle + span_angle) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
